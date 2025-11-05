import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, User, Group


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("DEBUG: WebSocket connect called")  # ← 追加1
        # 1. URLからグループIDを取得
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'group_chat_{self.group_id}'

        print(f"DEBUG: Group ID is {self.group_id}")  # ← 追加2

        # 2. Djangoの認証済みユーザーを取得
        self.user = self.scope['user']

        print(f"DEBUG: User is {self.user}, Is authenticated: {self.user.is_authenticated}")  # ← 追加3

        if not self.user.is_authenticated:
            print("DEBUG: Connection rejected (Not authenticated)")  # ← 追加4
            # 未認証ユーザーは接続を拒否
            await self.close()
            return

        # (セキュリティチェック) ユーザーがこのグループに所属しているか確認
        if not await self.is_user_in_group(self.user, self.group_id):
            print("DEBUG: Connection rejected (User not in group)")  # ← 追加5
            await self.close()
            return

        # 3. Channelsのグループに参加
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print("DEBUG: Connection accepted!")  # ← 追加6

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # WebSocketからメッセージを受信したときの処理
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']

        # 4. メッセージをデータベースに保存 (非同期DBアクセス)
        new_message = await self.save_message(self.user, self.group_id, message_content)

        # 5. グループ内の全員にメッセージを送信
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',  # ← 実行されるメソッド名を指定
                'message': new_message.content,
                'sender': new_message.sender.full_name or new_message.sender.login_id
            }
        )

    # グループからメッセージを受信したときの処理 (typeで指定したメソッド)
    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']

        # 6. WebSocketにJSONデータを送信
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
        }))

    # --- データベース操作を非同期で行うためのヘルパー関数 ---
    @database_sync_to_async
    def is_user_in_group(self, user, group_id):
        try:
            group = Group.objects.get(id=group_id)
            return group.memberships.filter(member=user).exists()
        except Group.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user, group_id, message_content):
        group = Group.objects.get(id=group_id)
        # Messageモデルのauthorフィールドに合わせて修正
        return Message.objects.create(sender=user, group=group, content=message_content)

class DMChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # ログインユーザーのIDを取得
        my_id = self.scope['user'].id
        # URLから相手のユーザーIDを取得
        other_user_id = self.scope['url_route']['kwargs']['user_id']

        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        # 2人のIDを昇順にソートして、常に同じルーム名を生成する
        if int(my_id) > int(other_user_id):
            self.room_group_name = f'dm_{other_user_id}_{my_id}'
        else:
            self.room_group_name = f'dm_{my_id}_{other_user_id}'

        # Channelsのグループ（＝DMルーム）に参加
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # メッセージ受信時の処理
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        other_user_id = self.scope['url_route']['kwargs']['user_id']

        # メッセージをDBに保存
        new_message = await self.save_dm_message(self.scope['user'], other_user_id, message_content)

        # ルーム内の全員（＝2人）にメッセージを送信
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': new_message.content,
                'sender': new_message.sender.full_name or new_message.sender.login_id
            }
        )

    # グループからメッセージ受信時の処理
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
        }))

    # DB操作用のヘルパー関数
    @database_sync_to_async
    def save_dm_message(self, sender, recipient_id, message_content):
        recipient = User.objects.get(id=recipient_id)
        return Message.objects.create(
            sender=sender,
            recipient=recipient,
            content=message_content
        )