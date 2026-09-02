"""
Face Recognition and Emotion Detection Module for Interview Simulator
Uses OpenCV for face detection and TensorFlow/Keras for emotion detection
"""

import cv2
import numpy as np
import os
from datetime import datetime
import json
import face_recognition as fr

# Guard TensorFlow imports so the app can run without TF installed
TENSORFLOW_AVAILABLE = True
try:
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing.image import img_to_array
except Exception:
    TENSORFLOW_AVAILABLE = False
    load_model = None
    def img_to_array(x):
        # minimal fallback if needed; should not be used when TF absent
        return x
import pickle

class FaceRecognitionSystem:
    """Handle face detection and recognition"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_known_faces()
    
    def load_known_faces(self, faces_dir='candidate_faces'):
        """Load all known candidate faces from directory"""
        if not os.path.exists(faces_dir):
            os.makedirs(faces_dir)
            return
        
        for person_name in os.listdir(faces_dir):
            person_dir = os.path.join(faces_dir, person_name)
            if not os.path.isdir(person_dir):
                continue
            
            for image_name in os.listdir(person_dir):
                image_path = os.path.join(person_dir, image_name)
                try:
                    image = fr.load_image_file(image_path)
                    face_encodings = fr.face_encodings(image)
                    
                    if face_encodings:
                        self.known_face_encodings.append(face_encodings[0])
                        self.known_face_names.append(person_name)
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
    
    def register_candidate_face(self, candidate_id, image_path):
        """Register a new candidate's face"""
        faces_dir = 'candidate_faces'
        candidate_dir = os.path.join(faces_dir, str(candidate_id))
        
        if not os.path.exists(candidate_dir):
            os.makedirs(candidate_dir)
        
        try:
            image = fr.load_image_file(image_path)
            face_encodings = fr.face_encodings(image)
            
            if face_encodings:
                # Save encoding
                encoding_path = os.path.join(candidate_dir, f"encoding_{datetime.now().timestamp()}.npy")
                np.save(encoding_path, face_encodings[0])
                
                # Save image
                img_filename = os.path.join(candidate_dir, f"image_{datetime.now().timestamp()}.jpg")
                cv2.imwrite(img_filename, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
                
                # Update known faces
                self.known_face_encodings.append(face_encodings[0])
                self.known_face_names.append(str(candidate_id))
                
                return True, "Face registered successfully"
            else:
                return False, "No face detected in image"
        except Exception as e:
            return False, f"Error registering face: {str(e)}"
    
    def detect_and_recognize_faces(self, frame):
        """Detect and recognize faces in a frame
        
        Returns:
            - list of recognized candidates
            - list of unknown faces
            - annotated frame
        """
        # Convert frame to RGB for face_recognition library
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = fr.face_locations(rgb_frame, model='hog')  # Use 'cnn' for better accuracy but slower
        face_encodings = fr.face_encodings(rgb_frame, face_locations)
        
        face_labels = []
        unknown_faces = []
        recognized_candidates = []
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Compare with known faces
            matches = fr.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"
            confidence = 0
            
            # Calculate face distances
            face_distances = fr.face_distance(self.known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    confidence = 1 - face_distances[best_match_index]
                    recognized_candidates.append({
                        'candidate_id': name,
                        'confidence': float(confidence),
                        'timestamp': datetime.now().isoformat(),
                        'location': {'top': top, 'right': right, 'bottom': bottom, 'left': left}
                    })
                else:
                    unknown_faces.append({
                        'confidence': float(1 - face_distances[best_match_index]),
                        'location': {'top': top, 'right': right, 'bottom': bottom, 'left': left}
                    })
            else:
                unknown_faces.append({
                    'confidence': 0,
                    'location': {'top': top, 'right': right, 'bottom': bottom, 'left': left}
                })
            
            # Draw rectangle on frame
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, f"{name} ({confidence:.2f})", (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            face_labels.append(name)
        
        return recognized_candidates, unknown_faces, frame


class EmotionDetectionSystem:
    """Detect emotions from faces"""
    
    def __init__(self, model_path='INTERVIEW_NAVIGATOR/static/model.h5'):
        """Initialize emotion detection model"""
        # If TensorFlow is not available, disable emotion detection gracefully
        if not TENSORFLOW_AVAILABLE:
            print("TensorFlow not available — emotion detection disabled.")
            self.model = None
            self.emotion_labels = []
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            return

        try:
            self.model = load_model(model_path)
            self.emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception as e:
            print(f"Error loading emotion model: {e}")
            self.model = None
            self.emotion_labels = []
    
    def detect_emotions(self, frame):
        """Detect emotions in frame
        
        Returns:
            - list of emotions with confidence scores
            - annotated frame
        """
        if self.model is None:
            return [], frame
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        emotions_detected = []
        
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (48, 48))
            roi_gray = roi_gray.astype('float') / 255.0
            roi_gray = img_to_array(roi_gray)
            roi_gray = np.expand_dims(roi_gray, axis=0)
            
            emotion_prediction = self.model.predict(roi_gray, verbose=0)
            emotion_label = self.emotion_labels[np.argmax(emotion_prediction)]
            emotion_probability = np.max(emotion_prediction)
            
            emotions_detected.append({
                'emotion': emotion_label,
                'confidence': float(emotion_probability),
                'timestamp': datetime.now().isoformat(),
                'location': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                'all_emotions': {label: float(prob) for label, prob in zip(self.emotion_labels, emotion_prediction[0])}
            })
            
            # Draw rectangle and emotion label
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.putText(frame, f"{emotion_label} ({emotion_probability:.2f})", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
        
        return emotions_detected, frame


class ExamMonitoringSystem:
    """Monitor candidates during exam - combines face recognition and emotion detection"""
    
    def __init__(self):
        self.face_recognition = FaceRecognitionSystem()
        self.emotion_detection = EmotionDetectionSystem()
        self.monitoring_log = []
        self.violations = []
    
    def process_frame(self, frame, candidate_id):
        """Process a frame during exam
        
        Returns:
            monitoring_data: dict with detection results
        """
        # Detect and recognize faces
        recognized, unknown, frame_faces = self.face_recognition.detect_and_recognize_faces(frame)
        
        # Detect emotions
        emotions, frame_emotions = self.emotion_detection.detect_emotions(frame)
        
        # Check for violations
        violation_flags = self._check_violations(recognized, unknown, emotions, candidate_id)
        
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'recognized_faces': recognized,
            'unknown_faces': unknown,
            'emotions': emotions,
            'violations': violation_flags,
            'frame': frame_emotions,  # Use the emotion-annotated frame
            'candidate_id': candidate_id
        }
        
        self.monitoring_log.append(monitoring_data)
        
        if violation_flags:
            self.violations.append(monitoring_data)
        
        return monitoring_data
    
    def _check_violations(self, recognized, unknown, emotions, candidate_id):
        """Check for potential exam violations"""
        violations = []
        
        # Check for unknown faces (other people in frame)
        if len(unknown) > 0:
            violations.append({
                'type': 'unknown_person_detected',
                'severity': 'high',
                'count': len(unknown),
                'message': f'Detected {len(unknown)} unknown face(s)'
            })
        
        # Check for multiple faces
        total_faces = len(recognized) + len(unknown)
        if total_faces > 1:
            violations.append({
                'type': 'multiple_people_detected',
                'severity': 'critical',
                'count': total_faces,
                'message': f'Multiple people detected: {total_faces}'
            })
        
        # Check for suspicious emotions
        for emotion_data in emotions:
            emotion = emotion_data['emotion'].lower()
            if emotion in ['angry', 'disgust', 'fear']:
                violations.append({
                    'type': f'suspicious_emotion_{emotion}',
                    'severity': 'medium',
                    'emotion': emotion,
                    'message': f'Detected {emotion} emotion'
                })
        
        return violations
    
    def get_monitoring_report(self):
        """Generate monitoring report for exam session"""
        report = {
            'total_frames_processed': len(self.monitoring_log),
            'total_violations': len(self.violations),
            'violations_by_type': {},
            'emotion_summary': {},
            'recognized_faces_count': 0,
            'unknown_faces_count': 0,
            'monitoring_log': self.monitoring_log,
            'violations': self.violations
        }
        
        # Aggregate violation types
        for violation_entry in self.violations:
            for violation in violation_entry['violations']:
                vtype = violation['type']
                report['violations_by_type'][vtype] = report['violations_by_type'].get(vtype, 0) + 1
        
        # Aggregate emotions
        for log_entry in self.monitoring_log:
            for emotion_data in log_entry['emotions']:
                emotion = emotion_data['emotion']
                report['emotion_summary'][emotion] = report['emotion_summary'].get(emotion, 0) + 1
        
        # Count recognized and unknown faces
        for log_entry in self.monitoring_log:
            report['recognized_faces_count'] += len(log_entry['recognized_faces'])
            report['unknown_faces_count'] += len(log_entry['unknown_faces'])
        
        return report
    
    def reset(self):
        """Reset monitoring system for new session"""
        self.monitoring_log = []
        self.violations = []


# Utility functions

def capture_candidate_photo(candidate_id, output_dir='candidate_faces'):
    """Capture photo from webcam for candidate registration"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    candidate_dir = os.path.join(output_dir, str(candidate_id))
    if not os.path.exists(candidate_dir):
        os.makedirs(candidate_dir)
    
    cap = cv2.VideoCapture(0)
    print(f"Capturing photo for candidate {candidate_id}. Press 'c' to capture, 'q' to quit.")
    
    captured_photos = []
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Show frame
            cv2.imshow(f'Capture photo for Candidate {candidate_id}', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                # Save photo
                filename = os.path.join(candidate_dir, f"photo_{len(captured_photos)}.jpg")
                cv2.imwrite(filename, frame)
                captured_photos.append(filename)
                print(f"Photo captured: {filename}")
            elif key == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return captured_photos


def get_webcam_stream():
    """Get webcam stream for real-time monitoring"""
    return cv2.VideoCapture(0)
