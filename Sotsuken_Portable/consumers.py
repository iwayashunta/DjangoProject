import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message, User, Group, OnlineUser, GroupMember

class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']

        # --- グループ名の決定 ---
        if self.group_id == 'all':
            self.group_name = 'chat_broadcast'
        else:
            self.group_name = f'chat_{self.group_id}'
            # 権限チェック
            if self.user.is_authenticated:
                if not await self.is_user_in_group(self.user, self.group_id):
                    await self.close()
                    return
            else:
                # ラズパイ等の未認証アクセス（ポリシーにより許可）
                pass

        # グループに参加
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        if self.user.is_authenticated:
            await self.save_online_status(is_online=True)
            print(f"[CONNECT] {self.user.username} -> {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
        if self.user.is_authenticated:
            await self.save_online_status(is_online=False)
        print(f"[DISCONNECT] {self.user.username}")

    # ------------------------------------------------------------------
    # 【注】現在はAPI(POST)経由で送信しているため、この receive は
    # クライアントから直接 socket.send() した場合のみ動きます。
    # 整合性を保つため、ここでも sender と sender_full_name を分けます。
    # ------------------------------------------------------------------
    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data: return
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']

        # DB保存
        msg = await self.save_message(self.user, self.group_id, message_content)

        # 配信データ構築
        chat_data = {
            'type': 'chat_message',
            'id': msg.id,
            'message': message_content,
            'sender': self.user.username,  # ★重要: ID判定用 (user01)
            'sender_full_name': self.user.full_name or self.user.username, # ★追加: 表示用 (管理者ちゃん)
            'image_url': None, # WS経由だと画像は送れないのでNone
            'group_id': self.group_id
        }

        # グループ配信
        if self.group_id == 'all':
            await self.channel_layer.group_send(self.group_name, chat_data)
        else:
            # オンラインユーザーのみに送信するロジック（必要であれば）
            # 基本的には group_send で良いですが、元のロジックを尊重する場合:
            await self.channel_layer.group_send(self.group_name, chat_data)

    # ------------------------------------------------------------------
    # ★重要: View (API) から group_send されたイベントを受け取るメソッド
    # ------------------------------------------------------------------
    async def chat_message(self, event):
        # WebSocketを通じてクライアント(JS)にJSONを送信
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message'),
            'sender': event.get('sender'),                 # ★ username (判定用)
            'sender_full_name': event.get('sender_full_name'), # ★ 表示名
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
        }))

    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': event['message_id']
        }))

    # --- DB Helper Methods ---
    @database_sync_to_async
    def is_user_in_group(self, user, group_id):
        if not user.is_authenticated: return False
        try:
            return Group.objects.get(id=group_id).memberships.filter(member=user).exists()
        except:
            return False

    @database_sync_to_async
    def save_online_status(self, is_online):
        if self.scope["user"].is_authenticated:
            if is_online:
                OnlineUser.objects.update_or_create(user=self.scope["user"], defaults={'channel_name': self.channel_name})
            else:
                OnlineUser.objects.filter(user=self.scope["user"]).delete()

    @database_sync_to_async
    def save_message(self, user, group_id, content):
        if group_id == 'all':
            return Message.objects.create(sender=user, group=None, content=content)
        else:
            return Message.objects.create(sender=user, group_id=group_id, content=content)


class DMChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        my_id = self.scope['user'].id
        other_user_id = self.scope['url_route']['kwargs']['user_id']

        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        if int(my_id) > int(other_user_id):
            self.room_group_name = f'dm_{other_user_id}_{my_id}'
        else:
            self.room_group_name = f'dm_{my_id}_{other_user_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        other_user_id = self.scope['url_route']['kwargs']['user_id']

        new_message = await self.save_dm_message(self.scope['user'], other_user_id, message_content)

        # DMの場合も同様に sender と sender_full_name を分ける
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': new_message.id,
                'message': new_message.content,
                'sender': self.scope['user'].username, # ★ username
                'sender_full_name': self.scope['user'].full_name or self.scope['user'].username, # ★ 表示名
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message'),
            'sender': event.get('sender'),                 # ★ username
            'sender_full_name': event.get('sender_full_name'), # ★ 表示名
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
        }))

    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': event['message_id']
        }))

    @database_sync_to_async
    def save_dm_message(self, sender, recipient_id, message_content):
        return Message.objects.create(sender=sender, recipient_id=recipient_id, content=message_content)