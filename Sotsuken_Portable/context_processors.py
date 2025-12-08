import datetime

import django

from .models import Message, ReadState, GroupMember, Connection
from django.db.models import Q
from django.utils import timezone


def unread_notification(request):
    if not request.user.is_authenticated:
        return {}

    has_unread = False

    # 1. 参加グループの未読チェック
    my_groups = [m.group for m in request.user.group_memberships.all()]
    for group in my_groups:
        read_state = ReadState.objects.filter(user=request.user, group=group).first()
        # last_read = read_state.last_read_at if read_state else timezone.datetime.min.replace(tzinfo=timezone.utc)

        if read_state:
            last_read = read_state.last_read_at
        else:
            # "ずっと昔" の日時を作る
            last_read = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        if Message.objects.filter(group=group, timestamp__gt=last_read).exclude(sender=request.user).exists():
            has_unread = True
            break

    # 2. DMの未読チェック (グループで未読が見つかればスキップ可)
    if not has_unread:
        # 友達関係(accepted)にあるユーザーを取得
        connections = Connection.objects.filter(
            (django.db.models.Q(requester=request.user) | django.db.models.Q(receiver=request.user)),
            status='accepted'
        )
        # フレンドIDリスト作成などは省略... (既存の実装に合わせてください)
        # DMの場合も同様に .exclude(sender=request.user) が必要ですが、
        # DMの場合は「相手からのメッセージ」だけを見ればいいので、
        # sender=dm_partner で絞り込んでいればOKです。
        pass

    return {'global_has_unread': has_unread}