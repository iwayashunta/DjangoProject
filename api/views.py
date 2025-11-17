# api/views.py
import json

from asgiref.sync import async_to_sync
from channels.layers import channel_layers
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404  # get_object_or_404 を追記
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from Sotsuken_Portable.models import RPiData, User, Shelter, DistributionItem, \
    DistributionRecord, FieldReportLog, Message, GroupMember, OnlineUser  # User, Shelter をインポート


@csrf_exempt
@require_POST
def shelter_checkin_api(request):
    """
    避難所のチェックインデータを受け付けるAPIビュー
    """
    try:
        # 1. ラズベリーパイから送信されたJSONデータを読み込む
        data = json.loads(request.body)

        # 2. JSONデータから必要な値を取得する
        login_id = data.get('login_id')  # QRコードから読み取った login_id
        shelter_id = data.get('shelter_management_id')  # ラズパイ側で設定された避難所のID
        device_id = data.get('device_id')  # ラズパイ自体のID

        # 3. 必須データが揃っているかチェック
        if not all([login_id, shelter_id, device_id]):
            return HttpResponseBadRequest("必要なデータが不足しています。(login_id, shelter_id, device_id)")

        # 4. 受け取った `login_id` を使って、データベースから該当するユーザーオブジェクトを取得
        #    - もし存在しない `login_id` なら、ここで 404 Not Found エラー相当の処理が走る
        user = get_object_or_404(User, login_id=login_id)

        # 5. RPiDataモデルに保存する
        #    - `payload` には、元のJSONデータをそのまま保存する
        rpi_data_record = RPiData.objects.create(
            data_type='shelter_checkin',
            device_id=device_id,
            payload=data  # 受け取った元のJSONをそのまま記録
        )

        # 6. (任意) 同時に避難所の現在の収容人数を1人増やす
        #    - こちらは shelter_id (プライマリーキー) で検索する
        shelter = get_object_or_404(Shelter, pk=shelter_id)
        shelter.current_occupancy += 1
        shelter.save()

        # 7. 成功したことをJSONで返す
        return JsonResponse({
            'status': 'success',
            'message': f"ユーザー「{user.login_id}」(氏名: {user.full_name or '未登録'}) のチェックインを受け付けました。",
            'record_id': rpi_data_record.id,
            'user_id': user.id  # ←【ご質問の点】ここで取得したユーザーオブジェクトのidを返すことは可能
        })

    except (json.JSONDecodeError, KeyError):
        # JSONの形式が不正な場合や、必須キーがない場合
        return JsonResponse({'status': 'error', 'message': '無効なデータ形式です。'}, status=400)
    except User.DoesNotExist:
        # login_id に一致するユーザーが見つからなかった場合
        return JsonResponse(
            {'status': 'error', 'message': f"指定されたログインID「{login_id}」のユーザーは存在しません。"}, status=404)
    except Shelter.DoesNotExist:
        # shelter_id に一致する避難所が見つからなかった場合
        return JsonResponse({'status': 'error', 'message': f"指定された避難所ID「{shelter_id}」は存在しません。"},
                            status=404)
    except Exception as e:
        # その他の予期せぬエラー
        return JsonResponse({'status': 'error', 'message': f"サーバー内部でエラーが発生しました: {str(e)}"}, status=500)


@require_GET
def shelter_list_api(request):
    """
    登録されている全ての避難所のリストをJSONで返すAPIビュー
    """
    try:
        shelters = Shelter.objects.all().order_by('name')

        shelter_list = [
            {
                "id": shelter.id,
                "name": shelter.name,
                "address": shelter.address,
                "max_capacity": shelter.max_capacity,
            }
            for shelter in shelters
        ]

        return JsonResponse(
            {'status': 'success', 'shelters': shelter_list},
            json_dumps_params={'ensure_ascii': False}
        )

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500,
                            json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_POST
