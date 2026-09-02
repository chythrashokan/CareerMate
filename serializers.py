from rest_framework import serializers
from .models import InterviewSession, QuestionAnswer, SessionAnalytics

class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = ['session_id', 'role', 'level', 'persona', 'start_time', 'end_time']

class QuestionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionAnswer
        fields = ['id', 'question', 'answer', 'question_type', 'category', 
                 'confidence_score', 'clarity_score', 'ai_feedback', 'timestamp',
                 'emotion_data', 'dominant_emotion', 'emotion_confidence', 
                 'audio_emotion_confidence', 'combined_emotion_confidence', 'normalized_confidence']

class SessionAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAnalytics
        fields = ['total_questions', 'avg_confidence', 'avg_clarity', 
                 'total_duration', 'generated_at']