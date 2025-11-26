import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Message, User, Group, OnlineUser, GroupMember


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        # if not self.user.is_authenticated:
        #    await self.close()
        #    return

        # URLからグループIDを取得
        self.group_id = self.scope['url_route']['kwargs']['group_id']

        # ---------------------------------------------------------
        # 分岐: 全体連絡 ('all') か、通常のグループチャットか
        # ---------------------------------------------------------
        if self.group_id == 'all':
            # --- A. 全体連絡の場合 ---
            self.group_name = 'chat_broadcast'
            # 全体連絡は権限チェック不要（ログインしていれば参加OK）

        else:
            # --- B. 通常のグループチャットの場合 ---
            self.group_name = f'chat_{self.group_id}'

            if self.user.is_authenticated:
                # ログインユーザーなら、ちゃんとグループに入っているかチェック
                if not await self.is_user_in_group(self.user, self.group_id):
                    await self.close()
                    return
            else:
                # 匿名ユーザー（ラズパイ）の場合
                # ここで await self.close() すれば「閲覧禁止」
                # 何もしなければ「閲覧許可（接続OK）」となります。
                # 今回はラズパイでの閲覧を許可するため、何もしない（スルー）でOKです。
                pass


        # グループに参加
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # オンライン状態を保存
        await self.save_online_status(is_online=True)
        print(f"[CONSUMER CONNECT] User '{self.user.username}' connected to group '{self.group_name}'")

    async def disconnect(self, close_code):
        # ★修正: 変数名を self.group_name に統一
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

        if self.user.is_authenticated:
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

        # 2. メッセージを配信
        chat_data = {
            'type': 'chat_message',
            'message': message_content,
            'sender': sender_name,
        }

        if self.group_id == 'all':
            # --- A. 全体連絡の場合: グループ全員に一斉送信 ---
            await self.channel_layer.group_send(
                self.group_name,  # 'chat_broadcast'
                chat_data
            )
        else:
            # --- B. 通常グループの場合: オンラインユーザーに個別送信 ---
            # (元のロジックを維持)
            online_channels = await self.get_online_channels_in_group(self.group_id)
            if not online_channels:
                print(f"[CONSUMER WARN] Group {self.group_id} has no online users.")
                return

            for channel_name in online_channels:
                await self.channel_layer.send(channel_name, chat_data)

    # グループからメッセージを受信したときの処理
    async def chat_message(self, event):
        # WebSocketにJSONデータを送信
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
        }))

    # --- データベース操作ヘルパー ---

    @database_sync_to_async
    def get_online_channels_in_group(self, group_id):
        target_members = GroupMember.objects.filter(group_id=group_id)
        target_user_ids = [member.member_id for member in target_members]
        online_users = OnlineUser.objects.filter(user_id__in=target_user_ids)
        return [user.channel_name for user in online_users]

    @database_sync_to_async
    def is_user_in_group(self, user, group_id):
        # ★追加: 匿名ユーザー（ラズパイ）の場合は、メンバー検索を行わずに False を返す
        # (ただし、ラズパイからの接続を許可したい場合は、ここで True を返してスルーさせる手もあります)
        if not user.is_authenticated:
            return False  # または True (ポリシー次第)

        try:
            group = Group.objects.get(id=group_id)
            return group.memberships.filter(member=user).exists()
        except (Group.DoesNotExist, ValueError):
            return False

    @database_sync_to_async
    def save_online_status(self, is_online):
        user = self.scope["user"]

        # ★追加: 認証済みユーザーの場合のみ保存処理を行う
        if user.is_authenticated:
            if is_online:
                OnlineUser.objects.update_or_create(
                    user=user,
                    defaults={'channel_name': self.channel_name}
                )
            else:
                OnlineUser.objects.filter(user=user).delete()

    @database_sync_to_async
    def save_message(self, user, group_id, message_content):
        # ★修正: group_id='all' の場合の保存処理を追加
        if group_id == 'all':
            return Message.objects.create(
                sender=user,
                group=None,
                content=message_content
            )
        else:
            group = Group.objects.get(id=group_id)
            return Message.objects.create(
                sender=user,
                group=group,
                content=message_content
            )


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
            'image_url': event.get('image_url'),
            'group_id': event.get('group_id'),
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
