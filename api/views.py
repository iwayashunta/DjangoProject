# api/views.py
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404  # get_object_or_404 を追記
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from Sotsuken_Portable.models import RPiData, User, Shelter  # User, Shelter をインポート


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
        shelter_id = data.get('shelter_id')  # ラズパイ側で設定された避難所のID
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