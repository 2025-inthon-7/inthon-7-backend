from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    # UUID 기반 session_id + 역할(role: teacher/student)
    re_path(
        r"ws/session/(?P<session_id>[0-9a-fA-F\-]+)/(?P<role>teacher|student)/$",
        consumer.SessionConsumer.as_asgi(),
    ),
]