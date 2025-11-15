from __future__ import annotations

import json
import logging
from datetime import timedelta
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .ai.answer import answer_question
from .ai.clean import clean_question
from .ai.summarize_image import summarize_image as summarize_important_image
from .tasks import generate_important_summary_task
from .models import (
    Course,
    FeedbackEvent,
    ImportantMoment,
    Question,
    Session,
    QuestionLike,
)
from .serializers import (
    AIAnswerResponseSerializer,
    CourseSerializer,
    FeedbackSubmitSerializer,
    HardThresholdCaptureResponseSerializer,
    HardThresholdCaptureUploadSerializer,
    MarkImportantUploadSerializer,
    QuestionCaptureResponseSerializer,
    QuestionCaptureUploadSerializer,
    QuestionIntentResponseSerializer,
    QuestionOverrideRequestSerializer,
    QuestionSerializer,
    QuestionTextResponseSerializer,
    QuestionTextSubmitSerializer,
    SessionSerializer,
    SessionSummarySerializer,
    SimpleStatusResponseSerializer,
)


logger = logging.getLogger(__name__)


# ------------------------
# 공통 유틸
# ------------------------

def get_device_hash(request) -> str:
    """
    Flutter에서 X-Device-Hash 헤더로 보내는 익명 디바이스 ID.
    """
    h = request.headers.get("X-Device-Hash")
    if not h:
        h = "anonymous"
    return h


def get_or_create_today_session_by_course_code(course_code: str) -> Session:
    """
    교수/학생이 접속할 때,
    - 과목 code + 오늘 날짜 기준으로 Session 자동 생성/조회.
    """
    course = get_object_or_404(Course, code=course_code)
    today = timezone.localdate()
    session, _ = Session.objects.get_or_create(
        course=course,
        date=today,
        defaults={"is_active": True},
    )
    return session


def get_session_group_name(session_id: UUID | str, role: str) -> str:
    """
    WebSocket 그룹 이름 (role: teacher or student)
    """
    return f"session_{session_id}_{role}"


# AI 헬퍼 함수
def ai_clean_question(
    original_text: str,
    screenshot_url: str | None = None,
    subject_name: str | None = None,
) -> str:
    """
    텍스트 + (옵션) PPT 캡처 기반으로 질문을 정제.

    실제 구현은 Gemini 기반 LLM을 호출하며, 오류 발생 시 원본 텍스트를 그대로 반환합니다.
    """
    try:
        cleaned = clean_question(
            question=original_text,
            image_path=screenshot_url,
            subject_name=subject_name,
            temperature=0.3,
        )
        return cleaned
    except Exception as e:
        logger.error("Error in ai_clean_question: %s", e)
        return original_text.strip()


def ai_answer_question(
    cleaned_text: str,
    screenshot_url: str | None = None,
    subject_name: str | None = None,
) -> str:
    """
    정제된 질문 + (옵션) PPT 캡처 기반으로 답변.

    실제 구현은 Gemini 기반 LLM을 호출하며, 오류 발생 시 사용자 친화적인 기본 안내 메시지를 반환합니다.
    """
    try:
        answer = answer_question(
            question=cleaned_text,
            lecture_context=None,  # 나중에 세션 요약/중요 구간 등을 넣어 맥락 풍부화 가능
            image_path=screenshot_url,
            subject_name=subject_name,
            temperature=0.7,
        )
        return answer
    except Exception as e:
        logger.error("Error in ai_answer_question: %s", e)
        return "AI 조교가 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요."


