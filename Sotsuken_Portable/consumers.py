import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Message, User, Group, OnlineUser, GroupMember


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()  # 未認証なら即切断
            return

        # 2. URLからグループIDを取得し、グループ名を設定
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.group_name = f'chat_{self.group_id}'  # room_group_name ではなく group_name に統一

        # 3. ユーザーがこのグループのメンバーかチェック (DBアクセス)
        if not await self.is_user_in_group(self.user, self.group_id):
            await self.close()  # メンバーでなければ切断
            return

        # 4. 全てのチェックをパスしたら、グループに参加
        await self.channel_layer.group_add(
            group=self.group_name,
            channel=self.channel_name
        )

        # 5. WebSocket接続を受け入れる
        await self.accept()

        # 6. DBにオンライン状態を保存 (接続が確定してから)
        await self.save_online_status(is_online=True)

        print(f"[CONSUMER CONNECT] User '{self.user.username}' connected to group '{self.group_name}'")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):  # group_nameが存在するか確認
            await self.channel_layer.group_discard(
                group=self.room_group_name,
                channel=self.channel_name,
            )
        if self.user.is_authenticated:  # 念のため
            await self.save_online_status(is_online=False)
        print(f"[CONSUMER DISCONNECT] User '{self.user.username}' disconnected.")

    # WebSocketからメッセージを受信したときの処理
    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            return

        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']

        # 1. メッセージをDBに保存
        await self.save_message(self.user, self.group_id, message_content)

        sender_name = self.user.full_name or self.user.username

        # --- ここからが新しいロジック ---

        # 2. 送信先のグループに所属している、現在オンラインのユーザーを探す
        online_channels = await self.get_online_channels_in_group(self.group_id)

        if not online_channels:
            print(f"[CONSUMER WARN] Group {self.group_id} has no online users to send message to.")
            return

        # 3. 送信するメッセージデータを作成
        chat_data = {
            'type': 'chat_message',  # chat_messageメソッドを呼び出す
            'message': message_content,
            'sender': sender_name,
        }

        # 4. オンラインのユーザー一人ひとりに、直接メッセージを送信
        for channel_name in online_channels:
            await self.channel_layer.send(channel_name, chat_data)

        '''
        # 5. グループ内の全員にメッセージを送信
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',  # ← 実行されるメソッド名を指定
                'message': new_message.content,
                'sender': new_message.sender.full_name or new_message.sender.username
            }
        )
        '''

    @database_sync_to_async
    def get_online_channels_in_group(self, group_id):
        """指定されたグループに所属し、かつオンラインのユーザーのchannel_nameリストを返す"""
        target_members = GroupMember.objects.filter(group_id=group_id)
        target_user_ids = [member.member_id for member in target_members]

        online_users = OnlineUser.objects.filter(user_id__in=target_user_ids)
        return [user.channel_name for user in online_users]

    # グループからメッセージを受信したときの処理 (typeで指定したメソッド)
    async def chat_message(self, event):
        print(f"[CONSUMER DEBUG] Received message in group {self.group_name}: {event}")
        message = event['message']
        sender = event['sender']

        print(f"[CONSUMER DEBUG] Received message in group {self.group_name}: {event}")

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
    def save_online_status(self, is_online):
        if is_online:
            OnlineUser.objects.update_or_create(
                user=self.scope["user"],
                defaults={'channel_name': self.channel_name}
            )
        else:
            OnlineUser.objects.filter(user=self.scope["user"]).delete()

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
                'sender': new_message.sender.full_name or new_message.sender.username
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