def check_distribution_api(request):
    try:
        data = json.loads(request.body)
        login_id = data.get('login_id')
        item_id = data.get('item_id')
        device_id = data.get('device_id')

        # 'action' パラメータで、判定のみか、記録まで行うかを制御
        action = data.get('action', 'check')  # デフォルトは 'check'

        if not all([login_id, item_id]):
            return JsonResponse({'status': 'error', 'message': 'login_idとitem_idは必須です。'}, status=400)

        user = get_object_or_404(User, login_id=login_id)
        item = get_object_or_404(DistributionItem, pk=item_id)

        # 過去の配布記録を検索
        record = DistributionRecord.objects.filter(user=user, item=item).first()

        if record:
            # 既に記録がある場合
            return JsonResponse({
                'status': 'already_distributed',
                'can_distribute': False,
                'message': f"配布済みです (日時: {record.distributed_at.strftime('%Y-%m-%d %H:%M')})"
            })

        # 記録がない場合
        if action == 'record':
            # 記録まで行うアクションの場合、新規に記録を作成
            DistributionRecord.objects.create(
                user=user,
                item=item,
                recorded_by_device=device_id
            )
            return JsonResponse({
                'status': 'recorded',
                'can_distribute': True,  # 配布可能だったので、記録した
                'message': '新規に配布を記録しました。'
            })
        else:
            # 判定のみのアクションの場合
            return JsonResponse({
                'status': 'can_distribute',
                'can_distribute': True,
                'message': '配布可能です。'
            })

    except (User.DoesNotExist, DistributionItem.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': '指定されたユーザーまたは物資が存在しません。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def distribution_item_list_api(request):
    """
    登録されている全ての配布物資のリストをJSONで返すAPIビュー
    """
    try:
        # 全てのDistributionItemオブジェクトを取得
        items = DistributionItem.objects.all().order_by('name')

        # テンプレートに渡すのではなく、APIフレンドリーな辞書のリストに変換
        item_list = [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
            }
            for item in items
        ]

        # JSONレスポンスとして返す
        return JsonResponse({
            'status': 'success',
            'items': item_list
        },

            json_dumps_params={'ensure_ascii': False}
        )

    except Exception as e:
        # 何らかのエラーが発生した場合
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500,
                            json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_POST
