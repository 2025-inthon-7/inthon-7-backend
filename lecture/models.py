from django.db import models

class Course(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    professor = models.CharField(max_length=100)
    time = models.CharField(max_length=100)

class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "date"],
                name="uniq_session_per_course_per_date",
            )
        ]

class FeedbackEvent(models.Model):
    FEEDBACK_TYPE = (('OK', 'OK'), ('HARD', 'HARD'))

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    device_hash = models.CharField(max_length=64)  # 익명 디바이스 식별자
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class Question(models.Model):
    class Status(models.TextChoices):
        INTENT = "INTENT", "Intent created"
        TEXT_SUBMITTED = "TEXT_SUBMITTED", "Text submitted & cleaned"
        AI_ANSWERED = "AI_ANSWERED", "AI answered"
        FORWARDED = "FORWARDED", "Forwarded to professor"
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    device_hash = models.CharField(max_length=64)
    original_text = models.TextField()
    cleaned_text = models.TextField(blank=True)

    ai_answer = models.TextField(blank=True)

    forwarded_to_professor = models.BooleanField(default=False)  # 교수에게 넘겼는지

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INTENT,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

class ImportantMoment(models.Model):
    TRIGGER_CHOICES = (
        ('MANUAL', 'Professor marked important'),
        ('QUESTION', 'Question with capture'),
        ('HARD', 'Hard threshold capture'),
    )

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=200, blank=True)
    screenshot_image = models.ImageField(upload_to='screenshots/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
