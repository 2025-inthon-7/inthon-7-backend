from django.contrib import admin

from .models import Course, Session, FeedbackEvent, Question, ImportantMoment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "professor", "time")
    search_fields = ("code", "name", "professor")
    list_filter = ("professor",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("course", "date", "is_active")
    list_filter = ("course", "is_active")
    search_fields = ("course__code", "course__name")


@admin.register(FeedbackEvent)
class FeedbackEventAdmin(admin.ModelAdmin):
    list_display = ("session", "device_hash", "feedback_type", "created_at")
    list_filter = ("feedback_type", "created_at")
    search_fields = (
        "device_hash",
        "session__course__code",
        "session__course__name",
    )
    readonly_fields = ("created_at",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "short_original_text",
        "status",
        "forwarded_to_professor",
        "created_at",
    )
    list_filter = ("status", "forwarded_to_professor", "created_at")
    search_fields = (
        "original_text",
        "cleaned_text",
        "session__course__code",
        "session__course__name",
    )
    readonly_fields = ("created_at", "updated_at")

    def short_original_text(self, obj):
        text = obj.original_text or ""
        return (text[:50] + "...") if len(text) > 50 else text

    short_original_text.short_description = "Original text"


@admin.register(ImportantMoment)
class ImportantMomentAdmin(admin.ModelAdmin):
    list_display = ("session", "trigger", "question", "note", "created_at")
    list_filter = ("trigger", "created_at")
    search_fields = (
        "note",
        "session__course__code",
        "session__course__name",
    )
    readonly_fields = ("created_at",)
