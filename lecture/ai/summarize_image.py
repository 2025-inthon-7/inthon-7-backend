"""
Image Summarization Module

교수님이 중요하다고 마크한 화면 이미지를 LLM에 넣어 1줄 요약하는 기능
현재 프롬프트를 고려하여 요약 생성
"""

from typing import Optional, Union, Any
from pathlib import Path

from .llm_client import LLMClient, get_default_client
from .prompt_templates import get_summarize_image_prompt


def summarize_image(
    image_path: Optional[Union[str, Path]] = None,
    image: Optional[Any] = None,
    llm_client: Optional[LLMClient] = None,
    temperature: float = 0.3,
    subject_name: Optional[str] = None,
) -> str:
    """
    교수님이 중요하다고 마크한 화면 이미지를 LLM에 넣어 1줄로 요약합니다.

    Args:
        image_path: 교수님 화면 캡쳐 이미지 파일 경로 또는 URL (필수, image와 함께 사용 불가)
        image: PIL Image 객체 또는 이미지 데이터 (필수, image_path와 함께 사용 불가)
        llm_client: LLM 클라이언트 인스턴스 (없으면 기본 인스턴스 사용)
        temperature: 모델 온도 (기본값: 0.3, 낮을수록 일관성 있음)
        subject_name: 과목명 (예: "자료구조", "알고리즘" 등) (선택)

    Returns:
        1줄 요약 문자열

    Raises:
        ValueError: image_path와 image가 모두 없는 경우
        RuntimeError: LLM API 호출 실패 시
    """
    if not image_path and not image:
        raise ValueError("image_path 또는 image 중 하나는 필수입니다.")

    if llm_client is None:
        llm_client = get_default_client()

    # 이미지 경로를 문자열로 변환
    img_path_str: Optional[str] = None

    # image_path가 빈 문자열이거나 None인 경우 처리
    if image_path:
        if isinstance(image_path, str):
            img_path_str = image_path.strip()
        else:
            img_path_str = str(image_path)

        if not img_path_str:  # 빈 문자열인 경우
            img_path_str = None
            if not image:
                raise ValueError("image_path 또는 image 중 하나는 필수입니다.")

    if img_path_str:
        img_path_str = (
            str(image_path) if isinstance(image_path, Path) else img_path_str
        )

    system_prompt, user_prompt = get_summarize_image_prompt(
        subject_name=subject_name,
    )

    # 이미지 요약은 간결하게 1줄이므로 적당한 토큰 수 설정
    max_output_tokens = 500

    try:
        summary = llm_client.call(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_output_tokens,
            image_path=img_path_str,
            image=image,
        )
        return summary.strip()
    except Exception as e:  # pragma: no cover - 외부 API 예외
        raise RuntimeError(f"이미지 요약 중 오류 발생: {str(e)}")


if __name__ == "__main__":  # pragma: no cover - 로컬 테스트 전용
    # 로컬 테스트
    test_image_path = "path/to/test/image.png"
    try:
        result = summarize_image(image_path=test_image_path)
        print(f"이미지 요약: {result}")
    except Exception as e:
        print(f"오류: {e}")