def ai_summarize_important_image(
    image_path: str | None = None,
    subject_name: str | None = None,
) -> str | None:
    """
    교수님이 마크한 중요 구간 캡처 이미지를 1줄로 요약.

    summarize_image 모듈을 thin-wrapper로 감싸고, 오류 시 None을 반환합니다.
    """
    logger.info(
        "[AI DEBUG] ai_summarize_important_image called image_path=%s subject_name=%s",
        image_path,
        subject_name,
    )

    if not image_path:
        logger.info(
            "[AI DEBUG] ai_summarize_important_image: no image_path, skipping LLM"
        )
        return None

    try:
        logger.info(
            "[AI DEBUG] ai_summarize_important_image: calling summarize_important_image"
        )
        summary = summarize_important_image(
            image_path=image_path,
            subject_name=subject_name,
            temperature=0.3,
        )
        summary = summary.strip()
        logger.info(
            "[AI DEBUG] ai_summarize_important_image: summary_preview=%s",
            summary[:200],
        )
        return summary or None
    except Exception as e:
        logger.error("[AI DEBUG] ai_summarize_important_image ERROR: %s", e)
        return None


# ------------------------
# Course & Session 관련
# ------------------------

@extend_schema(
    responses=CourseSerializer(many=True),
)
@api_view(["GET"])
def list_courses(request):
    """
    과목 리스트 조회
    """
    qs = Course.objects.all()
    serializer = CourseSerializer(qs, many=True)
    return Response(serializer.data)


@extend_schema(
    responses=SessionSerializer,
)
@api_view(["GET"])
def get_today_session(request, course_code: str):
    """
    교수/학생 공통: 오늘 세션 가져오기 (없으면 생성)

    Path parameters:
    - `code` (string): 과목 코드-분반, 예: "COSE101-01"
    """
    session = get_or_create_today_session_by_course_code(course_code)
    data = SessionSerializer(session).data
    return Response(data)


# ------------------------
# 피드백 (OK / HARD)
# ------------------------

