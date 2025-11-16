# 나작교 - Real-time Lecture Support System

## 1. 프로젝트 개요

**나작교**은 실시간 강의 환경을 개선하기 위해 설계된 Django 기반 웹 애플리케이션입니다. 교수와 학생 간의 상호작용을 증진하고, AI를 활용하여 강의 중 발생하는 질문들을 효과적으로 관리하며, 강의의 질을 높이는 것을 목표로 합니다.

본 시스템은 웹소켓을 통해 실시간으로 학생들의 이해도 피드백, 질문 등을 교수에게 전달하며, Google Generative AI를 연동하여 학생들의 질문 내용을 명료하게 다듬는 기능을 제공합니다.

---

## 2. 핵심 기능

- **실시간 세션 관리**: 강의별로 고유한 세션을 생성하고, 교수와 학생이 참여하는 실시간 채널을 운영합니다.
- **이해도 피드백**: 학생들은 "이해했어요" / "어려워요" 버튼을 통해 현재 강의 내용에 대한 이해도를 즉시 표현할 수 있습니다.
- **대화형 Q&A 시스템**:
  - 학생은 강의 중 언제든지 익명으로 질문을 등록할 수 있습니다.
  - 등록된 질문은 AI가 먼저 분석하여 내용을 명료하게 다듬어줍니다(Text Cleaning).
  - 다른 학생들은 "나도 궁금해요" 기능을 통해 질문에 공감할 수 있습니다.
- **'중요해요' 순간 기록**: 교수는 강의 중 중요한 부분을 강조하고, 해당 시점의 화면 캡처를 저장하여 학생들에게 공유할 수 있습니다.
- **'어려워요' 구간 알림**: 다수의 학생이 특정 구간을 '어려워요'로 표시하면, 해당 구간이 자동으로 기록되어 리뷰가 필요한 부분임을 알려줍니다.
- **강의 요약 및 분석**: 세션 종료 후, 질문, 중요해요, 어려워요 등 주요 이벤트를 바탕으로 한 강의 요약/리포트를 제공합니다.

---

## 3. 기술 스택

| 분야                | 기술                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------- |
| **Backend**         | `Django`, `Django REST Framework`, `Django Channels`                                              |
| **Database**        | `SQLite3` (개발용)                                                                                |
| **Asynchronous Task**| `Celery`                                                                                          |
| **Cache & Broker**  | `Redis` (WebSocket Channel Layer, Celery Broker)                                                  |
| **AI**              | `Google Generative AI` (Gemini)                                                                   |
| **File Storage**    | `Google Cloud Storage` (강의 중 캡처 이미지 등 저장)                                              |
| **API Documentation**| `drf-spectacular` (Swagger UI)                                                                    |

---

## 4. 시스템 아키텍처

나작교은 다음과 같은 구성 요소들이 유기적으로 상호작용하여 동작합니다.

1.  **Django Web Server**:
    - REST API 엔드포인트를 제공하여 세션 관리, 질문 등록, 피드백 제출 등의 핵심 로직을 처리합니다.
    - `drf-spectacular`를 통해 API 문서를 자동으로 생성합니다.

2.  **Django Channels (WebSocket Server)**:
    - `Uvicorn` ASGI 서버 위에서 동작하며, 교수와 학생 클라이언트 간의 실시간 양방향 통신을 담당합니다.
    - `Redis`를 Channel Layer 백엔드로 사용하여 여러 서버 인스턴스 간의 메시지 브로드캐스팅을 지원합니다.

3.  **Celery (Task Queue)**:
    - 요약 생성 등 AI 모델 호출을 비동기적으로 처리합니다.
    - 예를 들어, 학생이 질문을 제출하면, Django 뷰는 질문 정제 및 AI 답변 생성 작업을 Celery에 위임하고 즉시 응답합니다. Celery 워커는 백그라운드에서 이 작업을 수행한 후, 결과를 WebSocket을 통해 클라이언트에게 전달합니다.

