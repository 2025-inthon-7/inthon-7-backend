"""
LLM Client Module

Google Gemini API 호출을 위한 공용 클라이언트
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union

try:
    import google.generativeai as genai  # type: ignore
except ImportError:
    raise ImportError(
        "google-generativeai 패키지가 설치되지 않았습니다. "
        "다음 명령어로 설치하세요: pip install google-generativeai"
    )

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    raise ImportError(
        "python-dotenv 패키지가 설치되지 않았습니다. "
        "다음 명령어로 설치하세요: pip install python-dotenv"
    )

# 환경 변수 로드 (현재 디렉토리와 상위 디렉토리에서 .env 파일 찾기)
current_dir = Path(__file__).parent
env_paths = [
    current_dir / ".env",  # lecture/ai/.env
    current_dir.parent / ".env",  # 프로젝트 루트/.env
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
else:
    # .env 파일이 없어도 환경변수에서 직접 로드 시도
    load_dotenv()


class LLMClient:
    """Google Gemini API 클라이언트"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        LLMClient 초기화

        Args:
            api_key: Google Gemini API 키 (없으면 환경변수에서 로드)
            model: 사용할 모델명 (기본값: gemini-2.5-flash)
                  옵션: gemini-2.5-flash, gemini-2.5-pro-preview-03-25, gemini-2.5-flash-preview-05-20
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API 키가 필요합니다. 환경변수 GEMINI_API_KEY 또는 GOOGLE_API_KEY를 설정하거나 "
                "api_key를 전달하세요."
            )

        # Gemini API 구성
        genai.configure(api_key=self.api_key)
        self.model_name = model

        # models/ 접두사 제거 (자동으로 붙음)
        if self.model_name.startswith("models/"):
            self.model_name = self.model_name.replace("models/", "")

        try:
            self.model = genai.GenerativeModel(model_name=self.model_name)
        except Exception as e:
            # 모델 이름이 잘못되었을 경우 사용 가능한 모델 자동 감지
            print(f"경고: 모델 {model}을 사용할 수 없습니다. 사용 가능한 모델을 찾는 중... (오류: {e})")
            try:
                available_models = [
                    m.name
                    for m in genai.list_models()
                    if "generateContent" in m.supported_generation_methods
                ]
                if available_models:
                    # gemini-2.5-flash 또는 가장 최신 모델 선택
                    fallback_model = None
                    for m in available_models:
                        model_name = m.replace("models/", "")
                        if "gemini-2.5-flash" in model_name and "preview" not in model_name:
                            fallback_model = model_name
                            break
                    if not fallback_model:
                        fallback_model = available_models[0].replace("models/", "")

                    print(f"사용 가능한 모델로 변경: {fallback_model}")
                    self.model_name = fallback_model
                    self.model = genai.GenerativeModel(model_name=self.model_name)
                else:
                    raise ValueError("사용 가능한 모델을 찾을 수 없습니다.")
            except Exception as e2:
                raise ValueError(f"모델 초기화 실패: {e2}")

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        image_path: Optional[str] = None,
        image: Optional[Any] = None,
        **kwargs,
    ) -> str:
        """
        Gemini API 호출 (텍스트 및 이미지 지원)

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택) - Gemini는 system_instruction로 전달
            temperature: 모델 온도 (0.0-2.0)
            max_tokens: 최대 토큰 수 (max_output_tokens로 변환)
            image_path: 이미지 파일 경로 또는 URL (선택)
            image: PIL Image 객체 또는 이미지 데이터 (선택)
            **kwargs: 기타 API 파라미터

        Returns:
            LLM 응답 텍스트
        """
        # -----------------------------
        # 디버그용 프롬프트 출력 TODO: 나중에 제거
        # -----------------------------
        try:
            print("\n[AI DEBUG] ===== LLM CALL START =====")
            print(f"[AI DEBUG] model_name: {self.model_name}")
            print(f"[AI DEBUG] temperature: {temperature}, max_tokens: {max_tokens}")
            if system_prompt:
                print("[AI DEBUG] --- system_prompt ---")
                print(system_prompt)
                print("[AI DEBUG] --- end system_prompt ---")
            print("[AI DEBUG] --- user_prompt ---")
            print(prompt)
            print("[AI DEBUG] --- end user_prompt ---")
            print(f"[AI DEBUG] image_path: {image_path}, has_image: {bool(image_path or image)}")
            print("[AI DEBUG] =====  LLM CALL END (prompt dump) =====\n")
        except Exception:
            # 디버그 출력 자체가 실패하더라도 LLM 호출은 계속 진행
            pass

        # 시스템 프롬프트가 있으면 모델에 전달
        if system_prompt:
            model = genai.GenerativeModel(
                model_name=self.model_name, system_instruction=system_prompt
            )
        else:
            model = self.model

        # 생성 설정 - dict로 전달
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            **kwargs,
        }

        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        # 이미지 처리
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            raise ImportError(
                "PIL (Pillow) 패키지가 설치되지 않았습니다. "
                "이미지 처리를 위해 다음 명령어로 설치하세요: pip install Pillow"
            )

        content_parts: list[Union[str, Any]] = [prompt]

        # image_path가 빈 문자열이거나 None이 아닌 경우만 처리
        if image_path and str(image_path).strip():
            try:
                # URL인 경우 requests로 다운로드 시도
                if str(image_path).startswith(("http://", "https://")):
                    try:
                        import requests
                        from io import BytesIO

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        }
                        response = requests.get(image_path, headers=headers, timeout=10)
                        response.raise_for_status()
                        img = Image.open(BytesIO(response.content))
                        content_parts.append(img)
                    except ImportError:
                        raise ValueError(
                            "URL 이미지를 사용하려면 requests 패키지가 필요합니다: pip install requests"
                        )
                    except Exception as e:
                        raise ValueError(f"URL에서 이미지를 다운로드하는데 실패했습니다: {e}")
                else:
                    # 파일 경로에서 이미지 로드
                    img_path = Path(image_path)
                    if not img_path.exists():
                        raise ValueError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
                    img = Image.open(img_path)
                    content_parts.append(img)
            except Exception as e:
                raise ValueError(f"이미지 파일 로드 실패 ({image_path}): {e}")

        try:
            response = model.generate_content(
                content_parts,
                generation_config=generation_config,
            )

            # finish_reason 확인 (1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER)
            finish_reason = None
            if getattr(response, "candidates", None) and len(response.candidates) > 0:
                finish_reason = response.candidates[0].finish_reason

                if finish_reason == 3:
                    raise RuntimeError(
                        "응답이 안전 필터링으로 차단되었습니다. 프롬프트를 수정해주세요."
                    )
                elif finish_reason == 4:
                    raise RuntimeError(
                        "응답이 인용 필터링으로 차단되었습니다. 프롬프트를 수정해주세요."
                    )

            # 응답 텍스트 추출 시도
            response_text: Optional[str] = None
            try:
                response_text = response.text  # type: ignore[assignment]
            except (ValueError, AttributeError) as e:
                # response.text 접근 실패 시 candidates에서 직접 추출 시도
                if getattr(response, "candidates", None) and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if getattr(candidate, "content", None) and candidate.content.parts:
                        # parts에서 텍스트 추출
                        text_parts: list[str] = []
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            response_text = "".join(text_parts)

                if not response_text:
                    # finish_reason에 따른 에러 메시지
                    if finish_reason == 2:
                        raise RuntimeError(
                            "응답이 최대 토큰 수를 초과하여 잘렸습니다. max_tokens를 늘려주세요."
                        )
                    elif finish_reason:
                        raise RuntimeError(
                            "Gemini API가 유효한 응답을 반환하지 못했습니다. "
                            f"(finish_reason: {finish_reason})"
                        )
                    else:
                        raise RuntimeError(f"Gemini API 응답 처리 실패: {str(e)}")

            if not response_text or not response_text.strip():
                if finish_reason == 2:
                    raise RuntimeError(
                        "응답이 최대 토큰 수를 초과하여 잘렸습니다. max_tokens를 늘려주세요."
                    )
                elif finish_reason:
                    raise RuntimeError(
                        f"Gemini API가 빈 응답을 반환했습니다. (finish_reason: {finish_reason})"
                    )
                else:
                    raise RuntimeError("Gemini API가 빈 응답을 반환했습니다.")

            return response_text.strip()
        except Exception as e:  # pragma: no cover - 외부 API 예외
            raise RuntimeError(f"Gemini API 호출 중 오류 발생: {str(e)}")

    def call_with_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        JSON 형식 응답을 받는 Gemini API 호출

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 모델 온도
            **kwargs: 기타 API 파라미터

        Returns:
            파싱된 JSON 딕셔너리
        """
        # JSON 응답을 요청하는 프롬프트 추가
        json_prompt = (
            f"{prompt}\n\n응답은 반드시 유효한 JSON 형식으로만 작성해주세요. "
            "추가 설명 없이 JSON만 반환하세요."
        )

        response_text = self.call(
            prompt=json_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

        # JSON 파싱 시도
        try:
            # 응답에서 JSON 부분만 추출 (마크다운 코드 블록 제거)
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]  # ```json 제거
            elif text.startswith("```"):
                text = text[3:]  # ``` 제거

            if text.endswith("```"):
                text = text[:-3]  # ``` 제거

            text = text.strip()

            # JSON이 중간에 잘린 경우 마지막 불완전한 키-값 쌍 제거
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                # JSON이 불완전한 경우 재시도
                if e.pos is not None:
                    # 불완전한 부분 제거 후 재시도
                    partial_text = text[: e.pos]
                    # 마지막 불완전한 키-값 쌍 찾기
                    last_comma = partial_text.rfind(",")
                    last_brace = partial_text.rfind("}")
                    if last_brace > last_comma:
                        # 마지막 불완전한 키-값 쌍 제거
                        partial_text = partial_text[: last_brace + 1]
                        try:
                            return json.loads(partial_text)
                        except Exception:
                            pass

                # 모든 시도 실패 시 원본 오류 발생
                raise ValueError(
                    f"JSON 파싱 실패: {str(e)}\n응답 (처음 500자): {response_text[:500]}"
                )
        except json.JSONDecodeError as e:
            raise ValueError(
                f"JSON 파싱 실패: {str(e)}\n응답 (처음 500자): {response_text[:500]}"
            )


# 싱글톤 인스턴스 (선택적 사용)
_default_client: Optional[LLMClient] = None


def get_default_client() -> LLMClient:
    """기본 LLM 클라이언트 인스턴스 반환"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


