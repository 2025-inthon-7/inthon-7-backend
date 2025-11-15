"""
Prompt Templates Module

LLM에 사용할 프롬프트 템플릿 정의
"""

from typing import Optional
from django.db.models import Q

def get_subject_info(subject_name: Optional[str] = None) -> str:
    """
    과목명/코드에 해당하는 과목 정보를 DB에서 조회해 반환합니다.

    Args:
        subject_name: 과목 코드 또는 이름 (예: "COSE213", "자료구조" 등)
                      None이거나 매칭되는 레코드가 없으면 빈 문자열 반환
    
    Returns:
        과목 정보 문자열 (학수번호와 설명 포함, 없으면 빈 문자열)
    """
    if not subject_name or not subject_name.strip():
        return ""

    subject_name = subject_name.strip()

    from ..models import SubjectInfo

    try:
        subject = (
            SubjectInfo.objects.filter(is_active=True)
            .filter(Q(code__iexact=subject_name) | Q(name__iexact=subject_name))
            .first()
        )
    except Exception:
        return ""

    if not subject:
        return ""
    
    # 과목명(subject.name)과 설명을 함께 반환
    result_parts = []
    if subject.name:
        result_parts.append(f"과목명: {subject.name}")
    if subject.description:
        result_parts.append(subject.description)
    
    return "\n".join(result_parts) if result_parts else "" # "name:description"꼴로 반환


# 질문 알잘딱 프롬프트 템플릿
CLEAN_QUESTION_SYSTEM_PROMPT_TEMPLATE = """당신은 학생 질문을 정제하는 전문가입니다.
학생이 작성한 질문에서 오타, 문법 오류, 불필요한 표현, 저속한 표현을 수정하고 명확하게 만들어야 합니다.
원래 의도를 유지하면서 더 이해하기 쉽고 정제된 질문으로 변환하세요.

{subject_section}제공된 교수님 화면 캡쳐 이미지가 있다면, 이미지의 내용을 참고하여 질문의 맥락을 더 정확히 파악하고 정제하세요.
이미지에 표시된 강의 내용, 코드, 수식 등을 고려하여 질문을 더 명확하게 만들 수 있습니다.
과목 관련 용어나 개념이 포함된 경우, 위 과목 정보를 참고하여 정확하게 정제하세요."""

CLEAN_QUESTION_USER_TEMPLATE = """다음 학생 질문을 정제해주세요:

{question}

{image_instruction}

정제된 질문만 반환해주세요. 추가 설명 없이 질문만 출력하세요."""

CLEAN_QUESTION_WITH_IMAGE_TEMPLATE = """다음 학생 질문을 정제해주세요:

{question}

위 질문과 함께 제공된 교수님 화면 캡쳐 이미지를 참고하여 질문을 정제해주세요.
이미지에 표시된 강의 내용, 코드, 수식 등을 고려하여 질문의 맥락을 파악하고 더 명확하게 만들어주세요.

정제된 질문만 반환해주세요. 추가 설명 없이 질문만 출력하세요."""

# 질문 detect 프롬프트트
DETECT_QUESTION_SYSTEM_PROMPT = """당신은 학생 질문을 분류하는 전문가입니다.
제공된 텍스트가 강의 관련 질문인지, 아니면 질문이 아닌지 판단하고, 질문인 경우 카테고리를 분류해야 합니다."""

DETECT_QUESTION_USER_TEMPLATE = """다음 텍스트를 분석하여 질문인지 여부와 카테고리를 판단해주세요:

{text}

다음 JSON 형식으로 응답해주세요:
{
    "is_question": true/false,
    "category": "학술적 질문"/"기술적 질문"/"일반 질문"/"질문 아님",
    "confidence": 0.0-1.0 사이의 신뢰도 점수,
    "reason": "판단 근거"
}

카테고리 설명:
- "학술적 질문": 강의 내용, 개념, 이론에 대한 질문
- "기술적 질문": 실습, 코드, 구현 방법에 대한 질문
- "일반 질문": 강의와 관련은 있지만 구체적인 내용과 무관한 질문
- "질문 아님": 질문이 아닌 경우 (응답은 항상 JSON 형식)"""

#강의 요약 프롬프트트
SUMMARIZE_LECTURE_SYSTEM_PROMPT = """당신은 강의 내용을 요약하는 전문가입니다.
제공된 강의 텍스트나 대본을 바탕으로 핵심 내용을 명확하고 구조화된 형태로 요약해야 합니다."""

SUMMARIZE_LECTURE_USER_TEMPLATE = """다음 강의 내용을 요약해주세요:

{lecture_content}

다음 항목들을 포함하여 요약해주세요:
1. 주요 주제 및 목표
2. 핵심 개념 및 내용
3. 중요한 포인트
4. 실습/예제 요약 (있는 경우)

구조화된 형태로 명확하게 작성해주세요."""

