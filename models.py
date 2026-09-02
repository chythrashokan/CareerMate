from django.db import models

# Create your models here.
class login(models.Model):
    username=models.CharField(max_length=200)
    password=models.CharField(max_length=200)
    usertype=models.CharField(max_length=200)

class company(models.Model):
    company_name=models.CharField(max_length=200)
    latitude=models.CharField(max_length=200)
    longitude=models.CharField(max_length=200)
    email=models.CharField(max_length=200)
    phone=models.CharField(max_length=200)
    description=models.CharField(max_length=200)
    place=models.CharField(max_length=200)
    pin=models.CharField(max_length=200)
    post=models.CharField(max_length=200)
    mailprovider=models.CharField(max_length=200)
    apppassword=models.CharField(max_length=200)
    image=models.CharField(max_length=200)
    LOGIN=models.ForeignKey(login,on_delete=models.CASCADE)

class user(models.Model):
    name=models.CharField(max_length=200)
    email=models.CharField(max_length=200)
    phone=models.CharField(max_length=200)
    place=models.CharField(max_length=200)
    pin=models.CharField(max_length=200)
    post=models.CharField(max_length=200)
    image=models.CharField(max_length=200)
    experience=models.PositiveIntegerField( default=1)
    LOGIN=models.ForeignKey(login,on_delete=models.CASCADE)

class job_category(models.Model):
    category_name=models.CharField(max_length=200)

class qualifications(models.Model):
    qualification=models.CharField(max_length=200)
    type = models.CharField(max_length=100)

class suggestions(models.Model):
    suggestion=models.CharField(max_length=200)
    date=models.CharField(max_length=200)
    type=models.CharField(max_length=200,default=1)
    LOGIN=models.ForeignKey(login,on_delete=models.CASCADE)


class vacancy(models.Model):
    job_type = models.CharField(max_length=100)
    salary = models.CharField(max_length=100)
    fulltime_parttime = models.CharField(max_length=100)
    description = models.TextField(max_length=100, default=1)
    experience = models.CharField(max_length=100, default=1)
    cuttoff = models.CharField(max_length=100, default=1)
    apply_from_date = models.DateField(null=True, blank=True)
    apply_to_date = models.DateField(null=True, blank=True)
    COMPANY = models.ForeignKey(company, on_delete=models.CASCADE, default=1)


class vaccancy_qualification(models.Model):
    QUALIFICATION = models.ForeignKey(qualifications, on_delete=models.CASCADE, default=1)
    VACANCY = models.ForeignKey(vacancy, on_delete=models.CASCADE, default=1)


class candidate(models.Model):
    exam_date = models.CharField(max_length=100)
    exam_ftime = models.CharField(max_length=100)
    exam_ttime = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    apply_date = models.CharField(max_length=100)
    apply_time = models.CharField(max_length=100)
    link = models.CharField(max_length=100)
    interview_date = models.CharField(max_length=100)
    interview_time = models.CharField(max_length=100)
    binterview_date = models.CharField(max_length=100)
    binterview_time = models.CharField(max_length=100)
    resume = models.CharField(max_length=100)
    no_of_unknown_person = models.CharField(max_length=100)
    multiple_person = models.CharField(max_length=100)
    match_percentage = models.CharField(max_length=100)
    total_mark = models.CharField(max_length=100)
    USER = models.ForeignKey(user, on_delete=models.CASCADE, default=1)
    VACANCY = models.ForeignKey(vacancy, on_delete=models.CASCADE, default=1)


# class test(models.Model):
#     name = models.CharField(max_length=100)
#     date = models.CharField(max_length=100)
#     mark = models.CharField(max_length=100)
#     cut_off_mark = models.CharField(max_length=100)
#     VACCANCY = models.ForeignKey(vacancy, on_delete=models.CASCADE, default=1)

class exam(models.Model):
    mark = models.IntegerField(max_length=100)
    CANDIDATE = models.ForeignKey(candidate, on_delete=models.CASCADE, default=1)


class question(models.Model):
    question = models.TextField(max_length=100)
    option1 = models.TextField(max_length=100)
    option2 = models.TextField(max_length=100)
    option3 = models.TextField(max_length=100)
    option4 = models.TextField(max_length=100)
    answers = models.TextField(max_length=100)
    VACANCY = models.ForeignKey(vacancy, on_delete=models.CASCADE, default=1)


class test_results(models.Model):
    status = models.CharField(max_length=100)
    mark = models.CharField(max_length=100)
    date = models.CharField(max_length=100)
    USER = models.ForeignKey(user, on_delete=models.CASCADE, default=1)
    QUESTION = models.ForeignKey(question, default=1, on_delete=models.CASCADE)

class emotions(models.Model):
    emotions = models.CharField(max_length=100)
    CANDIDATE = models.ForeignKey(candidate, on_delete=models.CASCADE, default=1)

class ProctoringViolation(models.Model):
    candidate = models.ForeignKey('candidate', on_delete=models.CASCADE)
    violation_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    screenshot = models.ImageField(upload_to='violation_screenshots/', blank=True, null=True)


