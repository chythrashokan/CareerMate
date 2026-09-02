import numpy as np
import base64
import io
import os
import logging
import threading
import signal
from PIL import Image
from django.conf import settings
from django.core.files.storage import default_storage
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy native imports to avoid importing heavy C-extensions during module load.
_cv2 = None
_face_recognition = None

def _ensure_native_libs():
    """Attempt to import native libraries (cv2, face_recognition) on first use.
    Logs failures instead of crashing the process during module import.
    """
    global _cv2, _face_recognition
    if _cv2 is None:
        try:
            import cv2 as _cv2_mod
            _cv2 = _cv2_mod
        except Exception as e:
            logger.error(f"OpenCV (cv2) import failed: {e}")
            _cv2 = None

    if _face_recognition is None:
        try:
            import face_recognition as _fr_mod
            _face_recognition = _fr_mod
        except Exception as e:
            logger.error(f"face_recognition import failed: {e}")
            _face_recognition = None


def load_image_file_compat(path):
    """Load an image file using PIL when face_recognition.load_image_file fails."""
    # try:
    #     _ensure_native_libs()
    #     if _face_recognition is not None:
    #         return _face_recognition.load_image_file(path)
    # except Exception as e:
    #     err_text = str(e) or ''
    #     if isinstance(e, AttributeError) and 'scipy.misc' in err_text:
    #         logger.warning("face_recognition.load_image_file failed due to scipy.misc deprecation; falling back to PIL")
    #     else:
    #         logger.warning(f"face_recognition.load_image_file failed: {type(e).__name__}: {e}")

    try:
        with Image.open(path) as image:
            image = image.convert('RGB')
            return np.array(image)
    except Exception as pil_err:
        logger.error(f"PIL fallback failed loading image: {type(pil_err).__name__}: {pil_err}")
        raise


def optimize_image_for_face_detection(image, aggressive=False):
    """
    Optimize image size for faster face detection/encoding
    Reduces processing time significantly while maintaining accuracy
    aggressive=True uses smaller dimensions for maximum speed
    """
    try:
        _ensure_native_libs()
        if _cv2 is None:
            logger.warning("optimize_image_for_face_detection: OpenCV not available, skipping resize")
            return image
        height, width = image.shape[:2]
        
        # Target dimensions for faster processing
        # Regular: max 600px on longest side
        # Aggressive: max 400px on longest side (much faster encoding extraction)
        MAX_DIMENSION = 400 if aggressive else 600
        
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            logger.debug(f"[OPTIMIZE] {'Aggressive' if aggressive else 'Standard'} resizing from {width}x{height} to {new_width}x{new_height}")
            image = _cv2.resize(image, (new_width, new_height), interpolation=_cv2.INTER_AREA)
            logger.debug(f"[OPTIMIZE] Image resized successfully. New shape: {image.shape}")
        
        return image
    except Exception as e:
        logger.warning(f"[OPTIMIZE] Failed to optimize image: {e}")
        return image


def extract_face_encodings_with_timeout(image, timeout_seconds=20):
    """
    Extract face encodings with timeout protection
    Prevents the process from hanging indefinitely
    Default 20 second timeout to accommodate slower systems
    """
    import time
    result = {'encodings': [], 'error': None, 'timed_out': False, 'duration': 0}
    
    def worker():
        try:
            start_time = time.time()
            logger.debug(f"[ENCODING_WORKER] Starting face encoding extraction (timeout: {timeout_seconds}s)")
            _ensure_native_libs()
            if _face_recognition is None:
                raise RuntimeError("face_recognition library not available")
            encodings = _face_recognition.face_encodings(image)
            duration = time.time() - start_time
            result['duration'] = duration
            logger.debug(f"[ENCODING_WORKER] Face encoding extraction completed in {duration:.2f}s. Got {len(encodings)} encoding(s)")
            result['encodings'] = encodings
        except Exception as e:
            logger.error(f"[ENCODING_WORKER] Exception during face encoding: {type(e).__name__}: {e}")
            result['error'] = str(e)
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"[ENCODING_WORKER] Face encoding extraction timed out after {timeout_seconds}s")
        result['timed_out'] = True
        result['error'] = f"Face encoding extraction timed out after {timeout_seconds} seconds"
    
    return result