#이미지 요약 프롬프트
SUMMARIZE_IMAGE_SYSTEM_PROMPT_TEMPLATE = """당신은 강의 화면 이미지를 분석하고 요약하는 전문가입니다.
교수님이 중요하다고 마크한 화면 이미지를 분석하여 핵심 내용을 1줄로 요약해야 합니다.
{subject_section}이미지에 표시된 강의 내용, 코드, 수식, 화면 내용 등을 정확하게 파악하여 간결하고 명확하게 요약하세요."""

SUMMARIZE_IMAGE_USER_TEMPLATE = """제공된 교수님 화면 캡쳐 이미지를 분석하여 1줄로 요약해주세요.

이미지에 표시된 강의 내용, 코드, 수식, 화면 내용 등을 정확하게 파악하여 핵심 내용만 간결하게 1줄로 요약하세요.
추가 설명이나 형식 없이 요약 내용만 반환해주세요."""

#교수 빙의 프롬프트 템플릿
ANSWER_QUESTION_SYSTEM_PROMPT_TEMPLATE = """당신은 경험이 풍부하고 친절한 대학교수입니다.
{subject_section}당신은 이 과목의 전문가이며, 학생들의 질문에 대해 명확하고 교육적으로 답변해야 합니다.

답변 작성 시 다음 원칙을 따르세요:
1. 명확하고 이해하기 쉬운 설명
2. 필요시 예시나 비유 사용
3. 단계별 설명 (복잡한 개념의 경우)
4. 격려하고 긍정적인 톤 유지
5. 강의 맥락을 고려한 답변 (특히 위 과목 내용과 관련된 경우 정확하게 답변)
6. 추가 학습 자료나 참고 사항 제시 (필요시)
7. 과목 관련 질문의 경우 해당 과목의 전문 지식을 활용하여 정확하게 답변

**중요**: 답변은 최대한 딱딱하고 객관적으로 작성하세요. 불필요한 수식어나 감정 표현을 피하고, 핵심 내용만 간결하고 명확하게 전달하세요. 격려나 친근한 표현은 최소화하고 사실과 정보에 집중하세요."""

ANSWER_QUESTION_USER_TEMPLATE = """학생이 다음과 같은 질문을 했습니다:

{question}

{context_section}
{image_instruction}

위 질문에 대해 교수님 역할로 명확하고 교육적인 답변을 작성해주세요.
답변은 최대한 딱딱하고 객관적으로 작성하세요. 불필요한 수식어나 감정 표현 없이 핵심 내용만 간결하고 명확하게 전달하세요. 필요시 예시를 포함하되, 격려나 친근한 표현은 최소화하고 사실과 정보에 집중하세요."""

ANSWER_QUESTION_WITH_CONTEXT_TEMPLATE = """학생이 다음과 같은 질문을 했습니다:

{question}

강의 맥락/컨텍스트:
{lecture_context}
{image_instruction}

위 질문에 대해 교수님 역할로 명확하고 교육적인 답변을 작성해주세요.
답변은 최대한 딱딱하고 객관적으로 작성하세요. 불필요한 수식어나 감정 표현 없이 핵심 내용만 간결하고 명확하게 전달하세요. 강의 맥락을 고려하여 답변하되, 필요시 예시를 포함하되 격려나 친근한 표현은 최소화하고 사실과 정보에 집중하세요."""

ANSWER_QUESTION_WITH_IMAGE_TEMPLATE = """학생이 다음과 같은 질문을 했습니다:

{question}

{context_section}
위 질문과 함께 제공된 교수님 화면 캡쳐 이미지를 참고하여 답변해주세요.
이미지에 표시된 강의 내용, 코드, 수식, 화면 내용 등을 분석하여 질문의 맥락을 파악하고 정확하게 답변하세요.

위 질문에 대해 교수님 역할로 명확하고 교육적인 답변을 작성해주세요.
답변은 최대한 딱딱하고 객관적으로 작성하세요. 불필요한 수식어나 감정 표현 없이 핵심 내용만 간결하고 명확하게 전달하세요. 필요시 예시를 포함하되, 격려나 친근한 표현은 최소화하고 사실과 정보에 집중하세요."""

