import csv
import datetime
import json

from asgiref.sync import async_to_sync
from channels.layers import channel_layers
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # ログイン必須にするためのデコレータ
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.views import generic
from django.views.decorators.http import require_POST
# generic から、使いたいクラスを直接インポートする
from django.views.generic import ListView, DetailView, CreateView, TemplateView

from Sotsuken_Portable.forms import SignUpForm, SafetyStatusForm, SupportRequestForm, CommunityPostForm, CommentForm, \
    GroupCreateForm, UserUpdateForm, MyPasswordChangeForm, ShelterForm
from Sotsuken_Portable.models import SafetyStatus, SupportRequest, SOSReport, Shelter, OfficialAlert, Group, Message, \
    CommunityPost, Comment, GroupMember, User, Manual, RPiData, DistributionRecord
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

@login_required()
def safety_check_view(request):
    """
    安否確認・支援要請ページの表示とフォーム処理を行うビュー
    """
    user = request.user

    # --- フォームの処理 (POSTリクエスト時) ---
    if request.method == 'POST':
        # どちらのフォームが送信されたかを判定
        # テンプレート側の送信ボタンに name属性 をつけておく
        if 'submit_safety' in request.POST:
            # 安否報告フォームが送信された場合
            # ログインユーザーの安否情報を取得 or なければ作成
            instance, created = SafetyStatus.objects.get_or_create(user=user)
            safety_form = SafetyStatusForm(request.POST, instance=instance)

            if safety_form.is_valid():
                safety_form.save()
                messages.success(request, '安否情報を更新しました。')
                return redirect('Sotsuken_Portable:safety_check')

            # エラーがあった場合は、もう片方のフォームは空で初期化
            support_form = SupportRequestForm()

        elif 'submit_support' in request.POST:
            # 支援要請フォームが送信された場合
            support_form = SupportRequestForm(request.POST)

            if support_form.is_valid():
                # DBに保存する前に、requesterをログインユーザーに設定
                instance = support_form.save(commit=False)
                instance.requester = user
                instance.save()
                messages.success(request, '支援要請を送信しました。')
                return redirect('Sotsuken_Portable:safety_check')

            # エラーがあった場合は、もう片方のフォームはユーザーの現在の状態で初期化
            safety_form = SafetyStatusForm(instance=user.safety_status_record)

    # --- ページの表示 (GETリクエスト時 or フォームエラー時) ---
    else:
        # ログインユーザーの現在の安否情報をフォームの初期値に設定
        try:
            my_status = user.safety_status_record
        except SafetyStatus.DoesNotExist:
            my_status = None

        if my_status:
            safety_form = SafetyStatusForm(instance=my_status)
        else:
            safety_form = SafetyStatusForm()

        support_form = SupportRequestForm()

        # --- 表示用データの準備 ---
        safety_list = SafetyStatus.objects.exclude(user=user).order_by('-last_updated')
        request_list = SupportRequest.objects.filter(status='pending').order_by('-requested_at')

        context = {
            'my_status': my_status,  # <-- 自分の安否情報を追加
            'safety_form': safety_form,
            'support_form': support_form,
            'safety_list': safety_list,
            'request_list': request_list,
        }

        return render(request, 'safety_check.html', context)

@login_required
def emergency_sos_view(request):
    """
    緊急SOS発信ページの表示と、SOS情報の受付処理
    """
    # POSTリクエスト（SOSボタンが押されて位置情報が送信された）の場合
    if request.method == 'POST':
        # フォームから緯度と経度を取得
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        # 緯度・経度が正常に取れているかチェック
        if latitude and longitude:
            # SOSレポートをデータベースに作成
            SOSReport.objects.create(
                reporter=request.user,
                latitude=latitude,
                longitude=longitude,
            )
            # 完了ページへリダイレクト
            return redirect('Sotsuken_Portable:emergency_sos_done')
        else:
            # もし位置情報が取得できていなければ、エラーメッセージと共に元のページに戻る
            messages.error(request, '位置情報の取得に失敗しました。再度お試しください。')
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
    """
    緊急情報ポータルページを表示するビュー
    """
    # 1. 行政からの最新情報を取得
    alerts = OfficialAlert.objects.all()

    # 2. 全ての避難所の情報を取得
    shelters = Shelter.objects.all()

    context = {
        'alerts': alerts,
        'shelters': shelters,
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
    user_list = User.objects.select_related('safety_status_record').order_by('login_id')

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
        deleted_user_login_id = user_to_delete.login_id
        user_to_delete.delete()

        messages.success(request, f"ユーザー「{deleted_user_login_id}」を削除しました。")
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
            messages.success(request, f"ユーザー「{user_to_change.login_id}」のロールを「{user_to_change.get_role_display()}」に変更しました。")
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
            report.reporter.login_id if report.reporter else '',
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
            'messages': messages,
        }
        return render(request, 'chat.html', context)
    except Group.DoesNotExist:
        return redirect('Sotsuken_Portable:chat_group_list')


@login_required
def dm_user_list_view(request):
    """
    DM相手と、参加中グループチャットへの入り口ページ
    """
    # 1. 自分以外の全ユーザーを取得 (DM相手用)
    dm_users = User.objects.exclude(pk=request.user.pk)

    # 2. 自分が所属するグループの一覧を取得 (グループチャット用)
    chat_groups = Group.objects.filter(memberships__member=request.user)

    context = {
        'dm_users': dm_users,
        'chat_groups': chat_groups,
    }

    # テンプレート名をより実態に合った 'chat_index.html' などに変更しても良い
    return render(request, 'dm_user_list.html', context)


@login_required
def dm_room_view(request, user_id):
    """
    特定のユーザーとのDMルームページ
    """
    try:
        other_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('Sotsuken_Portable:dm_user_list')

    # 自分と相手の間で交わされたメッセージを取得 (groupがNULLのものに限定)
    messages = Message.objects.filter(
        group__isnull=True,  # グループチャットのメッセージを除外
        sender__in=[request.user, other_user],
        recipient__in=[request.user, other_user]
    ).order_by('timestamp')

    context = {
        'other_user': other_user,
        'messages': messages,
    }
    return render(request, 'dm_room.html', context)


def _internal_post_message(sender_user, group_id, message):
    try:
        channel_layer = channel_layers['default']
        chat_data = {
            'type': 'chat_message',
            'message': message,
            'sender': sender_user.full_name or sender_user.login_id,
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
            "uid": user.id,
            "fn": user.full_name,
            "ss": safety_status.status, # 'safe' や 'help' などの内部コード
            "lu": safety_status.last_updated.strftime('%Y%m%d%H%M') # ハイフン等も削除
        }
    except SafetyStatus.DoesNotExist:
        qr_data = {"t": "us", "uid": user.id, "fn": user.full_name, "ss": "unknown"}

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

    # 変更後： user.id から user.login_id に変更
    login_id_str = str(request.user.login_id)

    context = {
        # テンプレートに渡す変数名も分かりやすく変更
        'login_id_str': login_id_str
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

