"""
ASGI config for SecureApprove.

This sets up Django Channels so we can handle both HTTP and WebSocket
connections (used by the internal chat).
"""

import os

from django.core.asgi import get_asgi_application

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import apps.chat.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                apps.chat.routing.websocket_urlpatterns,
            )
        ),
    }
)

