"""
Django views for face recognition and emotion detection integration
"""

from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import base64
import numpy as np
from datetime import datetime
from .models import candidate, exam, user
from .face_recognitions import ExamMonitoringSystem, FaceRecognitionSystem
import threading


# Global monitoring systems (in production, use proper session management)
monitoring_sessions = {}
_cv2 = None
_face_recognition_system = None

def _ensure_cv2():
    global _cv2
    if _cv2 is None:
        try:
            import cv2 as cv2_mod
            _cv2 = cv2_mod
        except Exception as e:
            print(f"OpenCV import failed in face_views: {e}")
            _cv2 = None
    return _cv2

def get_face_recognition_system():
    """Lazily initialize FaceRecognitionSystem to avoid heavy imports at module load."""
    global _face_recognition_system
    if _face_recognition_system is None:
        try:
            from .face_recognitions import FaceRecognitionSystem as FRS
            _face_recognition_system = FRS()
        except Exception as e:
            print(f"Failed to initialize FaceRecognitionSystem: {e}")
            _face_recognition_system = None
    return _face_recognition_system


@csrf_exempt
@require_http_methods(["POST"])
def capture_candidate_registration(request):
    """Capture and register candidate's face from camera feed"""
    try:
        candidate_id = request.POST.get('candidate_id')
        image_data = request.POST.get('image_data')  # Base64 encoded image
        
        if not candidate_id or not image_data:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate_id or image_data'})
        
        # Decode base64 image
        _cv2_local = _ensure_cv2()
        if _cv2_local is None:
            return JsonResponse({'status': 'error', 'message': 'OpenCV not available on server'})

        image_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = _cv2_local.imdecode(nparr, _cv2_local.IMREAD_COLOR)
        
        # Save temporary image
        temp_path = f'temp_face_{candidate_id}_{datetime.now().timestamp()}.jpg'
        cv2.imwrite(temp_path, img)
        
        # Register face
        frs = get_face_recognition_system()
        if frs is None:
            return JsonResponse({'status': 'error', 'message': 'Face recognition backend unavailable'})
        success, message = frs.register_candidate_face(candidate_id, temp_path)
        
        return JsonResponse({
            'status': 'success' if success else 'error',
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["GET"])
def start_exam_monitoring(request):
    """Start exam monitoring session for candidate"""
    try:
        if 'lid' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Session expired'})
        
        candidate_id = request.GET.get('candidate_id')
        
        if not candidate_id:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate_id'})
        
        # Initialize monitoring system for this session
        session_id = f"{candidate_id}_{datetime.now().timestamp()}"
        monitoring_sessions[session_id] = ExamMonitoringSystem()
        
        request.session['monitoring_session_id'] = session_id
        request.session['exam_monitoring_candidate'] = candidate_id
        
        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'message': 'Exam monitoring started'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def process_exam_frame(request):
    """Process frame during exam - detect faces and emotions"""
    try:
        if 'lid' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Session expired'})
        
        image_data = request.POST.get('image_data')  # Base64 encoded frame
        session_id = request.session.get('monitoring_session_id')
        candidate_id = request.session.get('exam_monitoring_candidate')
        
        if not image_data or not session_id:
            return JsonResponse({'status': 'error', 'message': 'Missing data'})
        
        _cv2_local = _ensure_cv2()
        if _cv2_local is None:
            return JsonResponse({'status': 'error', 'message': 'OpenCV not available on server'})

        # Decode base64 image
        image_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        frame = _cv2_local.imdecode(nparr, _cv2_local.IMREAD_COLOR)
        
        # Process frame
        monitoring_system = monitoring_sessions.get(session_id)
        if not monitoring_system:
            return JsonResponse({'status': 'error', 'message': 'Monitoring session not found'})
        
        monitoring_data = monitoring_system.process_frame(frame, candidate_id)
        
        # Encode annotated frame back to base64
        _, buffer = _cv2_local.imencode('.jpg', monitoring_data['frame'])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Prepare response
        response_data = {
            'status': 'success',
            'recognized_faces': monitoring_data['recognized_faces'],
            'unknown_faces': len(monitoring_data['unknown_faces']),
            'emotions': monitoring_data['emotions'],
            'violations': monitoring_data['violations'],
            'annotated_frame': f"data:image/jpeg;base64,{frame_b64}"
        }
        
        # Check for critical violations
        critical_violations = [v for v in monitoring_data['violations'] if v.get('severity') == 'critical']
        if critical_violations:
            response_data['warning'] = 'Critical violation detected - exam may be blocked'
        
        return JsonResponse(response_data)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["GET"])
