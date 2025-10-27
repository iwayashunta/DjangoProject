import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, User, Group


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. URLからグループIDを取得
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'chat_{self.group_id}'
        self.user = self.scope['user']

        # (セキュリティチェック) ユーザーがこのグループに所属しているか確認
        if not await self.is_user_in_group(self.user, self.group_id):
            await self.close()
            return

        # 2. グループに参加
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # グループから離脱
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # WebSocketからメッセージを受信したときの処理
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']

        # 3. メッセージをデータベースに保存
        new_message = await self.save_message(self.user, self.group_id, message_content)

        # 4. グループ内の全員にメッセージを送信
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': new_message.content,
                'sender': new_message.sender.full_name or new_message.sender.email
            }
        )

    # グループからメッセージを受信したときの処理
    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']

        # 5. WebSocketにメッセージを送信
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
        }))

    # --- データベース操作を非同期で行うためのヘルパー関数 ---
    @database_sync_to_async
    def is_user_in_group(self, user, group_id):
        return Group.objects.get(id=group_id).memberships.filter(member=user).exists()

    @database_sync_to_async
    def save_message(self, user, group_id, message_content):
        group = Group.objects.get(id=group_id)
        return Message.objects.create(sender=user, group=group, content=message_content)