4.  **Google Cloud Platform**:
    - **Generative AI**: 학생 질문의 의미를 분석하고, 답변을 생성하는 데 사용됩니다.
    - **Cloud Storage**: 강의 중 생성되는 이미지 파일(스크린샷 등)을 저장하고 서빙하는 역할을 합니다.

---

## 5. 프로젝트 구조

- `inthon7/`: Django 프로젝트의 메인 설정 디렉토리입니다.
  - `settings.py`: 프로젝트의 모든 설정 (DB, Celery, Channels, GCP 등)을 관리합니다.
  - `urls.py`: 최상위 URL 라우팅을 담당합니다.
  - `asgi.py`, `wsgi.py`: 각각 ASGI, WSGI 서버의 진입점입니다.
- `lecture/`: 핵심 비즈니스 로직이 담긴 Django 앱입니다.
  - `models.py`: 데이터베이스 스키마(Course, Session, Question 등)를 정의합니다.
  - `views.py`: REST API 뷰 로직을 포함합니다.
  - `consumer.py`: WebSocket 통신 로직을 처리하는 `SessionConsumer`가 있습니다.
  - `serializers.py`: DRF를 위한 데이터 직렬화 로직을 정의합니다.
  - `tasks.py`: Celery 비동기 작업을 정의합니다.
  - `ai/`: Google Generative AI 연동 관련 모듈(클라이언트, 프롬프트 등)이 위치합니다.
- `requirements.txt`: 프로젝트에 필요한 Python 패키지 목록입니다.

---

## 6. 시작하기

### 6.1. 사전 요구사항

- Python 3.12+
- Redis Server

### 6.2. 설치 및 설정

1.  **저장소 클론**

    ```bash
    git clone https://github.com/your-repository/inthon7.git
    cd inthon7
    ```

2.  **가상 환경 생성 및 활성화**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **패키지 설치**

    ```bash
    pip install -r requirements.txt
    ```

4.  **환경 변수 설정**

    프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 채웁니다. Google Cloud Platform 서비스 계정 키 파일이 필요합니다.

    ```dotenv
    # .env

    # Google Cloud Storage 및 Generative AI API를 위한 서비스 계정 키 파일 경로
    GCS_CREDENTIALS_FILE=/path/to/your/gcp-service-account-key.json
    GEMINI_API_KEY=/path/to/your/gemini-api-key.json

    # Redis 서버 주소 (Celery, Channels에서 사용)
    REDIS_URL="redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL="redis://127.0.0.1:6379/1"
    CELERY_RESULT_BACKEND="redis://127.0.0.1:6379/2"
    ```

5.  **데이터베이스 마이그레이션**

    ```bash
    python manage.py migrate
    ```

6.  **(선택) 초기 데이터 로드**

    강의 정보 및 AI 프롬프트에 사용될 과목 정보를 데이터베이스에 로드합니다.

    ```bash
    # CSV 파일로부터 강의 목록 임포트
    python manage.py import_courses courses.csv

    # SubjectInfo 데이터 로드 (migration 파일 내부에 구현됨)
    # 0004_load_subjectinfo 마이그레이션이 이미 적용되었다면 생략 가능
    ```

### 6.3. 개발 서버 실행

애플리케이션을 실행하려면 Django 개발 서버, Celery 워커, 총 2개의 터미널이 필요합니다.

1.  **Celery Worker 실행**

    ```bash
    celery -A inthon7 worker --loglevel=info
    ```

2.  **Django Server 실행 (ASGI)**

    ```bash
    python manage.py runserver
    ```

이제 `http://127.0.0.1:8000` 에서 서버가 실행됩니다.

---

## 7. API 명세

### 7.1. REST API

본 프로젝트의 REST API 명세는 Swagger UI를 통해 제공됩니다. 개발 서버를 실행한 후, 아래 URL로 접속하여 모든 엔드포인트와 요청/응답 형식을 확인할 수 있습니다.

