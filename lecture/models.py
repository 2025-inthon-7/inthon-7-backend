from django.db import models
import uuid
import os


def important_moment_screenshot_upload_path(instance, filename: str) -> str:
    """
    ImportantMoment 스크린샷 업로드 경로.

    - Session별로 하위 폴더를 나누어 관리하고
    - 파일명은 UUID 기반의 짧고 안전한 이름으로 통일.
    """

    _, ext = os.path.splitext(filename)
    ext = ext.lstrip(".") or "png"

    # Session별로 폴더 분리 (UUID → hex 문자열)
    session_id = getattr(instance, "session_id", None)
    if session_id is not None:
        try:
            session_str = session_id.hex if hasattr(session_id, "hex") else str(session_id)
        except Exception:
            session_str = str(session_id)
    else:
        session_str = "unknown-session"

    return f"screenshots/{session_str}/{uuid.uuid4().hex}.{ext}"


class Course(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    professor = models.CharField(max_length=100)
    time = models.CharField(max_length=100)


class SubjectInfo(models.Model):
    """
    과목 코드/이름별 상세 설명을 담는 모델.

    프롬프트 템플릿에서 과목 정보를 주입할 때 사용됩니다.
    """

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Subject info"
        verbose_name_plural = "Subject infos"

    def __str__(self) -> str:  # pragma: no cover - admin 표시용
        return f"{self.code} - {self.name}"

class Session(models.Model):
    # UUID를 기본 키로 사용
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
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
    screenshot_image = models.ImageField(
        upload_to=important_moment_screenshot_upload_path, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
