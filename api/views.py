# api/views.py
import json

from asgiref.sync import async_to_sync
from channels.layers import channel_layers
from dateutil import parser
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
        username = data.get('username')  # QRコードから読み取った username
        shelter_management_id = data.get('shelter_management_id')   # ラズパイ側で設定された避難所のID
        device_id = data.get('device_id')  # ラズパイ自体のID

        # 3. 必須データが揃っているかチェック
        if not all([username, shelter_management_id, device_id]):
            return HttpResponseBadRequest("必要なデータが不足しています。(username, shelter_id, device_id)")

        # 4. 受け取った `username` を使って、データベースから該当するユーザーオブジェクトを取得
        #    - もし存在しない `username` なら、ここで 404 Not Found エラー相当の処理が走る
        user = get_object_or_404(User, username=username)

        # 5. RPiDataモデルに保存する
        #    - `payload` には、元のJSONデータをそのまま保存する
        rpi_data_record = RPiData.objects.create(
            data_type='shelter_checkin',
            device_id=device_id,
            payload=data  # 受け取った元のJSONをそのまま記録
        )

        # 6. (任意) 同時に避難所の現在の収容人数を1人増やす
        #    - こちらは shelter_id (プライマリーキー) で検索する
        shelter = get_object_or_404(Shelter, management_id=shelter_management_id)
        shelter.current_occupancy += 1
        shelter.save()

        # 7. 成功したことをJSONで返す
        return JsonResponse({
            'status': 'success',
            'message': f"ユーザー「{user.username}」(氏名: {user.full_name or '未登録'}) のチェックインを受け付けました。",
            'record_id': rpi_data_record.id,
            'user_id': user.id  # ←【ご質問の点】ここで取得したユーザーオブジェクトのidを返すことは可能
        })

    except (json.JSONDecodeError, KeyError):
        # JSONの形式が不正な場合や、必須キーがない場合
        return JsonResponse({'status': 'error', 'message': '無効なデータ形式です。'}, status=400)
    except User.DoesNotExist:
        # username に一致するユーザーが見つからなかった場合
        return JsonResponse(
            {'status': 'error', 'message': f"指定されたログインID「{username}」のユーザーは存在しません。"}, status=404)
    except Shelter.DoesNotExist:
        # shelter_id に一致する避難所が見つからなかった場合
        return JsonResponse({'status': 'error', 'message': f"指定された避難所ID「{shelter_management_id}」は存在しません。"},
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
        username = data.get('username')
        item_id = data.get('item_id')
        device_id = data.get('device_id')

        # 'action' パラメータで、判定のみか、記録まで行うかを制御
        action = data.get('action', 'check')  # デフォルトは 'check'

        if not all([username, item_id]):
            return JsonResponse({'status': 'error', 'message': 'usernameとitem_idは必須です。'}, status=400)

        user = get_object_or_404(User, username=username)
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
    # 簡易的な認証: HTTPヘッダーから username を取得
    username = request.headers.get('X-User-Login-Id')

    if not username:
        return JsonResponse({'status': 'error', 'message': 'X-User-Login-Idヘッダーが必要です。'}, status=401)

    try:
        user = User.objects.get(username=username)

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
    メッセージ投稿API (ラズパイからのヘッダー認証 & ブラウザからのセッション認証 両対応)
    """
    user = None

    # 1. ヘッダー認証（ラズパイ用）を試みる
    header_username = request.headers.get('X-User-Login-Id')
    if header_username:
        try:
            user = User.objects.get(username=header_username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '指定されたユーザーが存在しません。'}, status=400)

    # 2. セッション認証（メインサーバーブラウザ用）を試みる
    elif request.user.is_authenticated:
        user = request.user

    # どちらもダメならエラー
    else:
        return JsonResponse({'status': 'error', 'message': '認証が必要です。'}, status=401)

    # ここからメイン処理
    try:
        # JSONではなくPOST/FILESからデータを取得
        group_id = request.POST.get('group_id')
        message = request.POST.get('message', '')
        image_file = request.FILES.get('image')

        print(f"[API DEBUG] group_id: {group_id}, message: {message}, image: {image_file}")

        # メッセージも画像もない場合はエラー
        if not message and not image_file:
            return JsonResponse({'status': 'error', 'message': 'メッセージまたは画像が必要です。'}, status=400)

        channel_layer = channel_layers['default']

        # DB保存と配信データの準備
        new_msg = None

        if str(group_id) == 'all':
            # --- A. 全体連絡 ---
            new_msg = Message.objects.create(
                sender=user,
                group=None,
                content=message,
                image=image_file
            )
            target_group_name = "chat_broadcast"

            # WebSocket配信用データ
            chat_data = {
                'type': 'chat_message',
                'message': new_msg.content,
                'sender': user.full_name or user.username,
                'group_id': 'all',
                'image_url': new_msg.image.url if new_msg.image else None,
            }

            # 一斉送信
            async_to_sync(channel_layer.group_send)(
                target_group_name,
                chat_data
            )

        else:
            # --- B. 通常グループ ---
            try:
                group_id_int = int(group_id)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': '無効なグループIDです'}, status=400)

            new_msg = Message.objects.create(
                sender=user,
                group_id=group_id_int,
                content=message,
                image=image_file
            )

            # WebSocket配信用データ
            chat_data = {
                'type': 'chat_message',
                'message': new_msg.content,
                'sender': user.full_name or user.username,
                'group_id': str(group_id_int),
                'image_url': new_msg.image.url if new_msg.image else None,
            }

            # オンラインユーザーへの個別送信（またはグループ送信）
            target_members = GroupMember.objects.filter(group_id=group_id_int)
            target_user_ids = [m.member_id for m in target_members]
            online_users = OnlineUser.objects.filter(user_id__in=target_user_ids)

            for online_user in online_users:
                async_to_sync(channel_layer.send)(
                    online_user.channel_name,
                    chat_data
                )

        return JsonResponse({'status': 'success', 'message': '送信成功'})

    except Exception as e:
        print(f"[API ERROR] {e}")  # エラーログを出す
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def get_group_messages_api(request, group_id):
    """
    指定されたグループの最新のメッセージ履歴を返すAPI
    （全体連絡 'all' 対応版）
    """
    try:
        # 認証チェック（簡易版）
        username = request.headers.get('X-User-Login-Id')
        if not username:
            return JsonResponse({'status': 'error', 'message': '認証ヘッダーが必要です。'}, status=401)

        user = User.objects.get(username=username)

        messages_query = None

        # ---------------------------------------------------------
        # 分岐: 全体連絡 ('all') か、特定のグループチャットか
        # ---------------------------------------------------------
        if group_id == 'all':
            # --- A. 全体連絡の場合 ---
            # 権限チェック不要（ログインしていれば誰でも見れる前提）

            # groupもrecipientもNULLのメッセージを取得
            messages_query = Message.objects.filter(
                group__isnull=True,
                recipient__isnull=True
            ).order_by('-timestamp')[:50]

        else:
            # --- B. 通常のグループチャットの場合 ---
            # ユーザーがそのグループのメンバーかどうかの権限チェック（重要）
            if not user.group_memberships.filter(group_id=group_id).exists():
                return JsonResponse({'status': 'error', 'message': 'このグループへのアクセス権がありません。'},
                                    status=403)

            # 指定されたグループIDのメッセージを取得
            messages_query = Message.objects.filter(group_id=group_id).order_by('-timestamp')[:50]

        # ---------------------------------------------------------
        # メッセージリストの作成（共通処理）
        # ---------------------------------------------------------
        message_list = [
            {
                "sender": msg.sender.full_name or msg.sender.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "image_url": msg.image.url if msg.image else None,
            }
            # messages_query は新しい順(order_by('-timestamp'))で取得しているので、
            # reversed() で古い順（時系列順）に戻してリスト化する
            for msg in reversed(messages_query)
        ]

        return JsonResponse(
            {'status': 'success', 'messages': message_list},
            json_dumps_params={'ensure_ascii': False}
        )

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'ユーザーが見つかりません。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def post_dm_message_api(request):
    """
    DMメッセージ投稿API (画像対応版)
    """
    # 認証チェック (セッション or ヘッダー)
    sender = None
    header_username = request.headers.get('X-User-Login-Id')
    if header_username:
        try:
            sender = User.objects.get(username=header_username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '送信ユーザーが見つかりません'}, status=400)
    elif request.user.is_authenticated:
        sender = request.user
    else:
        return JsonResponse({'status': 'error', 'message': '認証が必要です'}, status=401)

    try:
        recipient_id = request.POST.get('recipient_id')
        message = request.POST.get('message', '')
        image_file = request.FILES.get('image')

        if not recipient_id or (not message and not image_file):
            return JsonResponse({'status': 'error', 'message': '宛先と、メッセージまたは画像が必要です'}, status=400)

        recipient = User.objects.get(id=recipient_id)

        # 1. DB保存
        new_msg = Message.objects.create(
            sender=sender,
            recipient=recipient,
            group=None, # DMなのでNone
            content=message,
            image=image_file
        )

        # 2. WebSocket配信
        # ルーム名を生成 (IDの小さい順_大きい順)
        user_ids = sorted([sender.id, recipient.id])
        room_group_name = f'dm_{user_ids[0]}_{user_ids[1]}'

        channel_layer = channel_layers['default']
        chat_data = {
            'type': 'chat_message',
            'message': new_msg.content,
            'sender': sender.full_name or sender.username,
            'image_url': new_msg.image.url if new_msg.image else None, # 画像URL
        }

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            chat_data
        )

        return JsonResponse({'status': 'success', 'message': '送信成功'})

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '宛先ユーザーが見つかりません'}, status=404)
    except Exception as e:
        print(f"[DM API ERROR] {e}")
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
        required_keys = ["username", "shelter_management_id", "checkin_type", "timestamp", "device_id"]
        if not all(key in data for key in required_keys):
            return JsonResponse({'status': 'error', 'message': '必須データが不足しています。'}, status=400)

        # 2. 関連データの存在チェック
        user = get_object_or_404(User, username=data['username'])
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
        if data['checkin_type'] == 'checkin':
            user.last_known_location = shelter.name # 最後の確認場所を更新
        else:
            # 退所の場合は「(退所)」を付けるなど
            user.last_known_location = f"{shelter.name} (退所)"
        user.last_seen_at = parser.parse(data['timestamp'])  # 最後の確認日時を更新
        user.save()


        print(f"[API INFO] User {user.username} updated: Location={user.last_known_location}, Time={user.last_seen_at}")

        return JsonResponse({
            'status': 'success',
            'message': f"ID:{user.username} の {data['checkin_type']} 記録(ID:{log_record.id})を受け付けました。"
        }, status=201)

    except (User.DoesNotExist, Shelter.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': '指定されたユーザーIDまたは避難所IDが見つかりません。'},
                            status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def register_field_user_api(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password') # ★キー名を'password'に変更することを推奨
        full_name = data.get('full_name')


        missing_fields = []
        if not username: missing_fields.append('username')
        if not password: missing_fields.append('password')
        if not full_name: missing_fields.append('full_name')

        if missing_fields:
            return JsonResponse({
                'status': 'error',
                'message': f'必須項目が不足しています: {", ".join(missing_fields)}'
            }, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': f'ログインID「{username}」は既に使用されています。'}, status=409)

        # ★★★★★ ここを修正 ★★★★★
        # User.objects.create() の代わりに User.objects.create_user() を使う
        new_user = User.objects.create_user(
            username=username,
            password=password, # 生のパスワードを渡すと、内部で自動的にハッシュ化される
            full_name=full_name
        )
        # ★★★★★ ここまで ★★★★★

        return JsonResponse({'status': 'success', 'message': 'ユーザーの本登録が完了しました。'}, status=201)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def get_all_users_api(request):
    """
    ラズパイ向けに全ユーザーの認証情報（ハッシュ済みパスワード含む）を返すAPI
    ※ セキュリティ注意: 本番環境では必ずHTTPSで通信し、IP制限やトークン認証を行うこと
    """
    # ラズパイからのアクセスであることを確認する簡易認証（ヘッダーなど）を入れるとより安全です

    users = User.objects.all()
    data = []
    for user in users:
        data.append({
            'username': user.username,
            'password': user.password,  # ハッシュ化されたパスワード文字列
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role,
        })

    return JsonResponse({'status': 'success', 'users': data})




