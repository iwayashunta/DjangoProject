from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chat/group/(?P<group_id>\w+)/$', consumers.GroupChatConsumer.as_asgi()),

    re_path(r'^ws/chat/dm/(?P<user_id>\w+)/$', consumers.DMChatConsumer.as_asgi()),
]