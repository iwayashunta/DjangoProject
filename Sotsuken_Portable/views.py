import csv
import datetime
import json
import math

from asgiref.sync import async_to_sync
from channels.layers import channel_layers
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # ログイン必須にするためのデコレータ
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils import timezone
from django.views import generic
from django.views.decorators.http import require_POST
# generic から、使いたいクラスを直接インポートする
from django.views.generic import ListView, DetailView, CreateView, TemplateView

from Sotsuken_Portable.forms import SignUpForm, SafetyStatusForm, SupportRequestForm, CommunityPostForm, CommentForm, \
    GroupCreateForm, UserUpdateForm, MyPasswordChangeForm, ShelterForm, UserSearchForm, DistributionInfoForm
from Sotsuken_Portable.models import SafetyStatus, SupportRequest, SOSReport, Shelter, OfficialAlert, Group, Message, \
    CommunityPost, Comment, GroupMember, User, Manual, RPiData, DistributionRecord, JmaArea, Connection, \
    DistributionInfo, DistributionItem, ReadState, SafetyStatusHistory
from Sotsuken_Portable.decorators import admin_required


# Create your views here.

@login_required()
def index(request):
    return render(request, 'index.html')


def signup_view(request):
    """
    ユーザー登録の入力処理を行うビュー
    """
    # POSTリクエスト（フォームが送信された）の場合
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        # バリデーション (入力内容が正しいかチェック)
        if form.is_valid():
            # OKなら、入力内容をセッションに保存して確認画面へリダイレクト
            # cleaned_dataを使うと、フォームが処理した後の安全なデータを取り出せる
            request.session['signup_data'] = form.cleaned_data
            return redirect('Sotsuken_Portable:signup_confirm')

        # NGなら、エラーメッセージを含んだフォームを再度表示
        return render(request, 'signup.html', {'form': form})

    # GETリクエスト（初めてページを開いた）の場合
    else:
        # セッションに修正データがあればそれを使う（確認画面から「戻る」で来た場合）
        signup_data = request.session.get('signup_data')
        form = SignUpForm(initial=signup_data)
        return render(request, 'signup.html', {'form': form})


def signup_confirm_view(request):
    """
    ユーザー登録の確認・登録実行を行うビュー
    """
    # セッションからフォームデータを取得
    signup_data = request.session.get('signup_data')
    if not signup_data:
        # セッションにデータがなければ入力画面に強制的に戻す
        return redirect('Sotsuken_Portable:signup')

    # POSTリクエスト（「登録する」ボタンが押された）の場合
    if request.method == 'POST':
        form = SignUpForm(signup_data)  # セッションデータでフォームを再構築

        if form.is_valid():
            # データベースにユーザー情報を保存
            user = form.save()

            # 使い終わったセッション情報を削除
            del request.session['signup_data']

            # (任意) 登録後、自動でログインさせる
            # login(request, user)

            # 完了画面へリダイレクト
            return redirect('Sotsuken_Portable:signup_done')

        # もし何らかの理由でデータが無効なら入力画面に戻す
        else:
            # エラーを持って入力画面に戻ることも可能
            # return render(request, 'Sotsuken_Portable/signup.html', {'form': form})
            return redirect('Sotsuken_Portable:signup')

    # GETリクエスト（入力画面から遷移してきた）の場合
    else:
        # フォームにセッションのデータを渡して、確認画面テンプレートに渡す
        form = SignUpForm(initial=signup_data)
        return render(request, 'signup_confirm.html', {'form': form})


def signup_done_view(request):
    """
    ユーザー登録完了画面を表示するビュー
    """
    return render(request, 'signup_done.html')


@login_required
def safety_check_view(request):
    """
    安否確認・支援要請ページの表示とフォーム処理
    """
    user = request.user

    # --- 1. 自分の現在の安否情報を取得 ---
    try:
        my_status = getattr(user, 'safety_status_record', None)
    except SafetyStatus.DoesNotExist:
        my_status = None

    safety_form = None
    support_form = None

    # --- 2. フォームの処理 (POST) ---
    if request.method == 'POST':

        # ▼▼▼ パターンA: 安否報告 ▼▼▼
        if 'submit_safety' in request.POST:
            instance = my_status if my_status else SafetyStatus(user=user)
            safety_form = SafetyStatusForm(request.POST, instance=instance)
            support_form = SupportRequestForm()  # もう片方は空で初期化

            if safety_form.is_valid():
                # save()は1回でOKです。戻り値でオブジェクトを受け取れます。
                status_obj = safety_form.save()

                messages.success(request, '安否情報を更新しました。')

                # 履歴の作成
                SafetyStatusHistory.objects.create(
                    user=user,
                    status=status_obj.status,
                    message=status_obj.message,
                )
                return redirect('Sotsuken_Portable:safety_check')
            else:
                # バリデーションエラー時
                print("Safety Form Errors:", safety_form.errors)  # ★デバッグ用
                messages.error(request, '安否報告の入力内容にエラーがあります。')

        # ▼▼▼ パターンB: 支援要請 ▼▼▼
        elif 'submit_support' in request.POST:
            support_form = SupportRequestForm(request.POST)
            safety_form = SafetyStatusForm(instance=my_status)  # もう片方は現状維持

            if support_form.is_valid():
                instance = support_form.save(commit=False)
                instance.requester = user
                instance.status = 'pending'
                instance.save()

                messages.success(request, '支援要請を送信しました。')
                return redirect('Sotsuken_Portable:safety_check')
            else:
                # バリデーションエラー時
                # ★ここが重要！なぜ保存されなかったかがターミナルに出ます
                print("Support Form Errors:", support_form.errors)
                messages.error(request, '支援要請の送信に失敗しました。入力内容を確認してください。')

    # --- 3. フォーム初期化 (GET or Error) ---
    # POST処理でエラーだった場合、入力内容を保持したままフォームを表示するために
    # ここで None の場合のみ初期化するようにします。
    if not safety_form:
        safety_form = SafetyStatusForm(instance=my_status)
    if not support_form:
        support_form = SupportRequestForm()

    # --- 4. 表示用データの取得 ---
    safety_list = SafetyStatus.objects.exclude(user=user).order_by('-last_updated')

    request_list = SupportRequest.objects.exclude(
        status__in=['resolved', 'cancelled']
    ).order_by('-requested_at')

    context = {
        'my_status': my_status,
        'safety_form': safety_form,
        'support_form': support_form,
        'safety_list': safety_list,
        'request_list': request_list,
    }

    return render(request, 'safety_check.html', context)