- **Swagger UI**: `http://127.0.0.1:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://127.0.0.1:8000/api/schema/redoc/`

### 7.2. WebSocket API

이 문서는 `lecture/consumer.py` 의 `SessionConsumer` 를 기준으로 한 **수업(Session) 단위 WebSocket 프로토콜**을 정리한 것입니다.
특히 **student 그룹용 브로드캐스트**와 **teacher 그룹용 브로드캐스트**를 명확하게 구분하는 데 초점을 둡니다.

#### 7.2.1. 공통 개념

- **세션 ID (`session_id`)**: 하나의 수업(강의)을 식별하는 UUID
- **역할 (`role`)**:
  - `teacher`: 교수/강의자 클라이언트
  - `student`: 학생 클라이언트
- **그룹 이름 규칙**
  - `session_<session_id>_teacher` — 해당 세션의 **교수 WebSocket 그룹**
  - `session_<session_id>_student` — 해당 세션의 **학생 WebSocket 그룹**

#### 7.2.2. WebSocket 엔드포인트

- **접속 URL 패턴**
  - `ws://<host>/ws/session/<session_id>/teacher/`
  - `ws://<host>/ws/session/<session_id>/student/`

#### 7.2.3. 연결 시 서버 응답 (`connected` 이벤트)

클라이언트가 위 엔드포인트로 연결을 맺으면, 서버는 다음과 같은 JSON 을 1회 전송합니다.

```json
{
  "event": "connected",
  "session_id": "<string>",
  "role": "teacher" | "student",
  "teacher_online": <boolean>
}
```

- **필드 설명**
  - `event`: 항상 `"connected"`
  - `session_id`: URL 상의 `<session_id>` 문자열
  - `role`: 현재 연결한 클라이언트의 역할 (`"teacher"` 또는 `"student"`)
  - `teacher_online`:
    - `role = "student"`인 경우: 현재 세션에 **교수 WebSocket 연결이 1개 이상 존재하는지**를 Redis 기반으로 조회한 결과
    - `role = "teacher"`인 경우: 현재 구현 상 기본적으로 `False` (학생에 한해서 의미 있는 값)


#### 7.2.4. 클라이언트 → 서버 메시지

- **ping**

  - 클라이언트에서 보냄:

    ```json
    {
      "type": "ping"
    }
    ```

  - 서버 응답:

    ```json
    {
      "event": "pong"
    }
    ```

  - 용도: 단순 연결 상태 확인 (keep-alive 용도 포함)


#### 7.2.5. 서버 → 클라이언트 브로드캐스트 이벤트 정리

아래 이벤트들은 모두 **서버(REST 뷰 등)에서 `channel_layer.group_send(...)` 를 통해 호출**되고,
`SessionConsumer` 의 핸들러 메서드로 라우팅된 뒤, 최종적으로 **각 역할 그룹(student / teacher)에 브로드캐스트**됩니다.

##### 요약 표 (이벤트 vs 브로드캐스트 대상 그룹)

- **teacher 그룹으로 가는 이벤트 (교수만 수신)**
  - `feedback` — 학생의 이해도 피드백
  - `question_intent` — 학생이 질문을 시작했음을 알림

- **student 그룹으로 가는 이벤트 (학생만 수신)**
  - `question_capture` — 특정 질문에 대한 캡처 도착
  - `important` — 교수의 “중요해요” 구간 표시
  - `hard_alert` — “어려워요” 비율이 threshold 를 넘은 구간
  - `teacher_presence` — 교수 접속 여부(온라인/오프라인) 상태 변경

- **teacher + student 모두에게 가는 이벤트 (교수, 학생 모두 수신)**
  - `new_question` — 학생의 질문 + 캡처가 모두에게 공유됨
  - `question_like_update` — '나도 궁금해요' 카운트 업데이트
  - `session_ended` — 강의(세션) 종료

##### teacher 그룹용 브로드캐스트 상세

