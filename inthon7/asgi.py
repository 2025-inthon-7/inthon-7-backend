import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import lecture.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inthon7.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(lecture.routing.websocket_urlpatterns)
    ),
})