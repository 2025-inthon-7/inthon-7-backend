## InThon WebSocket API 명세

이 문서는 `lecture/consumer.py` 의 `SessionConsumer` 를 기준으로 한 **수업(Session) 단위 WebSocket 프로토콜**을 정리한 것입니다.  
특히 **student 그룹용 브로드캐스트**와 **teacher 그룹용 브로드캐스트**를 명확하게 구분하는 데 초점을 둡니다.


### 1. 공통 개념

- **세션 ID (`session_id`)**: 하나의 수업(강의)을 식별하는 UUID
- **역할 (`role`)**:  
  - `teacher`: 교수/강의자 클라이언트
  - `student`: 학생 클라이언트
- **그룹 이름 규칙**
  - `session_<session_id>_teacher` — 해당 세션의 **교수 WebSocket 그룹**
  - `session_<session_id>_student` — 해당 세션의 **학생 WebSocket 그룹**


### 2. WebSocket 엔드포인트

- **접속 URL 패턴**
  - `ws://<host>/ws/session/<session_id>/teacher/`
  - `ws://<host>/ws/session/<session_id>/student/`



### 3. 연결 시 서버 응답 (`connected` 이벤트)

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


### 4. 클라이언트 → 서버 메시지

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


### 5. 서버 → 클라이언트 브로드캐스트 이벤트 정리

아래 이벤트들은 모두 **서버(REST 뷰 등)에서 `channel_layer.group_send(...)` 를 통해 호출**되고,  
`SessionConsumer` 의 핸들러 메서드로 라우팅된 뒤, 최종적으로 **각 역할 그룹(student / teacher)에 브로드캐스트**됩니다.

#### 5.1 요약 표 (이벤트 vs 브로드캐스트 대상 그룹)

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


#### 5.2 teacher 그룹용 브로드캐스트 상세

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


#### 5.3 student 그룹용 브로드캐스트 상세

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


#### 5.4 공통 브로드캐스트 상세 (교수, 학생 모두 수신)

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