이 섹션의 모든 이벤트는 **`session_<session_id>_teacher` 그룹에 속한 WebSocket(교수)** 에게만 전송됩니다.

- **1) feedback**

  - 의미: 학생의 `"이해했어요 / 어려워요"` 등의 즉각 피드백 결과를 교수에게 전달
  - 핸들러: `feedback_message`
  - 페이로드 예시:

    ```json
    {
      "event": "feedback",
      "feedback_type": "OK" | "HARD",
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

- **2) question_intent**

  - 의미: 학생이 “질문하기” 버튼을 눌러 질문을 시작했을 때
  - 핸들러: `question_intent`
  - 페이로드 예시:

    ```json
    {
      "event": "question_intent",
      "question_id": 123,
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

##### student 그룹용 브로드캐스트 상세

이 섹션의 모든 이벤트는 **`session_<session_id>_student` 그룹에 속한 WebSocket(학생)** 에게만 전송됩니다.

- **1) question_capture**

  - 의미: 교수 측에서 특정 질문에 대해 업로드한 PPT 캡처가 학생들에게 공유될 때
  - 핸들러: `question_capture`
  - 페이로드 예시:

    ```json
    {
      "event": "question_capture",
      "question_id": 123,
      "capture_url": "https://example.com/capture.png",
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

- **2) important**

  - 의미: 교수의 “중요해요” 표시가 학생들에게 브로드캐스트될 때
  - 핸들러: `important_message`
  - 페이로드 예시:

    ```json
    {
      "event": "important",
      "note": "이 부분 꼭 다시 복습하세요",
      "capture_url": "https://example.com/important.png",
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

- **3) teacher_presence**

  - 의미: 교수 WebSocket 접속/해제에 따라 **교수 온라인/오프라인 상태가 변경**되었음을 학생에게 알림
  - 핸들러: `teacher_presence`
  - 서버 내부 흐름:
    - 교수 연결/해제 시:
      - `_mark_teacher_connected()` / `_mark_teacher_disconnected()` 로 Redis 집합(`session:{session_id}:teachers`) 관리
      - `_broadcast_teacher_presence()` 로 `session_<session_id>_student` 그룹에 브로드캐스트
  - 페이로드 예시:

    ```json
    {
      "event": "teacher_presence",
      "is_online": true,
      "changed_at": "2025-11-15T12:34:56.789Z"
    }
    ```


##### 공통 브로드캐스트 상세 (교수, 학생 모두 수신)

이 섹션의 모든 이벤트는 **`teacher` 및 `student` 그룹 모두에게** 전송됩니다.

- **1) new_question**

  - 의미: 정제된 질문 내용과 관련 캡처가 모두에게 도착했음을 알림
  - 핸들러: `new_question`
  - 페이로드 예시:

    ```json
    {
      "event": "new_question",
      "question_id": 123,
      "cleaned_text": "질문의 정제된 텍스트 내용",
      "capture_url": "https://example.com/capture.png",
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

- **2) question_like_update**

  - 의미: '나도 궁금해요' 카운트가 업데이트되었음을 알림
  - 핸들러: `question_like_update`
  - 페이로드 예시:

    ```json
    {
      "event": "question_like_update",
      "question_id": 123,
      "like_count": 5
    }
    ```

- **3) hard_alert**

  - 의미: 프론트에서 “어려워요” 비율이 특정 threshold 를 넘었다고 판단해, 해당 구간의 캡처를 학생에게 알릴 때
  - 핸들러: `hard_alert`
  - 페이로드 예시:

    ```json
    {
      "event": "hard_alert",
      "capture_url": "https://example.com/hard.png",
      "created_at": "2025-11-15T12:34:56.789Z"
    }
    ```

- **4) session_ended**

  - 의미: 교수가 세션을 종료했음을 알림. 클라이언트는 이 이벤트를 받으면 연결을 종료해야 함.
  - 핸들러: `session_ended`
  - 페이로드 예시:

    ```json
    {
      "event": "session_ended"
    }
    ```