class InterviewSession(models.Model):
    from datetime import timedelta
    session_id = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    # role/level/persona should not be unique per session; allow defaults
    role = models.CharField(max_length=100, blank=True, default='unknown')
    level = models.CharField(max_length=100, blank=True, default='mid')
    persona = models.CharField(max_length=100, blank=True, default='general')
    # Number of questions requested for this session (default 5, max 10)
    question_count = models.IntegerField(default=5)
    total_phonemes = models.IntegerField(default=0)
    duration = models.DurationField(default=timedelta(seconds=0))
    avg_speaking_rate = models.FloatField(null=True, blank=True)


class InterviewQA(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='qa_pairs')
    question = models.TextField()
    answer = models.TextField()
    timestamp = models.DateTimeField()

    # Answer timing
    answer_started_at = models.DateTimeField(null=True, blank=True)
    answer_ended_at = models.DateTimeField(null=True, blank=True)

    # Phoneme analysis
    phoneme_data = models.TextField()
    viseme_sequence = models.TextField()
    speaking_duration = models.FloatField(null=True, blank=True)

    # Emotional analysis
    question_emotion = models.CharField(max_length=20, blank=True)
    answer_emotion = models.CharField(max_length=20, blank=True)

    # Technical analysis
    technical_terms = models.TextField()
    confidence_score = models.FloatField(null=True, blank=True)
    clarity_score = models.FloatField(null=True, blank=True)

    # Raw ASR/Audio confidence (populated by backend/front-end) and normalized value (0..1)
    asr_confidence = models.FloatField(null=True, blank=True, help_text='Raw ASR confidence (0..1 or 0..100)')
    normalized_confidence = models.FloatField(null=True, blank=True, help_text='Normalized confidence 0..1')

    # Grammar suggestions and score
    grammar_suggestions = models.TextField(null=True, blank=True)
    grammar_score = models.FloatField(null=True, blank=True, help_text='Grammar quality score 0..1')

    def normalize_confidence(self):
        """Normalizes available confidence values into 0..1 and stores in normalized_confidence."""
        val = None
        if self.asr_confidence is not None:
            val = self.asr_confidence
        elif self.confidence_score is not None:
            val = self.confidence_score

        if val is None:
            return None

        # If value looks like a percentage >1, convert
        if val > 1:
            try:
                val = float(val) / 100.0
            except Exception:
                pass

        val = max(0.0, min(1.0, float(val)))
        self.normalized_confidence = val
        return self.normalized_confidence


class PhonemeAnalysis(models.Model):
    qa = models.ForeignKey(InterviewQA, on_delete=models.CASCADE, related_name='phonemes')
    phoneme = models.CharField(max_length=10)
    viseme = models.CharField(max_length=10)
    timestamp = models.FloatField()  # Seconds from start
    duration = models.FloatField()  # Duration in seconds


class QuestionAnswer(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='qas')
    question = models.TextField()
    answer = models.TextField()
    question_type = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    confidence_score = models.FloatField(null=True, blank=True)
    clarity_score = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    # Derived analysis fields
    normalized_confidence = models.FloatField(null=True, blank=True, help_text='Normalized confidence 0..1')
    grammar_suggestions = models.TextField(null=True, blank=True)
    grammar_score = models.FloatField(null=True, blank=True, help_text='Grammar quality score 0..1')
    lip_movement_score = models.FloatField(null=True, blank=True, help_text='Estimate 0..1 of lip movement quality')
    shiver_penalty = models.FloatField(null=True, blank=True,
                                       help_text='Penalty applied due to jitter/shivering 0..0.4')
    # Face emotion analysis fields
    emotion_data = models.TextField(null=True, blank=True, help_text='JSON store of emotions detected from face')
    dominant_emotion = models.CharField(max_length=50, null=True, blank=True,
                                        help_text='Most dominant emotion detected')
    emotion_confidence = models.FloatField(null=True, blank=True,
                                           help_text='Confidence score 0..1 from face emotion analysis')

    # Audio emotion analysis fields
    audio_emotion_confidence = models.FloatField(null=True, blank=True,
                                                 help_text='Confidence score 0..1 from audio emotion analysis')
    combined_emotion_confidence = models.FloatField(null=True, blank=True,
                                                    help_text='Combined 0..1 score from face (60%) + audio (40%)')

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Q{self.id}: {self.question[:50]}..."


class SessionAnalytics(models.Model):
    session = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='analytics')
    total_questions = models.IntegerField(default=0)
    avg_confidence = models.FloatField(default=0)
    avg_clarity = models.FloatField(default=0)
    total_duration = models.FloatField(default=0)  # in seconds
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analytics for {self.session.session_id}"


class EmotionSession(models.Model):
    """Store emotion data per interview session"""
    session_id = models.CharField(max_length=100, unique=True, db_index=True, primary_key=True)

    # Only keep minimal fields per request
    dominant_emotion = models.CharField(max_length=50, null=True, blank=True)
    emotion_confidence = models.FloatField(null=True, blank=True,
                                           help_text='Confidence score 0..1 of the dominant emotion')

    def __str__(self):
        return f"EmotionSession: {self.session_id} - {self.dominant_emotion}"


