from __future__ import annotations

import json
from typing import Any, Dict

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.utils import timezone

try:
    import redis.asyncio as redis  # type: ignore
except Exception:
    redis = None


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

        # 교수 접속 여부를 Redis에 기록 (멀티 프로세스/서버에서도 일관되게 확인 가능)
        if self.role == "teacher":
            await self._mark_teacher_connected()
            # 옵션: 학생 그룹에 "교수 온라인" 상태 브로드캐스트 가능
            await self._broadcast_teacher_presence()

        # 학생이 처음 접속할 때, 현재 교수 온라인 여부를 함께 내려줌
        teacher_online = False
        if self.role == "student":
            teacher_online = await self._is_teacher_online()

        await self.send_json(
            {
                "event": "connected",
                "session_id": self.session_id,
                "role": self.role,
                "teacher_online": teacher_online,
            }
        )

    async def disconnect(self, close_code: int) -> None:
        # 교수인 경우, 접속 해제 시 Redis 상태 업데이트
        if getattr(self, "role", None) == "teacher":
            await self._mark_teacher_disconnected()
            await self._broadcast_teacher_presence()

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
        교수에게 전달된 '정제된 질문 + 캡처' 알림.
        교수/학생 그룹 모두에게 브로드캐스트
        """
        await self.send_json(
            {
                "event": "new_question",
                "question_id": event.get("question_id"),
                "cleaned_text": event.get("cleaned_text"),
                "capture_url": event.get("capture_url"),
                "created_at": event.get("created_at"),
            }
        )

    async def question_capture(self, event: Dict[str, Any]) -> None:
        """
        교수 쪽에서 특정 질문에 대한 PPT 캡처를 업로드했을 때.
        student 그룹에 브로드캐스트.
        """
        await self.send_json(
            {
                "event": "question_capture",
                "question_id": event.get("question_id"),
                "capture_url": event.get("capture_url"),
                "created_at": event.get("created_at"),
            }
        )

    async def question_like_update(self, event: Dict[str, Any]) -> None:
        """
        '나도 궁금해요' 카운트 업데이트.
        교수/학생 그룹 모두에게 브로드캐스트.
        """
        await self.send_json(
            {
                "event": "question_like_update",
                "question_id": event.get("question_id"),
                "like_count": event.get("like_count"),
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
                "created_at": event.get("created_at"),
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
                "created_at": event.get("created_at"),
            }
        )

    async def session_ended(self, event: Dict[str, Any]) -> None:
        """
        교수가 세션을 종료했을 때.
        모든 클라이언트(교수/학생)에게 브로드캐스트.
        """
        await self.send_json({"event": "session_ended"})
        await self.close()

    # ------------------------------------------------------------------
    # 유틸
    # ------------------------------------------------------------------

    async def send_json(self, data: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(data))

    # ------------------------------------------------------------------
    # 교수 접속 여부 관련 유틸
    # ------------------------------------------------------------------

    @property
    def _redis(self):
        """
        RedisChannelLayer와 동일한 Redis 인스턴스를 사용해
        '교수 접속 여부'를 저장/조회하기 위한 클라이언트.
        """
        if redis is None:
            return None
        if not hasattr(self, "__redis_client"):
            url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
            setattr(self, "__redis_client", redis.from_url(url))
        return getattr(self, "__redis_client")

    async def _mark_teacher_connected(self) -> None:
        """
        현재 세션에 교수(teacher)가 접속했음을 Redis에 기록.
        여러 프로세스 / 서버에서 동시에 접근해도 일관되게 관리 가능.
        """
        if self._redis is None:
            return
        key = f"session:{self.session_id}:teachers"
        await self._redis.sadd(key, self.channel_name)

    async def _mark_teacher_disconnected(self) -> None:
        """
        현재 세션에서 해당 교수 connection을 제거.
        """
        if self._redis is None:
            return
        key = f"session:{self.session_id}:teachers"
        await self._redis.srem(key, self.channel_name)

    async def _is_teacher_online(self) -> bool:
        """
        현재 세션에 교수(teacher)가 하나 이상 접속해 있는지 여부.
        - WebSocket 핸들러나 REST API(별도 view에서 동일 키를 사용)에서 재활용 가능.
        """
        if self._redis is None:
            return False
        key = f"session:{self.session_id}:teachers"
        count = await self._redis.scard(key)
        return bool(count and count > 0)

    async def _broadcast_teacher_presence(self) -> None:
        """
        교수 접속 여부가 변할 때마다 학생 그룹에 브로드캐스트하고 싶을 경우 사용하는 유틸.
        프론트에서 받아서 '교수 온라인/오프라인' 표시 가능.
        """
        is_online = await self._is_teacher_online()
        # 학생 그룹 이름은 session_<session_id>_student
        student_group = f"session_{self.session_id}_student"
        await self.channel_layer.group_send(
            student_group,
            {
                "type": "teacher_presence",
                "is_online": is_online,
                "changed_at": timezone.now().isoformat(),
            },
        )

    async def teacher_presence(self, event: Dict[str, Any]) -> None:
        """
        학생 클라이언트가 받는 '교수 접속 여부' 이벤트.
        """
        await self.send_json(
            {
                "event": "teacher_presence",
                "is_online": event.get("is_online", False),
                "changed_at": event.get("changed_at"),
            }
        )
