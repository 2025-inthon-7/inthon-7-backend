from __future__ import annotations

import logging
from typing import Optional

from celery import shared_task
from django.db import close_old_connections

from .models import ImportantMoment
from .views import ai_summarize_important_image

logger = logging.getLogger(__name__)


@shared_task
def generate_important_summary_task(
    moment_id: int,
    session_id_str: str,
    raw_note: str,
) -> None:
    """
    Celery 작업: 중요한 구간 이미지에 대해 LLM 요약을 생성하고,
    DB의 note를 업데이트한다. (브로드캐스트는 view에서 즉시 수행)
    """
    try:
        # 스레드/워커 내에서 안전하게 DB 연결 사용
        close_old_connections()

        moment_obj = ImportantMoment.objects.select_related("session__course").get(id=moment_id)
        session_obj = moment_obj.session

        auto_summary: Optional[str] = None
        if getattr(moment_obj, "screenshot_image", None):
            image_url = getattr(moment_obj.screenshot_image, "url", None)
            logger.info(
                "[AI DEBUG] generate_important_summary_task before ai_summarize_important_image image_url=%s",
                image_url,
            )
            auto_summary = ai_summarize_important_image(
                image_path=image_url,
                subject_name=session_obj.course.code[:7],
            )
        else:
            logger.info(
                "[AI DEBUG] generate_important_summary_task: no screenshot_image, skipping LLM"
            )

        # note와 자동 요약 결합 로직
        if raw_note and auto_summary:
            final_note_local = f"{raw_note} | {auto_summary}"
        elif auto_summary:
            final_note_local = auto_summary
        else:
            final_note_local = raw_note

        logger.info(
            "[AI DEBUG] generate_important_summary_task final_note decided auto_summary_present=%s final_note=%r",
            bool(auto_summary),
            final_note_local,
        )

        if final_note_local != moment_obj.note:
            moment_obj.note = final_note_local
            moment_obj.save(update_fields=["note"])
    except Exception as e:  # pragma: no cover - 백그라운드 예외 로깅용
        logger.error("[AI DEBUG] generate_important_summary_task ERROR: %s", e)