@login_required
def safety_history_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    history_list = SafetyStatusHistory.objects.filter(user=target_user)

    context = {
        'target_user': target_user,
        'history_list': history_list
    }
    return render(request, 'safety_history.html', context)


# ★★★ 修正: 解決済みアクションのビュー ★★★
@login_required
def resolve_support_request_view(request, pk):
    """支援要請を「解決済み」にする"""

    # 権限チェック
    if request.user.role not in ['admin', 'rescuer'] and not request.user.is_superuser:
        messages.error(request, "権限がありません。")
        return redirect('Sotsuken_Portable:safety_check')

    if request.method == 'POST':
        req = get_object_or_404(SupportRequest, pk=pk)

        # ★★★ 修正: statusフィールドを更新 ★★★
        req.status = 'resolved'
        req.save()

        messages.success(request, f"支援要請（{req.get_category_display()}）を解決済みにしました。")

    return redirect('Sotsuken_Portable:safety_check')



def emergency_sos_view(request):
    """
    緊急SOS発信ページの表示と、SOS情報の受付処理
    """
    # POSTリクエスト（SOSボタンが押されて位置情報が送信された）の場合
    if request.method == 'POST':
        # フォームから緯度と経度を取得
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        guest_name_input = request.POST.get('guest_name', '匿名')

        # 緯度・経度が正常に取れているかチェック
        if latitude and longitude:

            # ★★★ 分岐処理 ★★★
            if request.user.is_authenticated:
                # ログインしている場合
                reporter_user = request.user
                saved_guest_name = ""  # ユーザーがいるならゲスト名は空でOK
            else:
                # ログインしていない場合
                reporter_user = None
                # 入力が空文字なら'匿名'にする
                saved_guest_name = guest_name_input if guest_name_input.strip() else '匿名'

            # SOSレポートをデータベースに作成
            SOSReport.objects.create(
                reporter=reporter_user,
                guest_name=saved_guest_name,
                latitude=latitude,
                longitude=longitude,
            )

            # 完了ページへリダイレクト
            return redirect('Sotsuken_Portable:emergency_sos_done')

        else:
            messages.error(request, '位置情報の取得に失敗しました。GPSを有効にして再度お試しください。')
            return render(request, 'emergency_sos.html')

    # GETリクエスト（初めてページを開いた）の場合
    return render(request, 'emergency_sos.html')


@login_required
def emergency_sos_done_view(request):
    """
    SOS発信完了ページを表示するビュー
    """
    return render(request, 'emergency_sos_done.html')


@login_required
def map_view(request):
    shelters = Shelter.objects.all()
    shelters_data = []
    for shelter in shelters:
        shelters_data.append({
            'name': shelter.name,
            'lat': shelter.latitude,
            'lng': shelter.longitude,
            'address': shelter.address,
            'capacity': shelter.max_capacity,
            'occupancy': shelter.current_occupancy,
        })
    shelters_json = json.dumps(shelters_data)

    context = {
        'shelters_json': shelters_json,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,  # APIキーをテンプレートに渡す
    }

    return render(request, 'map.html', context)


@login_required
def emergency_info_view(request):
    # 1. 行政情報、避難所情報の取得 (既存)
    alerts = OfficialAlert.objects.all()
    shelters = Shelter.objects.all()

    # 2. 全ての有効な配布情報を取得
    all_distributions = DistributionInfo.objects.exclude(status='ended').order_by('status', 'start_time')

    # 3. ★★★ ユーザーの場所に基づく振り分け ★★★
    my_shelter_distributions = []
    other_distributions = []

    # ユーザーの最終確認場所を取得 (例: "〇〇小学校")
    user_location = request.user.last_known_location

    for dist in all_distributions:
        # 配布情報に避難所が紐付いていて、かつ名前が一致する場合
        # (または location_name が一致する場合)
        is_match = False

        if dist.shelter and dist.shelter.name == user_location:
            is_match = True
        elif dist.location_name and dist.location_name == user_location:
            is_match = True

        if is_match:
            my_shelter_distributions.append(dist)
        else:
            other_distributions.append(dist)

    context = {
        'alerts': alerts,
        'shelters': shelters,
        'my_distributions': my_shelter_distributions,  # あなたの避難所用
        'other_distributions': other_distributions,  # その他
    }
    return render(request, 'emergency_info.html', context)


@login_required
def user_menu_view(request):
    """
    ユーザーメインメニューページを表示するビュー
    """
    return render(request, 'user_menu.html')