ANSWER_QUESTION_WITH_CONTEXT_AND_IMAGE_TEMPLATE = """학생이 다음과 같은 질문을 했습니다:

{question}

강의 맥락/컨텍스트:
{lecture_context}

위 질문과 함께 제공된 교수님 화면 캡쳐 이미지를 참고하여 답변해주세요.
이미지에 표시된 강의 내용, 코드, 수식, 화면 내용 등을 분석하여 질문의 맥락을 파악하고 정확하게 답변하세요.

위 질문에 대해 교수님 역할로 명확하고 교육적인 답변을 작성해주세요.
답변은 최대한 딱딱하고 객관적으로 작성하세요. 불필요한 수식어나 감정 표현 없이 핵심 내용만 간결하고 명확하게 전달하세요. 강의 맥락과 이미지 내용을 모두 고려하여 답변하되, 필요시 예시를 포함하되 격려나 친근한 표현은 최소화하고 사실과 정보에 집중하세요."""


def get_clean_question_prompt(
    question: str,
    has_image: bool = False,
    subject_name: Optional[str] = None,
) -> tuple[str, str]:
    """
    질문 정제 프롬프트 생성

    Args:
        question: 정제할 학생 질문
        has_image: 이미지가 제공되는지 여부
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    # 과목 정보 섹션 생성
    subject_info = get_subject_info(subject_name)
    if subject_info:
        subject_section = f"강의 과목 정보:\n{subject_info}\n\n"
    else:
        subject_section = ""

    system_prompt = CLEAN_QUESTION_SYSTEM_PROMPT_TEMPLATE.format(
        subject_section=subject_section
    )

    if has_image:
        user_prompt = CLEAN_QUESTION_WITH_IMAGE_TEMPLATE.format(question=question)
    else:
        user_prompt = CLEAN_QUESTION_USER_TEMPLATE.format(
            question=question,
            image_instruction="",
        )

    return (
        system_prompt,
        user_prompt,
    )


def get_detect_question_prompt(text: str) -> tuple[str, str]:
    """
    질문 감지 프롬프트 생성

    Args:
        text: 분석할 텍스트

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    return (
        DETECT_QUESTION_SYSTEM_PROMPT,
        DETECT_QUESTION_USER_TEMPLATE.format(text=text),
    )


def get_summarize_lecture_prompt(lecture_content: str) -> tuple[str, str]:
    """
    강의 요약 프롬프트 생성

    Args:
        lecture_content: 요약할 강의 내용

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    return (
        SUMMARIZE_LECTURE_SYSTEM_PROMPT,
        SUMMARIZE_LECTURE_USER_TEMPLATE.format(lecture_content=lecture_content),
    )


def get_summarize_image_prompt(subject_name: Optional[str] = None) -> tuple[str, str]:
    """
    이미지 요약 프롬프트 생성

    Args:
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    # 과목 정보 섹션 생성
    subject_info = get_subject_info(subject_name)
    if subject_info:
        subject_section = f"강의 과목 정보:\n{subject_info}\n\n"
    else:
        subject_section = ""

    system_prompt = SUMMARIZE_IMAGE_SYSTEM_PROMPT_TEMPLATE.format(
        subject_section=subject_section
    )

    user_prompt = SUMMARIZE_IMAGE_USER_TEMPLATE

    return (
        system_prompt,
        user_prompt,
    )


def get_answer_question_prompt(
    question: str,
    lecture_context: Optional[str] = None,
    has_image: bool = False,
    subject_name: Optional[str] = None,
) -> tuple[str, str]:
    """
    질문 답변 프롬프트 생성 (교수님 역할)

    Args:
        question: 학생의 질문
        lecture_context: 강의 맥락/컨텍스트 (선택)
        has_image: 이미지가 제공되는지 여부
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    # 과목 정보 섹션 생성
    subject_info = get_subject_info(subject_name)
    if subject_info:
        subject_section = (
            f"당신이 가르치는 과목은 다음과 같습니다:\n\n과목: {subject_info}\n\n"
        )
    else:
        subject_section = ""

    system_prompt = ANSWER_QUESTION_SYSTEM_PROMPT_TEMPLATE.format(
        subject_section=subject_section
    )

    if has_image:
        if lecture_context:
            user_prompt = ANSWER_QUESTION_WITH_CONTEXT_AND_IMAGE_TEMPLATE.format(
                question=question,
                lecture_context=lecture_context,
            )
        else:
            user_prompt = ANSWER_QUESTION_WITH_IMAGE_TEMPLATE.format(
                question=question,
                context_section="",
            )
    else:
        if lecture_context:
            user_prompt = ANSWER_QUESTION_WITH_CONTEXT_TEMPLATE.format(
                question=question,
                lecture_context=lecture_context,
                image_instruction="",
            )
        else:
            user_prompt = ANSWER_QUESTION_USER_TEMPLATE.format(
                question=question,
                context_section="",
                image_instruction="",
            )

    return (
        system_prompt,
        user_prompt,
    )



