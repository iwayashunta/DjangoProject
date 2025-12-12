from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 位置情報用のルートを追加
    re_path(r"ws/location/$", consumers.LocationConsumer.as_asgi()),

    # グループチャット（UUID対応 & 'all'対応）
    # \w+ だとハイフンが含まれない場合があるので、[^/]+ (スラッシュ以外全て) にするのが確実
    re_path(r'ws/chat/group/(?P<group_id>[^/]+)/$', consumers.GroupChatConsumer.as_asgi()),

    # DMチャット（UUID対応）
    # ★ここを修正: \d+ から [^/]+ に変更
    re_path(r'ws/chat/dm/(?P<user_id>[^/]+)/$', consumers.DMChatConsumer.as_asgi()),
]