@admin_required # ← この1行を追加するだけで、このビューは管理者/救助者しかアクセスできなくなる
def admin_menu_view(request):
    """
    管理者向けメニューページを表示するビュー
    """
    return render(request, 'admin_menu.html')

@admin_required
def user_management_view(request):
    """
    登録ユーザーの一覧と安否情報を表示する管理者向けビュー
    """
    # select_related を使って、User と SafetyStatus を効率的に一括取得
    user_list = User.objects.select_related('safety_status_record').order_by('username')

    context = {
        'user_list': user_list
    }
    return render(request, 'user_management.html', context)


@admin_required
def user_delete_view(request, user_id):
    """
    ユーザーを削除するビュー（確認画面付き）
    """
    # 削除対象のユーザーオブジェクトを取得。存在しなければ404エラー。
    user_to_delete = get_object_or_404(User, pk=user_id)

    # POSTリクエストの場合（削除実行）
    if request.method == 'POST':
        # 自分自身を削除しようとしていないかチェック（安全対策）
        if user_to_delete == request.user:
            messages.error(request, "自分自身のアカウントは削除できません。")
            return redirect('Sotsuken_Portable:user_management')

        # ユーザーを削除
        deleted_user_username = user_to_delete.username
        user_to_delete.delete()

        messages.success(request, f"ユーザー「{deleted_user_username}」を削除しました。")
        return redirect('Sotsuken_Portable:user_management')

    # GETリクエストの場合（確認画面の表示）
    context = {
        'user_to_delete': user_to_delete
    }
    return render(request, 'user_confirm_delete.html', context)

@require_POST # このビューはPOSTリクエストしか受け付けない
@admin_required
def user_change_role_view(request, user_id):
    """
    ユーザーのロールを変更する処理を行うビュー
    """
    user_to_change = get_object_or_404(User, pk=user_id)
    new_role = request.POST.get('role') # テンプレートから送られてきた新しいロールを取得

    # 有効なロールかどうかの簡単なチェック
    valid_roles = [role[0] for role in User.ROLE_CHOICES]
    if new_role in valid_roles:
        # 自分自身のロールは変更できないようにする（安全対策）
        if user_to_change == request.user:
            messages.error(request, "自分自身のロールは変更できません。")
        else:
            user_to_change.role = new_role
            user_to_change.save()
            messages.success(request, f"ユーザー「{user_to_change.username}」のロールを「{user_to_change.get_role_display()}」に変更しました。")
    else:
        messages.error(request, "無効なロールが指定されました。")

    return redirect('Sotsuken_Portable:user_management')


@admin_required
def shelter_management_view(request):
    """
    避難所の一覧表示と新規登録を行うビュー
    """
    # 新規登録フォームの処理 (POSTリクエスト)
    if request.method == 'POST':
        form = ShelterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '新しい避難所を登録しました。')
            return redirect('Sotsuken_Portable:shelter_management')
        # エラーがある場合は、エラー情報を含んだフォームがそのまま下に渡される

    # 通常の画面表示 (GETリクエスト) またはフォームエラー時
    else:
        form = ShelterForm()

    # 登録済みの全避難所を取得
    shelter_list = Shelter.objects.all().order_by('name')

    context = {
        'form': form,
        'shelter_list': shelter_list
    }
    return render(request, 'shelter_management.html', context)


# --- 避難所編集ビュー ---
@admin_required
def shelter_edit_view(request, management_id):
    """
    既存の避難所情報を編集するビュー
    """
    shelter_instance = get_object_or_404(Shelter, management_id=management_id)

    # POSTリクエスト（フォームが送信された）の場合
    if request.method == 'POST':
        # 既存のインスタンスに、送信されたデータを上書きする形でフォームを作成
        form = ShelterForm(request.POST, instance=shelter_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"避難所「{shelter_instance.name}」の情報を更新しました。")
            return redirect('Sotsuken_Portable:shelter_management')

    # GETリクエスト（編集ページを初めて開いた）の場合
    else:
        # 既存のインスタンスの情報をフォームにセットして表示
        form = ShelterForm(instance=shelter_instance)

    context = {
        'form': form,
        'shelter': shelter_instance  # テンプレートで避難所名などを表示するために渡す
    }
    return render(request, 'shelter_edit.html', context)


# --- 避難所削除ビュー ---
@admin_required
def shelter_delete_view(request, management_id):
    """
    避難所を削除するビュー（確認ページ付き）
    """
    shelter_to_delete = get_object_or_404(Shelter, management_id=management_id)

    # POSTリクエストの場合（削除実行）
    if request.method == 'POST':
        deleted_shelter_name = shelter_to_delete.name
        shelter_to_delete.delete()
        messages.success(request, f"避難所「{deleted_shelter_name}」を削除しました。")
        return redirect('Sotsuken_Portable:shelter_management')

    # GETリクエストの場合（確認画面の表示）
    context = {
        'shelter': shelter_to_delete
    }
    return render(request, 'shelter_confirm_delete.html', context)


@admin_required
def sos_report_list_view(request):
    """
    SOSレポートの一覧を表示するビュー
    """
    # select_related('reporter') を使って、SOSReportと発信者(User)の情報を効率的に一括取得
    # 新しいレポートが上に来るように、 reported_at の降順で並び替え
    report_list = SOSReport.objects.select_related('reporter').order_by('-reported_at')

    context = {
        'report_list': report_list
    }
    return render(request, 'sos_report_list.html', context)


