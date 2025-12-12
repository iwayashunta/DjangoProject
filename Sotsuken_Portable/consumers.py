import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message, User, Group, OnlineUser, GroupMember

class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        if self.group_id == 'all':
            self.group_name = 'chat_broadcast'
        else:
            self.group_name = f'chat_{self.group_id}'
            if self.user.is_authenticated:
                if not await self.is_user_in_group(self.user, self.group_id):
                    await self.close()
                    return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        if self.user.is_authenticated:
            await self.save_online_status(is_online=True)
            print(f"[CONNECT] {self.user.username} -> {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if self.user.is_authenticated:
            await self.save_online_status(is_online=False)
        print(f"[DISCONNECT] {self.user.username}")

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data: return
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        msg = await self.save_message(self.user, self.group_id, message_content)
        chat_data = {
            'type': 'chat_message',
            'id': msg.id,
            'message': message_content,
            'sender': self.user.username,
            'sender_full_name': self.user.full_name or self.user.username,
            'image_url': None,
            'group_id': self.group_id
        }
        await self.channel_layer.group_send(self.group_name, chat_data)

    async def chat_message(self, event):
        print(f"DEBUG: Consumers received event: {event}")
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message'),
            'sender': event.get('sender'),
            'sender_full_name': event.get('sender_full_name'),
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
        }))

    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({'type': 'delete', 'message_id': event['message_id']}))

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
        # UUIDオブジェクトかもしれないので str() で確実に文字列化
        my_id = str(self.scope['user'].id)
        # URLから取得したID (これは元々文字列)
        other_user_id = self.scope['url_route']['kwargs']['user_id']

        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        # ★修正: int() をやめて、文字列のリストとしてソートする
        # これにより "4b33..." と "a123..." のようなUUID同士でも正しく順序が決まります
        user_ids = sorted([my_id, other_user_id])

        # ソートされた順序で結合
        self.room_group_name = f'dm_{user_ids[0]}_{user_ids[1]}'

        # Channelsのグループに参加
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        other_user_id = self.scope['url_route']['kwargs']['user_id']
        new_message = await self.save_dm_message(self.scope['user'], other_user_id, message_content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': new_message.id,
                'message': new_message.content,
                'sender': self.scope['user'].username,
                'sender_full_name': self.scope['user'].full_name or self.scope['user'].username,
            }
        )

    async def chat_message(self, event):
        print(f"DEBUG: Consumers received event: {event}")
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event.get('id'),
            'message': event.get('message'),
            'sender': event.get('sender'),
            'sender_full_name': event.get('sender_full_name'),
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
        }))

    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({'type': 'delete', 'message_id': event['message_id'],'sender': event.get('sender'),}))

    @database_sync_to_async
    def save_dm_message(self, sender, recipient_id, message_content):
        return Message.objects.create(sender=sender, recipient_id=recipient_id, content=message_content)

# --- ここからLocationConsumerを追加 ---
class LocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print(f"Location WebSocket connected for user {self.user.username}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"Location WebSocket disconnected for user {self.user.username}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            lat, lng = data.get('lat'), data.get('lng')
            if lat is not None and lng is not None:
                await self.update_user_location(lat, lng)
                print(f"Received location from {self.user.username}: Lat={lat}, Lng={lng}")
        except (json.JSONDecodeError, Exception) as e:
            print(f"An error occurred in LocationConsumer: {e}")

    @database_sync_to_async
    def update_user_location(self, lat, lng):
        self.user.last_known_latitude = lat
        self.user.last_known_longitude = lng
        self.user.save(update_fields=['last_known_latitude', 'last_known_longitude'])
