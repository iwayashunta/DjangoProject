from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 位置情報用のルートを追加
    re_path(r"ws/location/$", consumers.LocationConsumer.as_asgi()),

    # 既存のチャット・DM用のルート
    re_path(r'^ws/chat/group/(?P<group_id>\w+)/$', consumers.GroupChatConsumer.as_asgi()),
    re_path(r'^ws/chat/dm/(?P<user_id>\w+)/$', consumers.DMChatConsumer.as_asgi()),
]