# --- SOSレポート 状況更新ビュー ---
@require_POST
@admin_required
def sos_report_update_status_view(request, report_id):
    report = get_object_or_404(SOSReport, pk=report_id)
    new_status = request.POST.get('status')

    # SOSReportモデルで定義されている有効なステータスかチェック
    valid_statuses = [status[0] for status in SOSReport.STATUS_CHOICES]
    if new_status in valid_statuses:
        report.status = new_status
        report.save()
        messages.success(request, f"レポート(ID:{report.id})の状況を「{report.get_status_display()}」に更新しました。")
    else:
        messages.error(request, "無効なステータスです。")

    return redirect('Sotsuken_Portable:sos_report_list')


# --- SOSレポート 削除ビュー ---
# こちらは確認画面を挟むため、GETとPOST両方を受け付ける
@admin_required
def sos_report_delete_view(request, report_id):
    report_to_delete = get_object_or_404(SOSReport, pk=report_id)

    if request.method == 'POST':
        report_to_delete.delete()
        messages.success(request, f"レポート(ID:{report_id})を削除しました。")
        return redirect('Sotsuken_Portable:sos_report_list')

    # GETリクエストの場合は確認ページを表示
    context = {
        'report': report_to_delete
    }
    return render(request, 'sos_report_confirm_delete.html', context)

@admin_required
def sos_report_export_csv_view(request):
    """
    SOSレポートをCSVファイルとしてエクスポートするビュー
    """
    # HTTPレスポンスのヘッダーを設定
    response = HttpResponse(content_type='text/csv')
    # 日本語のファイル名が文字化けしないように設定
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sos_reports_{current_time}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # ★重要: Excelで日本語が文字化けしないように、BOM付きUTF-8でエンコード
    response.write('\ufeff'.encode('utf8'))

    # CSVライターを作成
    writer = csv.writer(response)

    # 1. ヘッダー行を書き込む
    writer.writerow([
        'レポートID',
        '発信日時',
        '発信者ログインID',
        '発信者氏名',
        '緯度',
        '経度',
        '対応状況',
        '状況メモ'
    ])

    # 2. データ行を書き込む
    reports = SOSReport.objects.select_related('reporter').all()
    for report in reports:
        writer.writerow([
            report.id,
            report.reported_at.strftime('%Y-%m-%d %H:%M:%S'),
            report.reporter.username if report.reporter else '',
            report.reporter.full_name if report.reporter else '(削除されたユーザー)',
            report.latitude,
            report.longitude,
            report.get_status_display(), # 'pending' -> '未対応' のように変換
            report.situation_notes
        ])

    return response

@login_required
def chat_group_list_view(request):
    """
    ユーザーが所属するグループの一覧を表示するビュー
    """
    # ユーザーがメンバーとして所属しているGroupMemberオブジェクトを取得
    memberships = request.user.group_memberships.all()
    # そこからGroupオブジェクトのリストを取得
    chat_groups = [m.group for m in memberships]

    return render(request, 'chat_group_list.html', {'chat_groups': chat_groups})


@login_required
def chat_room_view(request, group_id):
    """
    特定のグループのチャットルームを表示するビュー
    """
    try:
        group = Group.objects.get(id=group_id)
        # (セキュリティ) ユーザーがこのグループのメンバーか確認
        if not group.memberships.filter(member=request.user).exists():
            # メンバーでなければアクセスを拒否
            return redirect('Sotsuken_Portable:chat_group_list')

        # 過去のメッセージを取得
        messages = Message.objects.filter(group=group).order_by('timestamp')

        context = {
            'group': group,
            'chat_messages': messages,
        }

        # ★ 既読日時を更新
        ReadState.objects.update_or_create(
            user=request.user,
            group=group,
            defaults={'last_read_at': timezone.now()}
        )

        return render(request, 'chat.html', context)
    except Group.DoesNotExist:
        return redirect('Sotsuken_Portable:chat_group_list')


