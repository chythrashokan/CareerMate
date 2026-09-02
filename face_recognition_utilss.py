import numpy as np
import json
import base64
from PIL import Image
import io
import os
from django.conf import settings
from datetime import datetime

# Lazy import OpenCV to avoid crashes during module import on systems
_cv2 = None

def _ensure_cv2():
    global _cv2
    if _cv2 is None:
        try:
            import cv2 as cv2_mod
            _cv2 = cv2_mod
        except Exception as e:
            print(f"OpenCV import failed in face_recognition_utilss: {e}")
            _cv2 = None
    return _cv2

class SimpleFaceDetector:
    def __init__(self):
        # Initialize Haar cascade for face detection
        cv2_local = _ensure_cv2()
        if cv2_local is None:
            raise RuntimeError('OpenCV is required for SimpleFaceDetector')
        self.face_cascade = cv2_local.CascadeClassifier(cv2_local.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detection history for each candidate
        self.detection_history = {}
        self.last_violation_time = {}
        
        # Detection thresholds
        self.FACE_CONFIDENCE_THRESHOLD = 0.5
        self.MULTIPLE_FACE_THRESHOLD = 2
        self.NO_FACE_FRAMES_THRESHOLD = 10
        self.HEAD_MOVEMENT_THRESHOLD = 40  # pixels
        
    def base64_to_image(self, image_data):
        """Convert base64 image data to OpenCV image"""
        try:
            # Handle data URL format
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array and OpenCV BGR format
            np_image = np.array(image)
            cv2_local = _ensure_cv2()
            if cv2_local is None:
                raise RuntimeError('OpenCV not available')
            bgr_image = cv2_local.cvtColor(np_image, cv2_local.COLOR_RGB2BGR)
            
            return bgr_image, image.width, image.height
            
        except Exception as e:
            print(f"Error converting image: {e}")
            return None, 0, 0
    
    def detect_faces(self, image_data):
        """Detect faces in image using Haar cascade"""
        try:
            # Convert image
            image, width, height = self.base64_to_image(image_data)
            if image is None:
                return {"face_count": 0, "faces": [], "error": "Invalid image"}
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            result = {
                "success": True,
                "face_count": len(faces),
                "faces": [],
                "image_size": {"width": width, "height": height}
            }
            
            for i, (x, y, w, h) in enumerate(faces):
                # Calculate face center
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Calculate relative position (percentage)
                rel_x = (center_x / width) * 100
                rel_y = (center_y / height) * 100
                
                # Determine position
                position = self._get_position(rel_x, rel_y)
                
                # Calculate confidence based on face size relative to image
                face_area = w * h
                image_area = width * height
                confidence = min(100, (face_area / image_area) * 1000)
                
                face_info = {
                    "id": i + 1,
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "center": {"x": int(center_x), "y": int(center_y)},
                    "position": position,
                    "confidence": round(confidence, 2),
                    "relative_position": {"x": round(rel_x, 2), "y": round(rel_y, 2)}
                }
                
                result["faces"].append(face_info)
            
            return result
            
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return {"success": False, "face_count": 0, "error": str(e)}
    
    def _get_position(self, rel_x, rel_y):
        """Determine face position based on relative coordinates"""
        if rel_x < 35:
            horizontal = "Left"
        elif rel_x > 65:
            horizontal = "Right"
        else:
            horizontal = "Center"
        
        if rel_y < 35:
            vertical = "Top"
        elif rel_y > 65:
            vertical = "Bottom"
        else:
            vertical = "Middle"
        
        if horizontal == "Center" and vertical == "Middle":
            return "Center"
        else:
            return f"{vertical} {horizontal}"
    
    def check_proctoring(self, image_data, candidate_id):
        """Check for proctoring violations"""
        try:
            # Initialize candidate history if not exists
            if candidate_id not in self.detection_history:
                self.detection_history[candidate_id] = {
                    "no_face_count": 0,
                    "last_face_position": None,
                    "last_detection_time": datetime.now(),
                    "consecutive_multiple_faces": 0
                }
            
            history = self.detection_history[candidate_id]
            violations = []
            recommendation = "Continue exam"
            
            # Detect faces
            detection_result = self.detect_faces(image_data)
            
            if not detection_result.get("success", False):
                return {
                    "success": False,
                    "violations": [{"type": "system_error", "message": "Face detection failed"}],
                    "recommendation": "Check camera"
                }
            
            face_count = detection_result.get("face_count", 0)
            faces = detection_result.get("faces", [])
            
            # Check for no face
            if face_count == 0:
                history["no_face_count"] += 1
                
                if history["no_face_count"] > self.NO_FACE_FRAMES_THRESHOLD:
                    # Check if enough time has passed since last violation
                    last_violation = self.last_violation_time.get(candidate_id, {}).get('no_face')
                    current_time = datetime.now()
                    
                    if not last_violation or (current_time - last_violation).seconds > 30:
                        violations.append({
                            "type": "no_face",
                            "message": f"No face detected for {history['no_face_count']} frames",
                            "severity": "warning" if history['no_face_count'] < 20 else "danger"
                        })
                        
                        if history['no_face_count'] >= 20:
                            recommendation = "Warning: Face not visible"
                            if candidate_id not in self.last_violation_time:
                                self.last_violation_time[candidate_id] = {}
                            self.last_violation_time[candidate_id]['no_face'] = current_time
            else:
                history["no_face_count"] = 0
                
                # Check for multiple faces
                if face_count > 1:
                    history["consecutive_multiple_faces"] += 1
                    
                    if history["consecutive_multiple_faces"] >= 3:
                        last_violation = self.last_violation_time.get(candidate_id, {}).get('multiple_faces')
                        current_time = datetime.now()
                        
                        if not last_violation or (current_time - last_violation).seconds > 60:
                            violations.append({
                                "type": "multiple_faces",
                                "message": f"Multiple faces detected: {face_count}",
                                "severity": "danger"
                            })
                            
                            if candidate_id not in self.last_violation_time:
                                self.last_violation_time[candidate_id] = {}
                            self.last_violation_time[candidate_id]['multiple_faces'] = current_time
                else:
                    history["consecutive_multiple_faces"] = 0
                    
                    # Check head movement for single face
                    if faces:
                        current_position = faces[0].get("position", "Center")
                        last_position = history.get("last_face_position")
                        
                        if last_position and current_position != last_position:
                            # Simple head movement detection
                            current_rel = faces[0].get("relative_position", {"x": 50, "y": 50})
                            if "last_relative_position" in history:
                                last_rel = history["last_relative_position"]
                                dx = abs(current_rel["x"] - last_rel["x"])
                                dy = abs(current_rel["y"] - last_rel["y"])
                                
                                if dx > self.HEAD_MOVEMENT_THRESHOLD or dy > self.HEAD_MOVEMENT_THRESHOLD:
                                    last_violation = self.last_violation_time.get(candidate_id, {}).get('head_movement')
                                    current_time = datetime.now()
                                    
                                    if not last_violation or (current_time - last_violation).seconds > 45:
                                        violations.append({
                                            "type": "head_movement",
                                            "message": f"Excessive head movement detected: {current_position}",
                                            "severity": "warning"
                                        })
                                        self.last_violation_time.setdefault(candidate_id, {})['head_movement'] = current_time
                        
                        # Update history
                        history["last_face_position"] = current_position
                        history["last_relative_position"] = faces[0].get("relative_position", {"x": 50, "y": 50})
            
            # Update last detection time
            history["last_detection_time"] = datetime.now()
            
            # Check if exam should be blocked
            total_violations = len(violations)
            if total_violations > 0:
                # Count dangerous violations
                dangerous_violations = [v for v in violations if v.get("severity") == "danger"]
                if len(dangerous_violations) >= 3:
                    recommendation = "Exam may be blocked"
            
            return {
                "success": True,
                "face_count": face_count,
                "violations": violations,
                "recommendation": recommendation,
                "detection_details": detection_result
            }
            
        except Exception as e:
            print(f"Error in proctoring check: {e}")
            return {"success": False, "error": str(e)}
    
    def save_screenshot(self, image_data, candidate_id, violation_type):
        """Save screenshot for violation evidence"""
        try:
            from .models import ProctoringViolation
            from datetime import datetime
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"violation_{candidate_id}_{violation_type}_{timestamp}.jpg"
            
            # Remove data URL prefix if present
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode and save
            image_bytes = base64.b64decode(image_data)
            
            # Save to media directory
            media_dir = os.path.join(settings.MEDIA_ROOT, 'violation_screenshots')
            os.makedirs(media_dir, exist_ok=True)
            
            filepath = os.path.join(media_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Return relative path
            return os.path.join('violation_screenshots', filename)
            
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return None

# Global instance
face_detector = SimpleFaceDetector()