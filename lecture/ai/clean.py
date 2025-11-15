"""
Question Cleaning Module

학생 질문 정제 기능
오타, 문법 오류 수정 및 명확성 개선
교수님 화면 캡쳐 이미지를 고려하여 정제
"""

from typing import Optional, Union, Any
from pathlib import Path

from .llm_client import LLMClient, get_default_client
from .prompt_templates import get_clean_question_prompt


def clean_question(
    question: str,
    image_path: Optional[Union[str, Path]] = None,
    image: Optional[Any] = None,
    llm_client: Optional[LLMClient] = None,
    temperature: float = 0.3,
    subject_name: Optional[str] = None,
) -> str:
    """
    학생 질문을 정제합니다. 교수님 화면 캡쳐 이미지를 고려하여 정제할 수 있습니다.

    Args:
        question: 정제할 원본 질문
        image_path: 교수님 화면 캡쳐 이미지 파일 경로 또는 URL (선택)
        image: PIL Image 객체 또는 이미지 데이터 (선택, image_path와 함께 사용 불가)
        llm_client: LLM 클라이언트 인스턴스 (없으면 기본 인스턴스 사용)
        temperature: 모델 온도 (낮을수록 일관성 있음)
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        정제된 질문 문자열

    Raises:
        ValueError: question이 비어있는 경우
        RuntimeError: LLM API 호출 실패 시
    """
    if not question or not question.strip():
        raise ValueError("질문이 비어있습니다.")

    if llm_client is None:
        # clean은 빠른 응답을 위해 flash-lite 사용
        llm_client = LLMClient(model="gemini-2.5-flash-lite")

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

    system_prompt, user_prompt = get_clean_question_prompt(
        question,
        has_image=has_image_input,
        subject_name=subject_name,
    )

    # 이미지가 포함된 경우 더 많은 토큰 필요
    max_output_tokens = 10000

    try:
        cleaned = llm_client.call(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_output_tokens,
            image_path=img_path_str,
            image=image,
        )
        return cleaned.strip()
    except Exception as e:  # pragma: no cover - 외부 API 예외
        raise RuntimeError(f"질문 정제 중 오류 발생: {str(e)}")


if __name__ == "__main__":  # pragma: no cover - 로컬 테스트 전용
    # 로컬 테스트
    test_question = "파이썬에서 리스트와 튜플의 차이점이 뭐에요? 그리고 언제 사용해야 하는지 궁금해요"
    try:
        result = clean_question(test_question)
        print(f"원본: {test_question}")
        print(f"정제: {result}")
    except Exception as e:
        print(f"오류: {e}")