@login_required
def dm_user_list_view(request):
    """
    DMユーザー一覧＆ユーザー検索画面
    """
    current_user = request.user
    search_query = request.GET.get('q')
    search_results = []

    # --- 1. 検索機能 (変更なし) ---
    if search_query:
        users = User.objects.filter(
            Q(username__icontains=search_query) | Q(full_name__icontains=search_query)
        ).exclude(id=current_user.id)

        for user in users:
            user.can_chat = False
            user.connection_status = 'none'

            # A. 特権階級チェック
            if user.role in ['admin', 'rescuer'] or current_user.role in ['admin',
                                                                          'rescuer'] or current_user.is_superuser:
                user.can_chat = True
                user.connection_status = 'special'
            # B. 友達関係チェック
            else:
                conn = Connection.objects.filter(
                    (Q(requester=current_user, receiver=user) |
                     Q(requester=user, receiver=current_user))
                ).first()

                if conn:
                    user.connection_status = conn.status
                    if conn.status == 'accepted':
                        user.can_chat = True
                    elif conn.status == 'requesting':
                        if conn.requester == current_user:
                            user.connection_status = 'sent_request'
                        else:
                            user.connection_status = 'received_request'

            search_results.append(user)

    # 自分宛ての未承認リクエストを取得 (変更なし)
    received_requests = Connection.objects.filter(
        receiver=current_user,
        status='requesting'
    )
    requesting_users = [req.requester for req in received_requests]

    # --- 2. DMリスト (★修正: 管理者なら履歴ベース、一般なら友達ベース) ---
    dm_users = []

    # 管理者(admin/rescuer)またはスーパーユーザーの場合
    if current_user.role in ['admin', 'rescuer'] or current_user.is_superuser:
        # メッセージ履歴があるユーザーを取得 (自分が送信 or 自分に受信)
        # DMの場合、groupはnull, recipientはnot null

        # 1. 自分が送った相手のID
        sent_ids = Message.objects.filter(sender=current_user, recipient__isnull=False).values_list('recipient',
                                                                                                    flat=True)

        # 2. 自分に送ってきた相手のID
        received_ids = Message.objects.filter(recipient=current_user).values_list('sender', flat=True)

        # IDの集合を作成して重複排除
        contacted_ids = set(sent_ids) | set(received_ids)
        # 自分自身が含まれていた場合は除外(通常ありえないが念のため)
        contacted_ids.discard(current_user.id)

        # IDリストからユーザーオブジェクトを取得
        dm_users = User.objects.filter(id__in=contacted_ids)

    else:
        # 一般ユーザー: 既存の「友達(accepted)」ロジック
        connections = Connection.objects.filter(
            (Q(requester=current_user) | Q(receiver=current_user)),
            status='accepted'
        )
        friend_ids = []
        for c in connections:
            if c.requester == current_user:
                friend_ids.append(c.receiver.id)
            else:
                friend_ids.append(c.requester.id)

        dm_users = User.objects.filter(id__in=friend_ids)

    # --- 3. グループチャット一覧 & 未読判定 (変更なし) ---
    memberships = current_user.group_memberships.all()
    chat_groups = [m.group for m in memberships]

    # A. グループチャットの未読判定
    for group in chat_groups:
        read_state = ReadState.objects.filter(user=current_user, group=group).first()
        if read_state:
            last_read = read_state.last_read_at
        else:
            last_read = timezone.datetime.min.replace(tzinfo=datetime.timezone.utc)

        group.has_unread = Message.objects.filter(
            group=group,
            timestamp__gt=last_read
        ).exclude(sender=current_user).exists()

    # B. DMの未読判定
    # dm_users の中身がロールによって切り替わっているので、
    # そのまま回せば「履歴のあるユーザー」または「友達」の未読がチェックされます
    for user in dm_users:
        read_state = ReadState.objects.filter(user=current_user, dm_partner=user).first()
        if read_state:
            last_read = read_state.last_read_at
        else:
            last_read = timezone.datetime.min.replace(tzinfo=datetime.timezone.utc)

        user.has_unread = Message.objects.filter(
            sender=user,
            recipient=current_user,
            timestamp__gt=last_read
        ).exists()

    context = {
        'search_query': search_query,
        'search_results': search_results,
        'dm_users': dm_users,
        'requesting_users': requesting_users,
        'chat_groups': chat_groups,
    }
    return render(request, 'dm_user_list.html', context)


@login_required
def dm_room_view(request, user_id):
    """
    特定のユーザーとのDMルームページ
    """

    # 自分自身とのチャットは許可するか？（メモ代わりにするならOK、禁止なら弾く）
    if request.user.id == user_id:
        pass  # 今回は許可

    target_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # --- 権限チェックロジック ---
    is_allowed = False

    # 1. 特権階級（救助隊・管理者）への連絡は無条件で許可する（災害用なので）
    if target_user.role in ['admin', 'rescuer']:
        is_allowed = True

    # 2. 自分が特権階級なら、誰にでも連絡できる
    elif current_user.role in ['admin', 'rescuer']:
        is_allowed = True

    # 3. それ以外（一般人同士）は、友達関係が必要
    else:
        # A->B または B->A のどちらかで 'accepted' な関係があるか
        connection = Connection.objects.filter(
            (Q(requester=current_user, receiver=target_user) |
             Q(requester=target_user, receiver=current_user)),
            status='accepted'
        ).exists()
        if connection:
            is_allowed = True

    if not is_allowed:
        messages.error(request, "このユーザーとメッセージを送る権限がありません（友達登録が必要です）。")
        return redirect('Sotsuken_Portable:index')

    try:
        other_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('Sotsuken_Portable:dm_user_list')

    # 自分と相手の間で交わされたメッセージを取得 (groupがNULLのものに限定)
    chat_history = Message.objects.filter(
        group__isnull=True,  # グループチャットのメッセージを除外
        sender__in=[request.user, other_user],
        recipient__in=[request.user, other_user]
    ).order_by('timestamp')

    context = {
        'other_user': other_user,
        'chat_messages': chat_history,
    }

    ReadState.objects.update_or_create(
        user=request.user,
        dm_partner=other_user,
        defaults={'last_read_at': timezone.now()}
    )
    return render(request, 'dm_room.html', context)


@login_required
def search_users_view(request):
    results = []
    form = UserSearchForm(request.GET or None)

    if form.is_valid():
        query = form.cleaned_data['query']
        # 自分以外、かつIDか氏名が一致するユーザーを検索
        results = User.objects.filter(
            Q(username__icontains=query) | Q(full_name__icontains=query)
        ).exclude(id=request.user.id)

    # 各ユーザーとの現在の関係性を確認（テンプレートでボタンを出し分けるため）
    # 実際はテンプレート内でカスタムタグ等を使うか、リストを加工して渡します

    context = {
        'form': form,
        'results': results,
    }
    return render(request, 'Sotsuken_Portable/user_search.html', context)


@login_required
def send_connection_request_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)

    # 重複チェック
    if Connection.objects.filter(requester=request.user, receiver=target_user).exists():
        messages.warning(request, "既に申請済みです。")
    elif Connection.objects.filter(requester=target_user, receiver=request.user).exists():
        messages.info(request, "相手から既に申請が来ています。承認してください。")
    else:
        Connection.objects.create(requester=request.user, receiver=target_user, status='requesting')
        messages.success(request, f"{target_user.username} さんに申請を送りました。")

    return redirect('Sotsuken_Portable:dm_user_list')  # 元の画面に戻る


