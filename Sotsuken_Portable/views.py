import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # ログイン必須にするためのデコレータ
from django.urls import reverse_lazy, reverse
from django.views import generic
# generic から、使いたいクラスを直接インポートする
from django.views.generic import ListView, DetailView, CreateView

from Sotsuken_Portable.forms import SignUpForm, SafetyStatusForm, SupportRequestForm, CommunityPostForm, CommentForm, \
    GroupCreateForm
from Sotsuken_Portable.models import SafetyStatus, SupportRequest, SOSReport, Shelter, OfficialAlert, Group, Message, \
    CommunityPost, Comment, GroupMember
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