@transaction.atomic  # データベース操作を安全に行うためのデコレータ
def field_report_api(request):
    """
    現場デバイスからの状況報告を受け付けるAPIビュー
    """
    try:
        data = json.loads(request.body)

        # 必須データのチェック
        required_keys = ["shelter_management_id", "current_evacuees", "medical_needs", "food_stock", "timestamp", "device_id"]
        if not all(key in data for key in required_keys):
            return JsonResponse({'status': 'error', 'message': '必須データが不足しています。'}, status=400)

        # 1. 報告をログとして保存
        shelter_instance = get_object_or_404(Shelter, management_id=data['shelter_management_id'])

        new_log = FieldReportLog.objects.create(
            shelter=shelter_instance,
            current_evacuees=data['current_evacuees'],
            medical_needs=data['medical_needs'],
            food_stock=data['food_stock'],
            original_timestamp=data['timestamp'],
            reported_by_device=data['device_id'],
        )

        # 2. (重要) 避難所マスタの情報を最新の報告内容で更新する
        #    例えば、Shelterモデルの current_occupancy を更新する
        shelter_instance.current_occupancy = data['current_evacuees']
        shelter_instance.save()

        return JsonResponse({'status': 'success', 'message': f'レポート(ID:{new_log.id})を受け付けました。'}, status=201)

    except Shelter.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '指定された避難所IDが見つかりません。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def get_user_groups_api(request):
    """
    指定されたユーザーが所属するグループのリストを返すAPIビュー
    """
    # 簡易的な認証: HTTPヘッダーから login_id を取得
    login_id = request.headers.get('X-User-Login-Id')

    if not login_id:
        return JsonResponse({'status': 'error', 'message': 'X-User-Login-Idヘッダーが必要です。'}, status=401)

    try:
        user = User.objects.get(login_id=login_id)

        # ユーザーが所属するグループを取得
        memberships = user.group_memberships.all()
        groups = [m.group for m in memberships]

        group_list = [
            {
                "id": group.id,
                "name": group.name,
            }
            for group in groups
        ]

        return JsonResponse(
            {'status': 'success', 'groups': group_list},
            json_dumps_params={'ensure_ascii': False}
        )

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '指定されたユーザーが見つかりません。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def post_group_message_api(request):
    """
    現場デバイスからグループチャットへのメッセージ投稿を受け付けるAPI
    """
    # 簡易認証
    login_id = request.headers.get('X-User-Login-Id')
    if not login_id:
        return JsonResponse({'status': 'error', 'message': 'X-User-Login-Idヘッダーが必要です。'}, status=401)

    try:
        user = User.objects.get(login_id=login_id)
        data = json.loads(request.body)
        group_id = data.get('group_id')
        message = data.get('message')

        # デバッグ用ログ出力
        print(f"[API DEBUG] Received message for group_id: {group_id}")
        print(f"[API DEBUG] Message content: {message}")
        target_group_name = f'chat_{group_id}'
        print(f"[API DEBUG] Sending to channel group: {target_group_name}")

        if not all([group_id, message]):
            return JsonResponse({'status': 'error', 'message': 'group_idとmessageは必須です。'}, status=400)

        # 1. 送信先のグループに所属しているメンバーを取得
        target_members = GroupMember.objects.filter(group_id=group_id)
        target_user_ids = [member.member_id for member in target_members]

        # 2. その中で、現在オンライン（WebSocketに接続中）のユーザーを探す
        online_users = OnlineUser.objects.filter(user_id__in=target_user_ids)

        if not online_users:
            # 誰もオンラインでなければ、何もしない（DBへの保存は別途行う）
            print(f"[API WARN] Group {group_id} has no online users.")
            # (メッセージをDBに保存する処理はここに入れる)
            return JsonResponse({'status': 'success', 'message': 'メッセージを保存しました（オンラインユーザーなし）。'})

        channel_layer = channel_layers['default']
        chat_data = {
            'type': 'chat_message',
            'message': message,
            'sender': user.full_name or user.login_id,
        }

        # 3. オンラインのユーザー一人ひとりに、直接メッセージを送信する
        for online_user in online_users:
            print(f"[API DEBUG] Sending direct message to channel: {online_user.channel_name}")
            async_to_sync(channel_layer.send)(
                online_user.channel_name,
                chat_data
            )

        # (メッセージをDBに保存する処理も忘れずに)
        try:
            # メッセージをデータベースのMessageテーブルに保存
            Message.objects.create(
                sender=user,
                group_id=group_id,
                content=message
            )
        except Exception as e:
            # DB保存に失敗しても、リアルタイム送信は試みる
            print(f"!!! DB SAVE ERROR in post_group_message_api: {e}")

        return JsonResponse({'status': 'success', 'message': 'メッセージをオンラインユーザーに送信しました。'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def get_group_messages_api(request, group_id):
    """
    指定されたグループの最新のメッセージ履歴を返すAPI
    """
    try:
        # 認証チェック（簡易版）
        login_id = request.headers.get('X-User-Login-Id')
        if not login_id:
            return JsonResponse({'status': 'error', 'message': '認証ヘッダーが必要です。'}, status=401)

        # ユーザーがそのグループのメンバーかどうかの権限チェック（重要）
        user = User.objects.get(login_id=login_id)
        if not user.group_memberships.filter(group_id=group_id).exists():
            return JsonResponse({'status': 'error', 'message': 'このグループへのアクセス権がありません。'}, status=403)

        # 最新50件のメッセージを取得
        messages = Message.objects.filter(group_id=group_id).order_by('-timestamp')[:50]

        message_list = [
            {
                "sender": msg.sender.full_name or msg.sender.login_id,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in reversed(messages)  # 古い順に戻してリスト化
        ]

        return JsonResponse(
            {'status': 'success', 'messages': message_list},
            json_dumps_params={'ensure_ascii': False}
        )
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
@transaction.atomic  # 複数のDB操作を安全に行う
def shelter_checkin_sync_api(request):
    """
    (データ同期用) ラズパイから未同期のチェックイン・チェックアウト記録を受け付けるAPI
    """
    try:
        data = json.loads(request.body)

        # 1. 必須データのチェック
        required_keys = ["login_id", "shelter_management_id", "checkin_type", "timestamp", "device_id"]
        if not all(key in data for key in required_keys):
            return JsonResponse({'status': 'error', 'message': '必須データが不足しています。'}, status=400)

        # 2. 関連データの存在チェック
        user = get_object_or_404(User, login_id=data['login_id'])
        shelter = get_object_or_404(Shelter, management_id=data['shelter_management_id'])

        # checkin_type の値が正しいかチェック
        if data['checkin_type'] not in ['checkin', 'checkout']:
            return JsonResponse({'status': 'error', 'message': '無効なcheckin_typeです。'}, status=400)

        # 3. ログとしてまず保存する (field_report_api と同じ思想)
        #    これにより、何が送られてきたかの記録が確実に残る
        log_record = RPiData.objects.create(
            data_type=f"sync_{data['checkin_type']}",  # 'sync_checkin' or 'sync_checkout'
            device_id=data['device_id'],
            payload=data,
            original_timestamp=data['timestamp']  # 元のタイムスタンプを記録
        )

        # 4. 避難所の現在の収容人数を更新
        if data['checkin_type'] == 'checkin':
            shelter.current_occupancy += 1
        else:  # 'checkout' の場合
            # 0未満にならないように制御
            if shelter.current_occupancy > 0:
                shelter.current_occupancy -= 1
        shelter.save()

        # 5. (重要) ユーザーの安否ステータスや最終確認場所を更新する
        #    これがユーザーの安否確認の中核機能となる
        user.safety_status = 'safe'  # 例: チェックインなら「無事」に
        user.last_known_location = shelter.name  # 最後の確認場所を更新
        user.last_seen_at = data['timestamp']  # 最後の確認日時を更新
        user.save()

        return JsonResponse({
            'status': 'success',
            'message': f"ID:{user.login_id} の {data['checkin_type']} 記録(ID:{log_record.id})を受け付けました。"
        }, status=201)

    except (User.DoesNotExist, Shelter.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': '指定されたユーザーIDまたは避難所IDが見つかりません。'},
                            status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