@login_required
def approve_connection_request_view(request, user_id):
    """友達申請を承認するビュー"""
    requester = get_object_or_404(User, pk=user_id)

    # 自分宛て(receiver=request.user)の申請を探す
    connection = get_object_or_404(
        Connection,
        requester=requester,
        receiver=request.user,
        status='requesting'
    )

    # ステータスを承認済みに更新
    connection.status = 'accepted'
    connection.save()

    messages.success(request, f"{requester.username} さんと友達になりました！")
    return redirect('Sotsuken_Portable:dm_user_list')




def _internal_post_message(sender_user, group_id, message):
    try:
        channel_layer = channel_layers['default']
        chat_data = {
            'type': 'chat_message',
            'message': message,
            'sender': sender_user.full_name or sender_user.username,
        }
        target_group_name = f'chat_{group_id}'

        async_to_sync(channel_layer.group_send)(target_group_name, chat_data)
        return True, "Success"
    except Exception as e:
        return False, str(e)



# 1. 投稿一覧ビュー
class CommunityPostListView(LoginRequiredMixin, ListView):
    model = CommunityPost
    template_name = 'community_list.html'
    context_object_name = 'post_list' # テンプレートで使う変数名を指定
    paginate_by = 10 # 1ページに10件まで表示（ページネーション）


# 2. 投稿詳細ビュー
class CommunityPostDetailView(LoginRequiredMixin, generic.View):
    # GETとPOSTで処理を分けるため、generic.DetailViewからgeneric.Viewに変更

    def get(self, request, *args, **kwargs):
        """GETリクエスト時の処理（詳細ページの表示）"""
        post = get_object_or_404(CommunityPost, pk=self.kwargs['pk'])
        comments = post.comments.all()
        comment_form = CommentForm()  # 空のコメントフォーム

        context = {
            'post': post,
            'comments': comments,
            'comment_form': comment_form,
        }
        return render(request, 'community_detail.html', context)

    def post(self, request, *args, **kwargs):
        """POSTリクエスト時の処理（コメントの投稿）"""
        post = get_object_or_404(CommunityPost, pk=self.kwargs['pk'])
        comment_form = CommentForm(request.POST)

        if comment_form.is_valid():
            # フォームからインスタンスを作成するが、まだDBには保存しない
            comment = comment_form.save(commit=False)
            # authorとpostを紐付ける
            comment.post = post
            comment.author = request.user
            comment.save()
            # 投稿後は同じページにリダイレクト（PRGパターン）
            return redirect('Sotsuken_Portable:community_detail', pk=post.pk)

        # フォームが無効だった場合は、エラーメッセージと共に再度ページを表示
        comments = post.comments.all()
        context = {
            'post': post,
            'comments': comments,
            'comment_form': comment_form,  # エラー情報を含んだフォーム
        }
        return render(request, 'community_detail.html', context)


# 3. 新規投稿ビュー
class CommunityPostCreateView(LoginRequiredMixin, CreateView):
    model = CommunityPost
    form_class = CommunityPostForm
    template_name = 'community_form.html'
    success_url = reverse_lazy('Sotsuken_Portable:community_list') # 成功時のリダイレクト先

    # フォームが送信されて、内容が正しい場合に呼ばれるメソッド
    def form_valid(self, form):
        # フォームの author フィールドに、現在ログインしているユーザーをセット
        form.instance.author = self.request.user
        # 親クラスのform_validを呼び出して、オブジェクトをDBに保存
        return super().form_valid(form)


class CommunityPostDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = CommunityPost
    template_name = 'community_confirm_delete.html'  # 確認ページのテンプレート
    success_url = reverse_lazy('Sotsuken_Portable:community_list')  # 削除成功後のリダイレクト先
    context_object_name = 'post'

    def dispatch(self, request, *args, **kwargs):
        """
        ビューが呼ばれた最初に実行されるメソッド。ここで権限チェックを行う。
        """
        # 削除対象の投稿オブジェクトを取得
        post = self.get_object()
        # ログイン中のユーザーを取得
        user = request.user

        # 投稿者本人でもなく、ロールが'admin'でもない場合
        if post.author != user and user.role != 'admin':
            # PermissionDenied例外を発生させ、403 Forbiddenページを表示
            raise PermissionDenied

        # 権限があれば、通常の処理を続ける
        return super().dispatch(request, *args, **kwargs)

class CommentDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Comment
    template_name = 'comment_confirm_delete.html'
    context_object_name = 'comment'

    def get_success_url(self):
        """削除成功後のリダイレクト先を動的に決定する"""
        # 削除されたコメントが紐づいていた投稿の詳細ページにリダイレクト
        post = self.object.post
        return reverse('Sotsuken_Portable:community_detail', kwargs={'pk': post.pk})

    def dispatch(self, request, *args, **kwargs):
        """権限チェック"""
        comment = self.get_object()
        user = request.user

        # 権限チェック：コメント投稿者 or 元の投稿の投稿者 or 管理者
        if (comment.author != user and
                comment.post.author != user and
                user.role != 'admin'):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

# 1. 自分が所属するグループ一覧ビュー
class GroupListView(LoginRequiredMixin, generic.ListView):
    model = Group
    template_name = 'group_list.html'
    context_object_name = 'group_list'

    # 表示するグループを、自分が所属しているものだけに絞り込む
    def get_queryset(self):
        return Group.objects.filter(memberships__member=self.request.user)


