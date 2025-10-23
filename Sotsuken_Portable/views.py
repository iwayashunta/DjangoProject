from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required # ログイン必須にするためのデコレータ

from Sotsuken_Portable.forms import SignUpForm, SafetyStatusForm, SupportRequestForm
from Sotsuken_Portable.models import SafetyStatus, SupportRequest


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
            instance = user.safety_status_record
        except SafetyStatus.DoesNotExist:
            instance = None
        safety_form = SafetyStatusForm(instance=instance)

        # 支援要請フォームは空で初期化
        support_form = SupportRequestForm()

    # --- テンプレートに渡す表示用データを準備 ---
    # 他のユーザーの安否リスト (ここでは全ユーザーを対象に)
    safety_list = SafetyStatus.objects.exclude(user=user).order_by('-last_updated')

    # 支援要請リスト (未対応のもの)
    request_list = SupportRequest.objects.filter(status='pending').order_by('-requested_at')

    context = {
        'safety_form': safety_form,
        'support_form': support_form,
        'safety_list': safety_list,
        'request_list': request_list,
    }

    return render(request, 'safety_check.html', context)


