"""
ASGI config for Sotsuken_Portable_Project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# ★★★ この行をファイルの "上の方" に移動する ★★★
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sotsuken_Portable_Project.settings')

# ★★★ この行を新しく追加する ★★★
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import Sotsuken_Portable.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app, # ← 変数を使うように変更
    "websocket": AuthMiddlewareStack(
        URLRouter(
            Sotsuken_Portable.routing.websocket_urlpatterns
        )
    ),
})