# 2. 新規グループ作成ビュー
class GroupCreateView(LoginRequiredMixin, generic.CreateView):
    model = Group
    form_class = GroupCreateForm
    template_name = 'group_form.html'
    success_url = reverse_lazy('Sotsuken_Portable:group_list') # 成功後は一覧ページへ

    def form_valid(self, form):
        # グループの作成者をログインユーザーに設定
        form.instance.creator = self.request.user
        # 親クラスのメソッドを呼び出してグループを保存
        response = super().form_valid(form)
        # ★重要: グループ作成者を、自動的にそのグループの最初のメンバー（管理者）として追加
        GroupMember.objects.create(
            group=self.object, # self.objectには作成されたGroupインスタンスが入っている
            member=self.request.user,
            role='admin' # グループ作成者はグループ管理者に設定
        )
        return response


# 3. グループ詳細ビュー
class GroupDetailView(LoginRequiredMixin, generic.DetailView):
    model = Group
    template_name = 'group_detail.html'
    context_object_name = 'group'

    # (セキュリティ) 自分が所属していないグループの詳細ページは見られないようにする
    def get_queryset(self):
        return Group.objects.filter(memberships__member=self.request.user)


class GroupDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Group
    template_name = 'group_confirm_delete.html'
    success_url = reverse_lazy('Sotsuken_Portable:group_list')
    context_object_name = 'group'

    def dispatch(self, request, *args, **kwargs):
        """権限チェック: グループ管理者のみ削除可能"""
        group = self.get_object()
        user = request.user

        # ログインユーザーが、このグループのメンバーであり、かつ役割が 'admin' であるかを確認
        is_group_admin = group.memberships.filter(member=user, role='admin').exists()

        if not is_group_admin:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class GroupLeaveView(LoginRequiredMixin, generic.View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=self.kwargs['pk'])
        user = request.user

        try:
            membership = GroupMember.objects.get(group=group, member=user)
        except GroupMember.DoesNotExist:
            # そもそもメンバーでなければ何もしない
            messages.error(request, 'あなたはこのグループのメンバーではありません。')
            return redirect('Sotsuken_Portable:group_list')

        # ★最後の管理者が脱退しようとした場合の考慮
        is_last_admin = (membership.role == 'admin' and
                         group.memberships.filter(role='admin').count() == 1)

        if is_last_admin:
            messages.error(request,
                           'あなたが最後の管理者であるため、グループから脱退できません。他のメンバーに管理者権限を譲渡してください。')
            return redirect('Sotsuken_Portable:group_detail', pk=group.pk)

        # メンバーシップを削除して脱退
        membership.delete()
        messages.success(request, f'グループ「{group.name}」から脱退しました。')
        return redirect('Sotsuken_Portable:group_list')

@login_required
def settings_view(request):
    """
    設定・プライバシー画面を表示するビュー
    """
    return render(request, 'settings.html')


@login_required
def user_profile_edit(request):
    """
    ユーザー情報とパスワードの編集を行うビュー
    """
    # ユーザー情報更新フォームの処理
    if 'user_update' in request.POST:
        user_form = UserUpdateForm(request.POST, instance=request.user)
        password_form = MyPasswordChangeForm(request.user)  # パスワードフォームは初期化
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'ユーザー情報を更新しました。')
            return redirect('Sotsuken_Portable:user_profile_edit')

    # パスワード変更フォームの処理
    elif 'password_change' in request.POST:
        password_form = MyPasswordChangeForm(request.user, request.POST)
        user_form = UserUpdateForm(instance=request.user)  # ユーザーフォームは初期化
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # パスワード変更後もログインを維持
            messages.success(request, 'パスワードを変更しました。')
            return redirect('Sotsuken_Portable:user_profile_edit')

    # GETリクエストの場合（通常の画面表示）
    else:
        user_form = UserUpdateForm(instance=request.user)
        password_form = MyPasswordChangeForm(request.user)

    context = {
        'user_form': user_form,
        'password_form': password_form
    }
    return render(request, 'user_profile_edit.html', context)


@login_required
def my_status_qr_view(request):
    user = request.user
    qr_data = {}
    try:
        safety_status = user.safety_status_record
        qr_data = {
            "t": "us",  # type: user_status
            "uid": str(user.id),
            "fn": user.full_name,
            "ss": safety_status.status, # 'safe' や 'help' などの内部コード
            "lu": safety_status.last_updated.strftime('%Y%m%d%H%M') # ハイフン等も削除
        }
    except SafetyStatus.DoesNotExist:
        qr_data = {"t": "us", "uid": str(user.id), "fn": user.full_name, "ss": "unknown"}

    context = {'qr_data_json': json.dumps(qr_data, ensure_ascii=False)}
    return render(request, 'my_status_qr.html', context)


# --- 2. グループ招待用QRコード用ビュー (新規作成) ---
@login_required
def group_invite_qr_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    # 招待用URLを生成
    # 例: http://127.0.0.1:8000/groups/join-by-code/xxxxxxxx-xxxx.../
    invite_url = request.build_absolute_uri(
        reverse('Sotsuken_Portable:group_join_by_code', kwargs={'invitation_code': group.invitation_code})
    )

    context = {
        'group': group,
        'qr_data_url': invite_url  # JSONではなくURLをテンプレートに渡す
    }
    return render(request, 'group_invite_qr.html', context)

