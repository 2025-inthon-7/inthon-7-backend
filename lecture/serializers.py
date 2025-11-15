# lecture/serializers.py
from rest_framework import serializers
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from .models import Course, Session, Question, ImportantMoment


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "professor", "time"]


class SessionSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Session
        fields = ["id", "course", "date", "is_active"]


class QuestionSerializer(serializers.ModelSerializer):
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "session",
            "device_hash",
            "original_text",
            "cleaned_text",
            "ai_answer",
            "forwarded_to_professor",
            "status",
            "like_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "session",
            "device_hash",
            "ai_answer",
            "forwarded_to_professor",
            "status",
            "like_count",
            "created_at",
            "updated_at",
        ]

    def get_like_count(self, obj: Question) -> int:
        # 'likes'는 QuestionLike 모델의 related_name
        return obj.likes.count()


class ImportantMomentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportantMoment
        fields = [
            "id",
            "session",
            "trigger",
            "question",
            "note",
            "screenshot_image",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class FeedbackSubmitSerializer(serializers.Serializer):
    feedback_type = serializers.ChoiceField(choices=["OK", "HARD"])


class SimpleStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class QuestionIntentResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class QuestionCaptureResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    capture_url = serializers.CharField()


@extend_schema_field(OpenApiTypes.BINARY)
class UploadImageField(serializers.ImageField):
    """
    drf-spectacular에서 요청 바디를 파일 업로드(binary)로 인식시키기 위한 ImageField 래퍼.
    """

    pass


class QuestionCaptureUploadSerializer(serializers.Serializer):
    """
    질문 캡처 업로드용 multipart/form-data 스키마
    """

    screenshot = UploadImageField()


class QuestionTextSubmitSerializer(serializers.Serializer):
    original_text = serializers.CharField()


class QuestionTextResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    original_text = serializers.CharField()
    cleaned_text = serializers.CharField()
    capture_url = serializers.CharField(allow_null=True)


class QuestionOverrideRequestSerializer(serializers.Serializer):
    override_cleaned_text = serializers.CharField(required=False, allow_blank=True)


class AIAnswerResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cleaned_text = serializers.CharField()
    ai_answer = serializers.CharField()
    capture_url = serializers.CharField(allow_null=True)


class ImportantMomentSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    note = serializers.CharField(allow_blank=True)
    capture_url = serializers.CharField(allow_null=True)


class MarkImportantUploadSerializer(serializers.Serializer):
    """
    '중요해요' 수동 캡처용 multipart/form-data 스키마
    """

    note = serializers.CharField(required=False, allow_blank=True)
    screenshot = UploadImageField(required=False)


class HardThresholdCaptureResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    capture_url = serializers.CharField()
    hard_ratio = serializers.CharField(allow_null=True)


class HardThresholdCaptureUploadSerializer(serializers.Serializer):
    """
    HARD threshold 캡처용 multipart/form-data 스키마
    """

    screenshot = UploadImageField()


class SessionSummaryMomentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    trigger = serializers.CharField()
    note = serializers.CharField(allow_blank=True)
    capture_url = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    question_id = serializers.IntegerField(allow_null=True)


class SessionSummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    course = serializers.DictField()
    duration_minutes = serializers.IntegerField()
    feedback = serializers.DictField()
    question_count = serializers.IntegerField()
    important_moments = SessionSummaryMomentSerializer(many=True)