@extend_schema(
    request=FeedbackSubmitSerializer,
    responses={
        200: SimpleStatusResponseSerializer,
        400: OpenApiResponse(description="Invalid feedback_type"),
        403: OpenApiResponse(description="Invalid device."),
        429: OpenApiResponse(description="Too many requests."),
    },
)
@api_view(["POST"])
def submit_feedback(request, session_id: UUID):
    """
    학생: OK/HARD 피드백

    Path parameters:
    - `id` (integer): 세션 ID

    Headers:
    - `X-Device-Hash` (string, optional): 익명 디바이스 ID (없으면 "anonymous")
    """
    session = get_object_or_404(Session, id=session_id, is_active=True)
    device_hash = get_device_hash(request)
    feedback_type = request.data.get("feedback_type")

    if feedback_type not in ("OK", "HARD"):
        return Response(
            {"detail": "feedback_type must be 'OK' or 'HARD'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 간단 rate limit: 3초 이내 연타 방지
    last = FeedbackEvent.objects.filter(
        session=session,
        device_hash=device_hash,
    ).order_by("-created_at").first()

    if last and (timezone.now() - last.created_at).total_seconds() < 3:
        return Response(
            {"detail": "Too many requests."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    event = FeedbackEvent.objects.create(
        session=session,
        device_hash=device_hash,
        feedback_type=feedback_type,
    )

    # WebSocket으로 교수(teacher 그룹)에 피드백 이벤트 쏘기
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session_id, "teacher"),
        {
            "type": "feedback_message",
            "feedback_type": feedback_type,
            "created_at": event.created_at.isoformat(),
        },
    )

    return Response({"status": "ok"})


# ------------------------
# 질문 + 캡처
# ------------------------

@extend_schema(
    request=None,
    responses=QuestionIntentResponseSerializer,
)
@api_view(["POST"])
def start_question_intent(request, session_id: UUID):
    """
    학생: '질문하기' 버튼 눌렀을 때 호출.
    아직 질문 내용을 모르고, '질문 하나 시작'만 알리는 단계.

    - Question 레코드를 미리 만들고(original_text는 일단 빈 문자열)
    - 교수 쪽 teacher WebSocket 그룹에 question_intent 이벤트 전송
    - 응답으로 question_id를 돌려줌 → 학생/교수 둘 다 이 ID로 이후 API를 호출

    Path parameters:
    - `id` (integer): 세션 ID

    Headers:
    - `X-Device-Hash` (string, optional)

    Request body:
    - 없음
    """
    session = get_object_or_404(Session, id=session_id, is_active=True)
    device_hash = get_device_hash(request)

    # original_text는 일단 빈 문자열로 placeholder
    question = Question.objects.create(
        session=session,
        device_hash=device_hash,
        original_text="",
        status=Question.Status.INTENT,
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session_id, "teacher"),
        {
            "type": "question_intent",
            "question_id": question.id,
            "created_at": question.created_at.isoformat(),
        },
    )

    return Response(
        {"question_id": question.id, "created_at": question.created_at.isoformat()},
        status=status.HTTP_201_CREATED,
    )

@extend_schema(
    request=QuestionCaptureUploadSerializer,
    responses=QuestionCaptureResponseSerializer,
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_question_capture(request, question_id: int):
    """
    교수: question_intent를 받고 PPT 화면을 캡처해서 업로드.

    multipart/form-data:
      - screenshot (필수)

    Path parameters:
    - `id` (integer): Question ID

    Request body (multipart/form-data):
    - `screenshot` (file, required): PPT 캡처 이미지
    """
    question = get_object_or_404(Question, id=question_id)
    session = question.session

    screenshot = request.FILES.get("screenshot")
    if not screenshot:
        return Response(
            {"detail": "screenshot is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    moment = ImportantMoment.objects.create(
        session=session,
        trigger="QUESTION",
        question=question,
        screenshot_image=screenshot,
        note="",  # 원하면 "질문 시작 시점" 같은 문구 넣어도 됨
    )

    capture_url = moment.screenshot_image.url
    logger.info(
        "[DEBUG] upload_question_capture saved: %s -> %s",
        moment.screenshot_image.name,
        capture_url,
    )


    # 학생 그룹 WebSocket으로도 브로드캐스트
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session.id, "student"),
        {
            "type": "question_capture",
            "question_id": question.id,
            "capture_url": capture_url,
            "created_at": moment.created_at.isoformat(),
        },
    )

    return Response(
        {"question_id": question.id, "capture_url": capture_url},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=QuestionTextSubmitSerializer,
    responses={
        200: QuestionTextResponseSerializer,
        400: OpenApiResponse(description="original_text is required."),
        403: OpenApiResponse(description="Invalid device."),
    },
)
@api_view(["POST"])
def submit_question_text(request, question_id: int):
    """
    학생: 질문 텍스트 제출 + clean만 수행.

    body:
      - original_text

    Path parameters:
    - `id` (integer): Question ID

    Headers:
    - `X-Device-Hash` (string, optional)

    """
    question = get_object_or_404(Question, id=question_id)
    device_hash = get_device_hash(request)

    original_text = request.data.get("original_text")
    if not original_text:
        return Response(
            {"detail": "original_text is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if question.device_hash != device_hash:
        return Response({"detail": "Invalid device."}, status=status.HTTP_403_FORBIDDEN)

    question.original_text = original_text

    # 캡처 URL 찾기
    moment = (
        ImportantMoment.objects.filter(question=question, trigger="QUESTION")
        .order_by("-created_at")
        .first()
    )
    screenshot_url = (
        moment.screenshot_image.url if moment and moment.screenshot_image else None
    )

    # clean만 수행 (이미지까지 같이 줌)
    cleaned = ai_clean_question(
        original_text,
        screenshot_url,
        subject_name=question.session.course.code[:7],
    )
    question.cleaned_text = cleaned
    question.status = Question.Status.TEXT_SUBMITTED
    question.save(update_fields=["original_text", "cleaned_text", "status"])

    return Response(
        {
            "id": question.id,
            "original_text": question.original_text,
            "cleaned_text": question.cleaned_text,
            "capture_url": screenshot_url,
        },
        status=status.HTTP_200_OK,
    )

@extend_schema(
    request=QuestionOverrideRequestSerializer,
    responses={
        200: AIAnswerResponseSerializer,
        403: OpenApiResponse(description="Invalid device."),
    },
)
@api_view(["POST"])
def request_ai_answer(request, question_id: int):
    """
    학생: 정제된 질문(또는 수정본)에 대해 AI 답변 요청.

    body (optional):
      - override_cleaned_text: string (학생이 수정한 clean 버전 반영하고 싶을 때)

    Path parameters:
    - `id` (integer): Question ID

    Headers:
    - `X-Device-Hash` (string, optional)

    """
    question = get_object_or_404(Question, id=question_id)
    device_hash = get_device_hash(request)

    if question.device_hash != device_hash:
        return Response({"detail": "Invalid device."}, status=status.HTTP_403_FORBIDDEN)

    override_cleaned = request.data.get("override_cleaned_text")

    # 사용할 cleaned_text 결정
    if override_cleaned:
        cleaned_for_answer = override_cleaned.strip()
    elif question.cleaned_text:
        cleaned_for_answer = question.cleaned_text
    else:
        # clean 안 된 상태에서 바로 호출하면 original_text 기반으로라도 동작
        cleaned_for_answer = question.original_text

    # 캡처 URL 찾기
    moment = (
        ImportantMoment.objects.filter(question=question, trigger="QUESTION")
        .order_by("-created_at")
        .first()
    )
    screenshot_url = (
        moment.screenshot_image.url if moment and moment.screenshot_image else None
    )

    # AI 답변 호출
    answer = ai_answer_question(
        cleaned_for_answer,
        screenshot_url,
        subject_name=question.session.course.code[:7],
    )

    # DB 업데이트: cleaned_text도 override_cleaned가 있으면 갱신
    question.cleaned_text = cleaned_for_answer
    question.ai_answer = answer
    question.status = Question.Status.AI_ANSWERED
    question.save(update_fields=["cleaned_text", "ai_answer", "status"])

    return Response(
        {
            "id": question.id,
            "cleaned_text": question.cleaned_text,
            "ai_answer": question.ai_answer,
            "capture_url": screenshot_url,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    request=QuestionOverrideRequestSerializer,
    responses=SimpleStatusResponseSerializer,
)
@api_view(["POST"])
def forward_question_to_professor(request, question_id: int):
    """
    학생: 현재 상태의 질문(원문/정제/AI답변 + 캡처)을 교수에게 전달.

    Path parameters:
    - `id` (integer): Question ID

    Request body:
    - override_cleaned_text (string, optional): 교수에게 전달할 정제 텍스트를 덮어쓰고 싶을 때
    """
    question = get_object_or_404(Question, id=question_id)

    # 학생이 수정한 clean 버전을 교수에게 바로 보내고 싶을 때 사용
    override_cleaned = request.data.get("override_cleaned_text")

    # 캡처 URL
    moment = (
        ImportantMoment.objects.filter(question=question, trigger="QUESTION")
        .order_by("-created_at")
        .first()
    )
    screenshot_url = (
        moment.screenshot_image.url if moment and moment.screenshot_image else None
    )

    # request_ai_answer와 동일한 로직으로 cleaned_for_answer 결정
    if override_cleaned:
        cleaned_for_answer = override_cleaned.strip()
    elif question.cleaned_text:
        cleaned_for_answer = question.cleaned_text
    else:
        cleaned_for_answer = question.original_text

    # override가 있으면 DB의 cleaned_text도 함께 갱신
    if override_cleaned:
        question.cleaned_text = cleaned_for_answer

    question.forwarded_to_professor = True
    question.status = Question.Status.FORWARDED
    question.save()

    # 교수 및 학생 그룹 WebSocket으로 알림
    channel_layer = get_channel_layer()
    payload = {
        "type": "new_question",
        "question_id": question.id,
        "cleaned_text": cleaned_for_answer,
        "capture_url": screenshot_url,
        "created_at": question.updated_at.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(question.session_id, "teacher"),
        payload,
    )
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(question.session_id, "student"),
        payload,
    )

    return Response({"status": "ok"})


@extend_schema(
    request=None,
    responses=SimpleStatusResponseSerializer,
)
@api_view(["POST"])
def like_question(request, question_id: int):
    """
    학생: '나도 궁금해요'
    """
    question = get_object_or_404(Question, id=question_id)
    device_hash = get_device_hash(request)

    # QuestionLike 생성 (이미 있으면 무시)
    like, created = QuestionLike.objects.get_or_create(
        question=question,
        device_hash=device_hash,
    )

    if created:
        # "나도 궁금해요" 카운트 브로드캐스트
        like_count = question.likes.count()
        session_id = question.session_id

        channel_layer = get_channel_layer()
        payload = {
            "type": "question_like_update",
            "question_id": question.id,
            "like_count": like_count,
        }
        # 교수와 학생 모두에게 보낸다
        async_to_sync(channel_layer.group_send)(
            get_session_group_name(session_id, "teacher"),
            payload,
        )
        async_to_sync(channel_layer.group_send)(
            get_session_group_name(session_id, "student"),
            payload,
        )

    return Response({"status": "ok"})


@extend_schema(
    responses=QuestionSerializer(many=True),
)
@api_view(["GET"])
def list_session_questions(request, session_id: UUID):
    """
    교수: 세션 질문 목록

    Path parameters:
    - `id` (integer): 세션 ID

    Query parameters:
    - `forwarded_only` (string, optional): "true" 인 경우 교수에게 전달된 질문만
    """
    session = get_object_or_404(Session, id=session_id)
    forwarded_only = request.query_params.get("forwarded_only") == "true"

    qs = Question.objects.filter(session=session).order_by("created_at")
    if forwarded_only:
        qs = qs.filter(forwarded_to_professor=True)

    serializer = QuestionSerializer(qs, many=True)
    return Response(serializer.data)



# ------------------------
# '중요해요' + HARD 구간 캡처
# ------------------------

@extend_schema(
    request=MarkImportantUploadSerializer,
    responses=QuestionCaptureResponseSerializer,
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def mark_important(request, session_id: UUID):
    """
    교수: '중요해요' + PPT 캡쳐

    multipart/form-data:
      - note (optional)
      - screenshot (optional)

    Path parameters:
    - `id` (integer): 세션 ID

    Request body (multipart/form-data):
    - `note` (string, optional): 메모, 예: "중요 개념"
    - `screenshot` (file, optional): PPT 캡처 이미지
    """
    session = get_object_or_404(Session, id=session_id, is_active=True)

    # 사용자가 직접 입력한 메모 (optional)
    raw_note = request.data.get("note", "") or ""
    screenshot = request.FILES.get("screenshot")
    logger.info(
        "[AI DEBUG] mark_important called session_id=%s has_screenshot=%s raw_note=%r",
        session_id,
        bool(screenshot),
        raw_note,
    )

    # 1차로 ImportantMoment를 생성해서 파일을 디스크에 저장
    moment = ImportantMoment.objects.create(
        session=session,
        trigger="MANUAL",
        note=raw_note,
        screenshot_image=screenshot,
    )

    capture_url = moment.screenshot_image.url if screenshot else None
    logger.info(
        "[AI DEBUG] mark_important saved ImportantMoment id=%s capture_url=%s",
        moment.id,
        capture_url,
    )
    
    # 학생 그룹에  브로드캐스트
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session_id, "student"),
        {
            "type": "important_message",
            "note": raw_note,
            "capture_url": capture_url,
            "created_at": moment.created_at.isoformat(),
        },
    )

    # Celery 비동기 작업으로 요약 생성 및 note 업데이트만 수행
    generate_important_summary_task.delay(
        moment_id=moment.id,
        session_id_str=str(session_id),
        raw_note=raw_note,
    )

    return Response(
        {"id": moment.id, "note": raw_note, "capture_url": capture_url},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=HardThresholdCaptureUploadSerializer,
    responses=HardThresholdCaptureResponseSerializer,
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def hard_threshold_capture(request, session_id: UUID):
    """
    교수(프론트): HARD가 threshold 넘었다고 판단했을 때

    multipart/form-data:
      - screenshot (필수)

    Path parameters:
    - `id` (integer): 세션 ID

    Request body (multipart/form-data):
    - `screenshot` (file, required): PPT 캡처 이미지
    """
    session = get_object_or_404(Session, id=session_id, is_active=True)
    screenshot = request.FILES.get("screenshot")

    if not screenshot:
        return Response(
            {"detail": "screenshot is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # note는 현재 별도 입력 없이 빈 문자열로 저장
    note = ""

    moment = ImportantMoment.objects.create(
        session=session,
        trigger="HARD",
        screenshot_image=screenshot,
        note=note,
    )

    capture_url = moment.screenshot_image.url
    logger.info(
        "[DEBUG] hard_threshold_capture saved: %s -> %s",
        moment.screenshot_image.name,
        capture_url,
    )
    channel_layer = get_channel_layer()
    payload = {
        "type": "hard_alert",
        "capture_url": capture_url,
        "created_at": moment.created_at.isoformat(),
    }

    # 학생 + 교수 둘 다에게 알림
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session_id, "student"),
        payload,
    )
    async_to_sync(channel_layer.group_send)(
        get_session_group_name(session_id, "teacher"),
        payload,
    )

    return Response(
        {"id": moment.id, "capture_url": capture_url},
        status=status.HTTP_201_CREATED,
    )


# ------------------------
# Summary
# ------------------------

@extend_schema(
    responses=SessionSummarySerializer,
)
@api_view(["GET"])
def session_summary(request, session_id: UUID):
    """
    수업 Summary

    Path parameters:
    - `id` (integer): 세션 ID
    """
    session = get_object_or_404(Session, id=session_id)


    first_feedback = (
        FeedbackEvent.objects.filter(session=session)
        .order_by("created_at")
        .first()
    )
    last_feedback = (
        FeedbackEvent.objects.filter(session=session)
        .order_by("-created_at")
        .first()
    )
    first_q = Question.objects.filter(session=session).order_by("created_at").first()
    last_q = Question.objects.filter(session=session).order_by("-created_at").first()
    first_m = (
        ImportantMoment.objects.filter(session=session)
        .order_by("created_at")
        .first()
    )
    last_m = (
        ImportantMoment.objects.filter(session=session)
        .order_by("-created_at")
        .first()
    )


    # feedback 집계
    feedback_qs = FeedbackEvent.objects.filter(session=session)
    total_ok = feedback_qs.filter(feedback_type="OK").count()
    total_hard = feedback_qs.filter(feedback_type="HARD").count()

    # 질문 집계
    questions_qs = Question.objects.filter(session=session)
    question_count = questions_qs.count()


    # important moments
    moments_qs = ImportantMoment.objects.filter(session=session).order_by("created_at")
    moments_data = [
        {
            "id": m.id,
            "trigger": m.trigger,
            "note": m.note,
            "capture_url": m.screenshot_image.url if m.screenshot_image else None,
            "created_at": m.created_at.isoformat(),
            "question_id": m.question_id,
        }
        for m in moments_qs
    ]

    return Response(
        {
            "date": session.date.isoformat(),
            "course": {
                "code": session.course.code,
                "name": session.course.name,
                "professor": session.course.professor,
            },
            "feedback": {"ok": total_ok, "hard": total_hard},
            "question_count": question_count,
            "important_moments": moments_data,
        }
    )
