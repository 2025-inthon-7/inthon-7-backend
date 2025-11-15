from __future__ import annotations

"""
inthon7 패키지 초기화 모듈.

Celery 앱을 자동으로 로드하기 위해 여기에서 가져온다.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)


