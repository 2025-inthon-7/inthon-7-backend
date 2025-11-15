from __future__ import annotations

import os

from celery import Celery

# 기본 Django settings 모듈 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inthon7.settings")

app = Celery("inthon7")

# Django settings에서 CELERY_ 로 시작하는 설정을 자동으로 로드
app.config_from_object("django.conf:settings", namespace="CELERY")

# 각 app의 tasks.py 자동 검색
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):  # pragma: no cover - 디버그용
    print(f"Request: {self.request!r}")


