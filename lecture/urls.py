from django.urls import path
from . import views

urlpatterns = [
    # Course & Session
    path("courses/", views.list_courses, name="list_courses"),
    path(
        "courses/<str:course_code>/today-session/",
        views.get_today_session,
        name="get_today_session",
    ),

    # Feedback
    path(
        "sessions/<int:session_id>/feedback/",
        views.submit_feedback,
        name="submit_feedback",
    ),

    # Question flow
    path(
        "sessions/<int:session_id>/questions/intent/",
        views.start_question_intent,
        name="start_question_intent",
    ),
    path(
        "questions/<int:question_id>/capture/",
        views.upload_question_capture,
        name="upload_question_capture",
    ),
    path(
        "questions/<int:question_id>/text/",
        views.submit_question_text,
        name="submit_question_text",
    ),
    path(
        "questions/<int:question_id>/ai-answer/",
        views.request_ai_answer,
        name="request_ai_answer",
    ),
    path(
        "questions/<int:question_id>/forward/",
        views.forward_question_to_professor,
        name="forward_question_to_professor",
    ),
    path(
        "sessions/<int:session_id>/questions/",
        views.list_session_questions,
        name="list_session_questions",
    ),

    # '중요해요' + HARD capture
    path(
        "sessions/<int:session_id>/important/",
        views.mark_important,
        name="mark_important",
    ),
    path(
        "sessions/<int:session_id>/hard-threshold-capture/",
        views.hard_threshold_capture,
        name="hard_threshold_capture",
    ),

    # Summary
    path(
        "sessions/<int:session_id>/summary/",
        views.session_summary,
        name="session_summary",
    ),
]