# --- 3. QRコードスキャナー用ビュー (新規作成) ---
@login_required
def qr_scan_view(request):
    """
    QRコードを読み取るためのスキャナーページを表示する。
    このビューはテンプレートを表示するだけで、特別なロジックは不要。
    """
    return render(request, 'qr_scanner.html')

@login_required
def join_group_by_code_view(request, invitation_code):
    """
    招待コードを使ってグループに参加する処理を行うビュー
    """
    try:
        # 招待コードに一致するグループを検索
        group = Group.objects.get(invitation_code=invitation_code)

        # 既に参加済みでないかチェック
        is_member = GroupMember.objects.filter(group=group, member=request.user).exists()
        if is_member:
            messages.warning(request, f"あなたは既に「{group.name}」のメンバーです。")
        else:
            # メンバーとして追加
            GroupMember.objects.create(group=group, member=request.user, role='member')
            messages.success(request, f"「{group.name}」に参加しました！")

        # グループの詳細ページにリダイレクト
        return redirect('Sotsuken_Portable:group_detail', pk=group.pk)

    except Group.DoesNotExist:
        messages.error(request, "無効な招待コードです。")
        return redirect('Sotsuken_Portable:group_list')  # エラー時はグループ一覧へ

# --- ユーザーID QRコード用ビュー ---
@login_required
def user_id_qr_view(request):
    """
    ログインユーザーの「ログインID」をQRコードとして表示するためのビュー
    """
    # 変更前
    # user_id = str(request.user.id)

    # 変更後： user.id から user.username に変更
    username_str = str(request.user.username)

    context = {
        # テンプレートに渡す変数名も分かりやすく変更
        'username_str': username_str
    }
    return render(request, 'user_id_qr.html', context)

@login_required
def manual_list(request):
    """
    マニュアル一覧を表示するビュー
    """
    manuals = Manual.objects.all().order_by('-created_at')
    context = {
        'manuals': manuals,
    }
    return render(request, 'manual_list.html', context)

@login_required
# @user_passes_test(lambda u: u.is_superuser)  # 管理者のみに制限する場合
def rpi_checkin_log_view(request):
    # チェックイン系のログのみを抽出
    logs = RPiData.objects.filter(
        data_type__in=['shelter_checkin', 'sync_checkin', 'sync_checkout']
    ).order_by('-received_at')

    context = {
        'logs': logs,
        'title': '避難所受付データ連携ログ'
    }
    return render(request, 'rpi_data_log.html', context)

# --- 2. 炊き出し配布記録の確認 ---
@login_required
def distribution_log_view(request):
    records = DistributionRecord.objects.all().order_by('-distributed_at')

    context = {
        'records': records,
    }
    return render(request, 'distribution_log.html', context)


@login_required
def add_distribution_info_view(request):
    """炊き出し・物資配布情報を手動で追加するビュー"""

    # 権限チェック (管理者 or 救助隊 or スーパーユーザー)
    if request.user.role not in ['admin', 'rescuer'] and not request.user.is_superuser:
        messages.error(request, "情報の追加権限がありません。")
        return redirect('Sotsuken_Portable:emergency_info')  # 緊急情報ページへ戻す

    if request.method == 'POST':
        form = DistributionInfoForm(request.POST)
        if form.is_valid():
            # commit=False で一旦止める（まだDBには保存しない）
            dist_info = form.save(commit=False)

            # ★★★ 追加ロジック: 新規品目の登録 ★★★
            new_item_name = form.cleaned_data.get('new_item_name')

            if new_item_name:
                # 入力された名前で DistributionItem を作成 (get_or_create で重複防止)
                item, created = DistributionItem.objects.get_or_create(
                    name=new_item_name,
                    defaults={'description': f'{request.user.username}により自動追加'}
                )
                # 作成（または取得）したアイテムを紐付ける
                dist_info.related_item = item

                if created:
                    messages.info(request, f"品目マスタに「{new_item_name}」を追加しました。")

            # 保存実行
            dist_info.save()

            messages.success(request, f"「{dist_info.title}」の情報を登録しました。")
            return redirect('Sotsuken_Portable:emergency_info')
    else:
        form = DistributionInfoForm()

    context = {
        'form': form,
    }
    return render(request, 'add_distribution_info.html', context)


def get_nearby_alerts_view(request):
    """
    【AJAX用】緯度経度を受け取り、最も近いエリアの有効な警報をJSONで返す
    """
    # GETリクエスト以外は拒否しても良い
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'GET method required'}, status=405)

    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': '緯度経度が不正です'}, status=400)

    # 1. 一番近い JmaArea を探す
    nearest_area = None
    min_dist = float('inf')

    # エリア数が少なければ全件ループで十分高速です
    for area in JmaArea.objects.all():
        d = math.sqrt((area.latitude - lat) ** 2 + (area.longitude - lon) ** 2)
        if d < min_dist:
            min_dist = d
            nearest_area = area

    if not nearest_area:
        return JsonResponse({'status': 'success', 'alerts': [], 'area_name': '不明'})

    # 2. そのエリアに紐付く有効な警報を取得
    alerts = OfficialAlert.objects.filter(
        area=nearest_area,
        is_active=True
    ).order_by('-published_at')[:5]

    alert_data = [
        {
            'title': a.title,
            'severity': a.get_severity_display() if hasattr(a, 'get_severity_display') else a.severity,
            'content': a.content,
            'date': a.published_at.strftime('%Y/%m/%d %H:%M')
        } for a in alerts
    ]

    return JsonResponse({
        'status': 'success',
        'area_name': nearest_area.name,
        'alerts': alert_data
    }, json_dumps_params={'ensure_ascii': False})