def end_exam_monitoring(request):
    """End exam monitoring and generate report"""
    try:
        if 'lid' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Session expired'})
        
        session_id = request.session.get('monitoring_session_id')
        candidate_id = request.session.get('exam_monitoring_candidate')
        
        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'No monitoring session found'})
        
        monitoring_system = monitoring_sessions.get(session_id)
        if not monitoring_system:
            return JsonResponse({'status': 'error', 'message': 'Monitoring session not found'})
        
        # Generate report
        report = monitoring_system.get_monitoring_report()
        
        # Save report to database
        try:
            candidate_obj = candidate.objects.get(id=candidate_id)
            # You can save this report to a new model or update existing fields
            # For now, we'll return it
            
            # Update candidate status based on violations
            if report['total_violations'] > 5:  # Threshold for violations
                candidate.objects.filter(id=candidate_id).update(
                    status='exam_suspicious',
                    no_of_unknown_person=report['unknown_faces_count'],
                    multiple_person=report['total_violations']
                )
        except Exception as e:
            print(f"Error updating candidate status: {e}")
        
        # Clean up session
        del monitoring_sessions[session_id]
        
        return JsonResponse({
            'status': 'success',
            'report': {
                'total_frames': report['total_frames_processed'],
                'total_violations': report['total_violations'],
                'violations_by_type': report['violations_by_type'],
                'emotion_summary': report['emotion_summary'],
                'recognized_faces_count': report['recognized_faces_count'],
                'unknown_faces_count': report['unknown_faces_count']
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["GET"])
def get_monitoring_status(request):
    """Get current monitoring status"""
    try:
        if 'lid' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Session expired'})
        
        session_id = request.session.get('monitoring_session_id')
        
        if not session_id or session_id not in monitoring_sessions:
            return JsonResponse({'status': 'not_started'})
        
        monitoring_system = monitoring_sessions[session_id]
        report = monitoring_system.get_monitoring_report()
        
        return JsonResponse({
            'status': 'active',
            'frames_processed': report['total_frames_processed'],
            'total_violations': report['total_violations'],
            'critical_violations': sum(1 for v_list in report['violations'] 
                                       for v in v_list.get('violations', []) 
                                       if v.get('severity') == 'critical')
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_http_methods(["POST"])
def verify_candidate_before_exam(request):
    """Verify candidate identity before exam starts"""
    try:
        if 'lid' not in request.session:
            return HttpResponse("<script>alert('Session Expired');window.location='/'</script>")
        
        candidate_id = request.POST.get('candidate_id')
        image_data = request.POST.get('image_data')
        
        if not candidate_id or not image_data:
            return JsonResponse({'status': 'error', 'message': 'Missing data'})
        
        # Decode image
        image_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        _cv2_local = _ensure_cv2()
        if _cv2_local is None:
            return JsonResponse({'status': 'error', 'message': 'OpenCV not available on server'})

        frame = _cv2_local.imdecode(nparr, _cv2_local.IMREAD_COLOR)
        
        # Recognize face
        frs = get_face_recognition_system()
        if frs is None:
            return JsonResponse({'status': 'error', 'message': 'Face recognition backend unavailable'})

        recognized, unknown, _ = frs.detect_and_recognize_faces(frame)
        
        # Check if candidate is recognized
        candidate_recognized = False
        confidence = 0
        
        for rec in recognized:
            if str(rec['candidate_id']) == str(candidate_id):
                candidate_recognized = True
                confidence = rec['confidence']
                break
        
        if candidate_recognized and confidence > 0.6:  # Confidence threshold
            return JsonResponse({
                'status': 'success',
                'message': f'Candidate verified successfully (Confidence: {confidence:.2f})',
                'verified': True
            })
        else:
            return JsonResponse({
                'status': 'failed',
                'message': 'Face verification failed. Please ensure proper lighting and face is clearly visible.',
                'verified': False
            })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})
