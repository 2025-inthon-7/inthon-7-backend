from __future__ import annotations

import json
from typing import Any, Dict

from channels.generic.websocket import AsyncWebsocketConsumer


class SessionConsumer(AsyncWebsocketConsumer):
    """
    수업(Session) 단위 WebSocket Consumer.

    - 접속 URL:
        ws://<host>/ws/session/<session_id>/teacher/
        ws://<host>/ws/session/<session_id>/student/

    - 그룹 이름:
        session_<session_id>_teacher
        session_<session_id>_student

    설계:
      - feedback (이해/어려움) -> 개별적으로 teacher 그룹에 브로드캐스트
      - new_question: 교수에게만 → teacher 그룹에 브로드캐스트
      - important / hard_alert: 학생에게만 → student 그룹에 브로드캐스트
    """

    async def connect(self) -> None:
        self.session_id: str = self.scope["url_route"]["kwargs"]["session_id"]
        self.role: str = self.scope["url_route"]["kwargs"]["role"]  # "teacher" or "student"

        # 역할별 그룹 이름
        self.group_name: str = f"session_{self.session_id}_{self.role}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_json(
            {
                "event": "connected",
                "session_id": self.session_id,
                "role": self.role,
            }
        )

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ) -> None:
        """
        클라이언트 → 서버 메시지.
        """
        if text_data is None:
            return

        try:
            data: Dict[str, Any] = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type: str | None = data.get("type")

        if msg_type == "ping":
            await self.send_json({"event": "pong"})

    # ------------------------------------------------------------------
    # 아래 메서드들은 REST 뷰에서 group_send(...)로 호출
    # ------------------------------------------------------------------

    async def feedback_message(self, event: Dict[str, Any]) -> None:
        """
        학생의 '이해했어요 / 어려워요' 반응을 교수에게 알림.
        teacher 그룹에 보내기
        """
        await self.send_json(
            {
                "event": "feedback",
                "feedback_type": event.get("feedback_type"),
                "created_at": event.get("created_at"),
            }
        )

    async def question_intent(self, event):
        """
        학생이 '질문하기' 버튼을 눌러 질문을 시작했을 때.
        교수(teacher) 그룹에 브로드캐스트.
        """
        await self.send_json(
            {
                "event": "question_intent",
                "question_id": event.get("question_id"),
                "created_at": event.get("created_at"),
            }
        )

    async def new_question(self, event: Dict[str, Any]) -> None:
        """
        교수에게 전달된 '정제된 질문 + AI 답변 + 캡처' 알림.
        teacher 그룹에 보내기
        """
        await self.send_json(
            {
                "event": "new_question",
                "question_id": event.get("question_id"),
                "text": event.get("text"),
                "ai_answer": event.get("ai_answer"),
                "capture_url": event.get("capture_url"),
            }
        )

    async def important_message(self, event: Dict[str, Any]) -> None:
        """
        교수의 '중요해요' 표시 → 학생에게만 브로드캐스트.
        student 그룹에 보내기
        """
        await self.send_json(
            {
                "event": "important",
                "note": event.get("note"),
                "capture_url": event.get("capture_url"),
            }
        )

    async def hard_alert(self, event: Dict[str, Any]) -> None:
        """
        프론트에서 threshold 넘었다고 판단해서 올린 '어려워요 구간' 캡처 알림.
        student 그룹에 보내기
        """
        await self.send_json(
            {
                "event": "hard_alert",
                "capture_url": event.get("capture_url"),
                "hard_ratio": event.get("hard_ratio"),
            }
        )

    # ------------------------------------------------------------------
    # 유틸
    # ------------------------------------------------------------------

    async def send_json(self, data: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(data))