class SimpleFaceDetector:
    """
    Real face detection and recognition using face_recognition library
    with deep learning models for accurate identification
    """
    
    def __init__(self):
        # face_recognition uses dlib internally for highly accurate detection
        self.known_faces = {}  # Cache of registered face encodings
        # Increased tolerance from 0.6 to 0.65 for better real-world matching
        # while maintaining security. Higher = more lenient, lower = stricter
        self.tolerance = 0.65  # Distance threshold for face matching
        
    def decode_base64_image(self, image_data):
        """Convert base64 image to numpy array"""
        try:
            _ensure_native_libs()
            if _cv2 is None:
                logger.error("decode_base64_image: OpenCV not available")
                return None
            if isinstance(image_data, str):
                # Remove data:image/jpeg;base64, prefix if exists
                if 'base64,' in image_data:
                    image_data = image_data.split('base64,')[1]
                
                # Decode base64
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                return _cv2.cvtColor(np.array(image), _cv2.COLOR_RGB2BGR)
            else:
                return np.array(image_data)
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return None
    
    def detect_faces(self, image_data):
        """Detect faces in image using face_recognition library"""
        try:
            _ensure_native_libs()
            if _face_recognition is None or _cv2 is None:
                return {
                    "success": False,
                    "message": "Face detection libraries not available",
                    "faces_detected": 0
                }

            frame = self.decode_base64_image(image_data)
            if frame is None:
                return {
                    "success": False,
                    "message": "Failed to decode image",
                    "faces_detected": 0
                }
            
            # Convert BGR to RGB for face_recognition
            rgb_frame = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            
            # Optimize image size for faster processing
            rgb_frame = optimize_image_for_face_detection(rgb_frame)
            
            # Detect faces using face_recognition
            face_locations = _face_recognition.face_locations(rgb_frame, model='hog')  # 'hog' for speed, 'cnn' for accuracy
            
            face_list = []
            for top, right, bottom, left in face_locations:
                face_list.append({
                    'x': int(left),
                    'y': int(top),
                    'width': int(right - left),
                    'height': int(bottom - top),
                    'confidence': 0.95,
                    'coordinates': {'top': int(top), 'right': int(right), 'bottom': int(bottom), 'left': int(left)}
                })
            
            return {
                "success": True,
                "faces_detected": len(face_locations),
                "faces": face_list,
                "message": f"Detected {len(face_locations)} face(s)"
            }
            
        except Exception as e:
            logger.error(f"Error in detect_faces: {e}")
            return {
                "success": False,
                "message": str(e),
                "faces_detected": 0
            }
    
    def detect_head_movement(self, image_data):
        """Detect head movement and pose using face position analysis"""
        try:
            _ensure_native_libs()
            if _face_recognition is None or _cv2 is None:
                return {
                    "success": False,
                    "head_movement": False,
                    "head_pose": "unknown"
                }

            frame = self.decode_base64_image(image_data)
            if frame is None:
                logger.warning("detect_head_movement: Failed to decode image")
                return {
                    "success": False,
                    "head_movement": True,  # Treat as suspicious - cannot verify face
                    "head_pose": "image_decode_failed",
                    "confidence": 0.95,
                    "reason": "Could not process image frame"
                }
            rgb_frame = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            
            # Optimize image size (resize for faster face detection)
            rgb_frame = optimize_image_for_face_detection(rgb_frame)
            
            face_locations = _face_recognition.face_locations(rgb_frame, model='hog')
            
            if len(face_locations) == 0:
                logger.warning("detect_head_movement: No face detected in frame")
                return {
                    "success": False,
                    "head_movement": True,  # **SUSPICIOUS** - Face not visible (turned away, obstructed, or left frame)
                    "head_pose": "no_face_visible",
                    "confidence": 0.98,
                    "reason": "Face not detected in camera frame - possible turn away, obstruction, or absence from frame"
                }
            
            # Analyze first face position
            top, right, bottom, left = face_locations[0]
            
            # Calculate face position in frame
            frame_height, frame_width = rgb_frame.shape[:2]
            face_center_x = (left + right) / 2
            face_center_y = (top + bottom) / 2
            frame_center_x = frame_width / 2
            frame_center_y = frame_height / 2
            
            # Calculate horizontal and vertical deviation
            horizontal_deviation = abs(face_center_x - frame_center_x) / frame_center_x
            vertical_deviation = abs(face_center_y - frame_center_y) / frame_center_y
            
            # Determine head position based on deviation (more sensitive thresholds)
            movement_detected = horizontal_deviation > 0.25 or vertical_deviation > 0.20
            
            if horizontal_deviation > 0.35:
                head_pose = "turned_away"
            elif horizontal_deviation > 0.20:
                head_pose = "slightly_turned"
            elif vertical_deviation > 0.25:
                head_pose = "looking_down_or_up"
            else:
                head_pose = "facing_camera"
            
            return {
                "success": True,
                "head_movement": movement_detected,
                "head_pose": head_pose,
                "horizontal_deviation": float(horizontal_deviation),
                "vertical_deviation": float(vertical_deviation),
                "confidence": 0.90
            }
        
        except Exception as e:
            logger.error(f"Error in detect_head_movement: {e}")
            return {
                "success": False,
                "head_movement": True,  # Treat errors as suspicious activity
                "head_pose": "error_detection_failed",
                "confidence": 0.95,
                "reason": f"Face detection error: {str(e)}"
            }
    
    def get_face_encoding(self, image_data):
        """Extract face encoding for comparison using face_recognition"""
        try:
            _ensure_native_libs()
            if _face_recognition is None or _cv2 is None:
                return {'has_face': False}

            frame = self.decode_base64_image(image_data)
            if frame is None:
                return None

            rgb_frame = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            
            # Optimize image size for faster processing
            rgb_frame = optimize_image_for_face_detection(rgb_frame)
            
            # Get face locations
            face_locations = _face_recognition.face_locations(rgb_frame, model='hog')
            if len(face_locations) == 0:
                return {'has_face': False}
            
            # Get face encodings with timeout protection
            encoding_result = extract_face_encodings_with_timeout(rgb_frame, timeout_seconds=20)
            if encoding_result['timed_out'] or encoding_result['error']:
                logger.warning(f"Face encoding extraction failed: {encoding_result.get('error', 'timeout')}")
                return {'has_face': False}
            
            face_encodings = encoding_result['encodings']
            if len(face_encodings) == 0:
                return {'has_face': False}
            
            # Return first face encoding
            return {
                'has_face': True,
                'encoding': face_encodings[0],
                'location': face_locations[0],
                'num_encodings': len(face_encodings)
            }
        
        except Exception as e:
            logger.error(f"Error in get_face_encoding: {e}")
            return {'has_face': False}
    
    def compare_faces(self, face1_encoding, face2_encoding):
        """Compare two face encodings using face_recognition"""
        try:
            if not face1_encoding or not face1_encoding.get('has_face'):
                return {'match': False, 'score': 0.0}
            
            if not face2_encoding or not face2_encoding.get('has_face'):
                return {'match': False, 'score': 0.0}
            
            # Extract encodings
            encoding1 = face1_encoding.get('encoding')
            encoding2 = face2_encoding.get('encoding')
            
            if encoding1 is None or encoding2 is None:
                return {'match': False, 'score': 0.0}
            
            _ensure_native_libs()
            if _face_recognition is None:
                return {'match': False, 'score': 0.0}

            # Compare faces using face_recognition
            results = _face_recognition.compare_faces(
                [encoding1], 
                encoding2, 
                tolerance=self.tolerance
            )
            
            match = bool(results[0]) if results else False
            
            # Get face distance (lower is better, 0.0 is identical)
            distance_result = _face_recognition.face_distance([encoding1], encoding2)[0]
            distance = float(distance_result)
            
            # Convert distance to similarity score (1.0 is perfect match)
            similarity_score = 1.0 - distance
            
            return {
                'match': match,
                'score': float(similarity_score),
                'distance': float(distance)
            }
        
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return {'match': False, 'score': 0.0}
    
    def _compare_with_registered(self, candidate_id, current_image_data):
        """Compare current image with registered student photo"""
        try:
            from .models import candidate, user
            from django.conf import settings
            
            try:
                # Get the candidate record first
                cand = candidate.objects.get(id=candidate_id)
                # Get the associated student
                stud = cand.USER
                
                if not stud.image:
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'no_registered_image'
                    }
                
                # Read registered image - handle both relative and absolute paths
                try:
                    image_field = stud.image
                    image_str = str(image_field).strip()
                    
                    logger.debug(f"[REGISTERED_IMAGE] Image Info:")
                    logger.debug(f"   - Image Field: {image_field}")
                    logger.debug(f"   - Image String: {image_str}")
                    logger.debug(f"   - MEDIA_ROOT: {settings.MEDIA_ROOT}")
                    
                    if not image_str:
                        return {
                            'match': False,
                            'score': 0.0,
                            'method': 'invalid_image_path'
                        }

                    candidate_image_path = None
                    path_candidate = image_str.replace('\\', '/').strip()

                    # Normalize common media path formats:
                    # - /media/file.jpg
                    # - media/file.jpg
                    # - http://host/media/file.jpg
                    # - https://host/media/file.jpg
                    # - \media\file.jpg
                    if path_candidate.startswith(settings.MEDIA_URL):
                        path_candidate = path_candidate[len(settings.MEDIA_URL):]
                    elif path_candidate.startswith(settings.MEDIA_URL.lstrip('/')):
                        path_candidate = path_candidate[len(settings.MEDIA_URL.lstrip('/')):]
                    elif path_candidate.lower().startswith('media/'):
                        path_candidate = path_candidate[len('media/'):]

                    # If the stored path is a URL, keep only the filename or relative path
                    if '://' in path_candidate:
                        path_candidate = path_candidate.split('://', 1)[1]
                        path_candidate = path_candidate.split('/', 1)[-1]

                    path_candidate = path_candidate.lstrip('/')

                    # Try absolute path first if provided
                    if os.path.isabs(path_candidate):
                        candidate_image_path = os.path.normpath(path_candidate)
                        logger.debug(f"   - Trying absolute path: {candidate_image_path}")
                    else:
                        candidate_image_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, path_candidate))
                        logger.debug(f"   - Trying MEDIA_ROOT-based path: {candidate_image_path}")

                    if not os.path.exists(candidate_image_path):
                        filename = os.path.basename(path_candidate)
                        candidate_image_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, filename))
                        logger.debug(f"   - Fallback filename path: {candidate_image_path}")

                    registered_image_path = candidate_image_path
                    logger.debug(f"   - Final Path: {registered_image_path}")

                    # Final check - ensure path exists
                    if not registered_image_path or not os.path.exists(registered_image_path):
                        logger.warning(f"[NOT_FOUND] Image file not found at: {registered_image_path}")
                        return {
                            'match': False,
                            'score': 0.0,
                            'method': 'registered_image_not_found'
                        }
                    
                    logger.debug(f"[SUCCESS] Image file found: {registered_image_path}")
                        
                except Exception as path_err:
                    logger.error(f"Error resolving image path: {path_err}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'failed_to_resolve_image_path'
                    }
                
                # Load images using face_recognition
                try:
                    _ensure_native_libs()
                    if _face_recognition is None or _cv2 is None:
                        logger.error("Native face libraries missing during _compare_with_registered")
                        return {
                            'match': False,
                            'score': 0.0,
                            'method': 'native_libs_missing'
                        }

                    logger.debug(f"[LOADING] Starting to load registered image from: {registered_image_path}")
                    try:
                        registered_image = load_image_file_compat(registered_image_path)
                        logger.debug(f"[LOADED] Successfully loaded registered image. Shape: {registered_image.shape}")
                    except Exception as load_err:
                        logger.error(f"[ERROR] Failed to load registered image: {type(load_err).__name__}: {load_err}")
                        return {
                            'match': False,
                            'score': 0.0,
                            'method': 'failed_to_load_registered'
                        }
                except Exception as load_err:
                    logger.error(f"[ERROR] Exception while loading registered image: {type(load_err).__name__}: {load_err}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'failed_to_load_registered'
                    }

                # Decode current image
                logger.debug(f"[DECODING] Starting to decode current image from base64")
                current_frame = self.decode_base64_image(current_image_data)
                if current_frame is None:
                    logger.error(f"[ERROR] Failed to decode current image")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'failed_to_decode_current'
                    }
                logger.debug(f"[DECODED] Successfully decoded current image. Shape: {current_frame.shape}")
                
                # Convert BGR to RGB
                logger.debug(f"[CONVERTING] Converting current image from BGR to RGB")
                current_rgb = _cv2.cvtColor(current_frame, _cv2.COLOR_BGR2RGB)
                logger.debug(f"[CONVERTED] Image conversion complete")
                
                # Optimize images for faster processing (reduce size to speed up encoding extraction)
                # Use aggressive optimization for registered image to speed up encoding extraction
                logger.debug(f"[OPTIMIZING] Optimizing registered image for faster encoding (AGGRESSIVE)")
                optimized_registered = optimize_image_for_face_detection(registered_image, aggressive=True)
                
                logger.debug(f"[OPTIMIZING] Optimizing current image for faster encoding")
                optimized_current = optimize_image_for_face_detection(current_rgb)
                
                # Get face encodings with timeout protection
                logger.debug(f"[ENCODING] Extracting face encodings from registered image (with 20s timeout)")
                reg_encoding_result = extract_face_encodings_with_timeout(optimized_registered, timeout_seconds=20)
                
                if reg_encoding_result['timed_out']:
                    logger.error(f"[TIMEOUT] Registered image encoding extraction timed out")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'timeout_registered_encoding'
                    }
                
                if reg_encoding_result['error']:
                    logger.error(f"[ERROR] Error extracting registered encodings: {reg_encoding_result['error']}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'error_registered_encoding'
                    }
                
                registered_encodings = reg_encoding_result['encodings']
                logger.debug(f"[ENCODED] Got {len(registered_encodings)} encoding(s) from registered image")
                
                logger.debug(f"[ENCODING] Extracting face encodings from current image (with 20s timeout)")
                curr_encoding_result = extract_face_encodings_with_timeout(optimized_current, timeout_seconds=20)
                
                if curr_encoding_result['timed_out']:
                    logger.error(f"[TIMEOUT] Current image encoding extraction timed out")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'timeout_current_encoding'
                    }
                
                if curr_encoding_result['error']:
                    logger.error(f"[ERROR] Error extracting current encodings: {curr_encoding_result['error']}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'error_current_encoding'
                    }
                
                current_encodings = curr_encoding_result['encodings']
                logger.debug(f"[ENCODED] Got {len(current_encodings)} encoding(s) from current image")
                
                if len(registered_encodings) == 0:
                    logger.warning(f"[NO_FACE] No face found in registered image for candidate {candidate_id}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'no_face_in_registered'
                    }
                
                if len(current_encodings) == 0:
                    logger.warning(f"[NO_FACE] No face found in current image for candidate {candidate_id}")
                    return {
                        'match': False,
                        'score': 0.0,
                        'method': 'no_face_in_current'
                    }
                
                # Compare faces
                logger.debug(f"[COMPARING] Starting face comparison for candidate {candidate_id}")
                registered_encoding = registered_encodings[0]
                current_encoding = current_encodings[0]
                
                # Use face_recognition compare
                logger.debug(f"[COMPARING] Computing face comparison with tolerance={self.tolerance}")
                match_result = _face_recognition.compare_faces(
                    [registered_encoding], 
                    current_encoding, 
                    tolerance=self.tolerance
                )[0]
                # Convert numpy bool to Python bool for JSON serialization
                match = bool(match_result)
                logger.debug(f"[COMPARED] Face comparison result: {match}")
                
                # Get distance and convert to similarity
                logger.debug(f"[DISTANCE] Computing face distance")
                distance_result = _face_recognition.face_distance([registered_encoding], current_encoding)[0]
                # Convert numpy float to Python float for JSON serialization
                distance = float(distance_result)
                logger.debug(f"[DISTANCE] Face distance computed: {distance:.4f}")
                
                similarity_score = 1.0 - distance
                
                logger.info(f"[FACE_COMPARISON] Results for Candidate {candidate_id}:")
                logger.info(f"   - Distance: {distance:.4f} (lower = more similar)")
                logger.info(f"   - Similarity Score: {similarity_score:.4f} (higher = more similar)")
                logger.info(f"   - Tolerance Threshold: {self.tolerance} (match if distance < threshold)")
                logger.info(f"   - Match Result: {match} {'[MATCH]' if match else '[NO_MATCH]'}")
                
                logger.debug(f"[SUCCESS] Face comparison completed successfully for candidate {candidate_id}")
                
                return {
                    'match': match,
                    'score': float(similarity_score),
                    'method': 'face_recognition_deep_learning',
                    'distance': float(distance),
                    'tolerance': self.tolerance
                }
            
            except Exception as inner_e:
                import traceback
                logger.error(f"[ERROR] Exception in _compare_with_registered inner block: {type(inner_e).__name__}: {inner_e}")
                logger.error(f"[TRACEBACK] {traceback.format_exc()}")
                return {
                    'match': False,
                    'score': 0.0,
                    'method': 'error_loading_registered'
                }
        
        except Exception as e:
            import traceback
            logger.error(f"[CRITICAL] Exception in _compare_with_registered outer block: {type(e).__name__}: {e}")
            logger.error(f"[TRACEBACK] {traceback.format_exc()}")
            return {
                'match': False,
                'score': 0.0,
                'method': 'error'
            }
    
    def check_proctoring(self, image_data, candidate_id):
        """Comprehensive proctoring check"""
        try:
            frame = self.decode_base64_image(image_data)
            if frame is None:
                return {
                    "success": False,
                    "message": "Failed to decode image"
                }
            
            violations = []
            rgb_frame = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)

            # Optimize image size for faster processing
            logger.debug(f"[CHECK_PROCTORING] Optimizing image for proctoring check")
            rgb_frame = optimize_image_for_face_detection(rgb_frame)

            # 1. Check number of faces
            logger.debug(f"[CHECK_PROCTORING] Detecting faces in image")
            face_locations = _face_recognition.face_locations(rgb_frame, model='hog')
            
            if len(face_locations) == 0:
                violations.append({
                    'type': 'no_face',
                    'message': 'No face detected - Student not visible',
                    'severity': 'high'
                })
            elif len(face_locations) > 1:
                violations.append({
                    'type': 'multiple_faces',
                    'message': f'Multiple persons detected ({len(face_locations)} faces)',
                    'severity': 'critical'
                })
            
            # 2. Check head movement
            head_check = self.detect_head_movement(image_data)
            # Ignore movement that still results in the student facing the camera
            if head_check.get('head_movement') and head_check.get('head_pose') != 'facing_camera':
                violations.append({
                    'type': 'head_movement',
                    'message': f'Head movement detected - Student turned away ({head_check.get("head_pose")})',
                    'severity': 'medium'
                })
            
            return {
                "success": True,
                "violations": violations if violations else [],
                "message": f"Proctoring check complete. {len(violations)} violation(s) detected.",
                "faces_detected": len(face_locations),
                "heads_detected": len(face_locations),
                "head_pose": head_check.get('head_pose', 'unknown')
            }
        
        except Exception as e:
            logger.error(f"Error in check_proctoring: {e}")
            return {
                "success": False,
                "message": str(e),
                "violations": []
            }
    
    def save_screenshot(self, image_data, candidate_id, violation_type):
        """Save violation screenshot to media folder"""
        try:
            _ensure_native_libs()
            if _cv2 is None:
                logger.error("save_screenshot: OpenCV not available")
                return None

            frame = self.decode_base64_image(image_data)
            if frame is None:
                logger.error(f"Failed to decode image for screenshot")
                return None
            
            from django.conf import settings
            
            # Create directory for violation screenshots
            screenshot_dir = os.path.join(
                settings.MEDIA_ROOT,
                'violation_screenshots',
                str(candidate_id)
            )
            
            # Ensure directory exists
            try:
                os.makedirs(screenshot_dir, exist_ok=True)
            except Exception as dir_err:
                logger.error(f"Error creating screenshot directory {screenshot_dir}: {dir_err}")
                return None
            
            # Generate filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            filename = f"{violation_type}_{timestamp}.jpg"
            filepath = os.path.join(screenshot_dir, filename)
            
            # Save image using OpenCV
            success = _cv2.imwrite(filepath, frame)
            if not success:
                logger.error(f"Failed to write image to {filepath}")
                return None
            
            logger.info(f"Screenshot saved: {filepath}")
            
            # Return relative path for storage in database
            relative_path = f"violation_screenshots/{candidate_id}/{filename}"
            return relative_path
        
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}", exc_info=True)
            return None

    def save_exam_snapshot(self, image_data, candidate_id):
        """Save regular exam snapshot for audit trail"""
        try:
            _ensure_native_libs()
            if _cv2 is None:
                logger.error("save_exam_snapshot: OpenCV not available")
                return None

            frame = self.decode_base64_image(image_data)
            if frame is None:
                return None
            
            from django.conf import settings
            
            # Create directory for exam snapshots
            snapshot_dir = os.path.join(
                settings.MEDIA_ROOT,
                'exam_snapshots',
                str(candidate_id)
            )
            
            # Ensure directory exists
            try:
                os.makedirs(snapshot_dir, exist_ok=True)
            except Exception as dir_err:
                logger.error(f"Error creating snapshot directory {snapshot_dir}: {dir_err}")
                return None
            
            # Generate filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"snapshot_{timestamp}.jpg"
            filepath = os.path.join(snapshot_dir, filename)
            
            # Save image
            success = _cv2.imwrite(filepath, frame)
            if not success:
                logger.error(f"Failed to write snapshot to {filepath}")
                return None
            
            # Return relative path for storage
            relative_path = f"exam_snapshots/{candidate_id}/{filename}"
            return relative_path
        
        except Exception as e:
            logger.error(f"Error saving exam snapshot: {e}")
            return None
