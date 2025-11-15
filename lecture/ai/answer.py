"""
Question Answering Module

교수님 역할로 학생 질문에 대한 답변 생성 기능
강의 맥락을 고려하여 교육적이고 명확한 답변 제공
교수님 화면 캡쳐 이미지를 고려하여 답변 생성
"""

from typing import Optional, Union, Any
from pathlib import Path

from .llm_client import LLMClient, get_default_client
from .prompt_templates import get_answer_question_prompt


def answer_question(
    question: str,
    lecture_context: Optional[str] = None,
    image_path: Optional[Union[str, Path]] = None,
    image: Optional[Any] = None,
    llm_client: Optional[LLMClient] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = 4096,
    subject_name: Optional[str] = None,
) -> str:
    """
    학생 질문에 대해 교수님 역할로 답변을 생성합니다. 교수님 화면 캡쳐 이미지를 고려하여 답변할 수 있습니다.

    Args:
        question: 학생의 질문
        lecture_context: 강의 맥락/컨텍스트 (선택) - 강의 내용, 이전 대화 등
        image_path: 교수님 화면 캡쳐 이미지 파일 경로 또는 URL (선택)
        image: PIL Image 객체 또는 이미지 데이터 (선택, image_path와 함께 사용 불가)
        llm_client: LLM 클라이언트 인스턴스 (없으면 기본 인스턴스 사용)
        temperature: 모델 온도 (기본값: 0.7)
        max_tokens: 최대 토큰 수 (기본값: 4096, 이미지 포함 시 자동 증가)
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        교수님 역할의 답변 문자열

    Raises:
        ValueError: question이 비어있는 경우
        RuntimeError: LLM API 호출 실패 시
    """
    if not question or not question.strip():
        raise ValueError("질문이 비어있습니다.")

    if llm_client is None:
        llm_client = get_default_client()

    # 이미지 경로를 문자열로 변환
    img_path_str: Optional[str] = None
    has_image_input = bool(image_path or image)

    # image_path가 빈 문자열이거나 None인 경우 처리
    if image_path:
        if isinstance(image_path, str):
            img_path_str = image_path.strip()
        else:
            img_path_str = str(image_path)

        if not img_path_str:  # 빈 문자열인 경우
            img_path_str = None
            has_image_input = bool(image)  # image 객체만 확인
        else:
            img_path_str = (
                str(image_path) if isinstance(image_path, Path) else img_path_str
            )

    # 이미지가 포함된 경우 더 많은 토큰 필요
    if has_image_input:
        max_output_tokens = 8192 if (not max_tokens or max_tokens < 8192) else max_tokens
    else:
        max_output_tokens = max_tokens or 4096

    system_prompt, user_prompt = get_answer_question_prompt(
        question,
        lecture_context,
        has_image=has_image_input,
        subject_name=subject_name,
    )

    try:
        answer = llm_client.call(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_output_tokens,
            image_path=img_path_str,
            image=image,
        )
        return answer.strip()
    except Exception as e:  # pragma: no cover - 외부 API 예외
        raise RuntimeError(f"질문 답변 생성 중 오류 발생: {str(e)}")


if __name__ == "__main__":  # pragma: no cover - 로컬 테스트 전용
    # 로컬 테스트
    test_question = "파이썬에서 리스트와 튜플의 차이점이 뭐에요?"
    test_context = """
    오늘 강의에서는 파이썬의 기본 데이터 구조에 대해 배웠습니다.
    리스트는 순서가 있는 가변 데이터 구조이고,
    튜플은 순서가 있지만 불변 데이터 구조입니다.
    """

    try:
        answer = answer_question(test_question, test_context)
        print(f"질문: {test_question}")
        print(f"\n답변:\n{answer}")
    except Exception as e:
        print(f"오류: {e}")


