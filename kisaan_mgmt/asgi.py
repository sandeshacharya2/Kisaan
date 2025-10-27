# kisaan_mgmt/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing  # We’ll create this next

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kisaan_mgmt.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Handles traditional HTTP
    "websocket": AuthMiddlewareStack(  # Handles WebSocket connections
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})