from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.signing import TimestampSigner
from django.urls import reverse

# User = get_user_model()  <-- ここで実行すると循環インポートになるため削除

def send_email_to_user(user, subject, body):
    """
    特定のユーザーにメールを送信する関数
    """
    if not user.email:
        return False, "メールアドレスが登録されていません"

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True, "送信成功"
    except Exception as e:
        return False, str(e)

def send_email_to_users(users, subject, body):
    """
    ユーザーのリスト（QuerySetなど）にメールを一斉送信する関数
    """
    success_count = 0
    failure_count = 0
    errors = []

    for user in users:
        success, message = send_email_to_user(user, subject, body)
        if success:
            success_count += 1
        else:
            failure_count += 1
            errors.append(f"{user.username}: {message}")

    return {
        'success': success_count,
        'failure': failure_count,
        'errors': errors
    }

def send_sos_notification(report):
    """
    SOSレポートの内容を管理者(admin, rescuer)にHTMLメールで通知する
    """
    User = get_user_model() # ★ ここで取得する

    print(f"[DEBUG] SOS通知処理開始: Report ID={report.id}")

    # 送信対象: 管理者と救助隊
    admins = User.objects.filter(role__in=['admin', 'rescuer'], is_active=True).exclude(email='')
    
    if not admins.exists():
        print("[DEBUG] 送信対象の管理者が見つかりません。")
        # スーパーユーザーも確認してみる
        admins = User.objects.filter(is_superuser=True, is_active=True).exclude(email='')
        if not admins.exists():
             print("[DEBUG] 送信対象のスーパーユーザーも見つかりません。メール送信を中止します。")
             return

    print(f"[DEBUG] 送信対象者数: {admins.count()}名")
    for admin in admins:
        print(f"  - {admin.username} ({admin.email})")

    subject = f"【緊急SOS】{report.guest_name}さんから救助要請がありました"
    
    # HTMLテンプレートからメール本文を生成
    try:
        html_content = render_to_string('emails/sos_notification.html', {'report': report})
        text_content = strip_tags(html_content) # HTMLタグを除去してテキスト版を作成
    except Exception as e:
        print(f"[DEBUG] テンプレートレンダリングエラー: {e}")
        return

    # 管理者全員に送信
    for admin in admins:
        try:
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [admin.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            print(f"[DEBUG] {admin.username} へのメール送信成功")
        except Exception as e:
            print(f"[ERROR] {admin.username} へのメール送信失敗: {e}")

def send_quick_sos_email(user, request=None):
    """
    ユーザーにワンクリックSOS用のリンクを含むメールを送信する
    """
    if not user.email:
        return False, "メールアドレスがありません"

    signer = TimestampSigner()
    token = signer.sign(str(user.id)) # ユーザーIDを署名

    # URLを生成
    # requestがあれば絶対URLを生成できるが、ない場合（管理コマンドなど）はsettingsからドメインを取得する必要がある
    # ここでは簡易的にハードコードするか、requestを必須にするか、settingsにSITE_URLを定義する
    
    path = reverse('Sotsuken_Portable:quick_sos', kwargs={'user_id': user.id, 'token': token})
    
    if request:
        url = request.build_absolute_uri(path)
    else:
        # settings.SITE_URL があると仮定、なければlocalhost
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        url = f"{site_url}{path}"

    subject = "【重要】緊急SOS発信リンク"
    
    context = {
        'user': user,
        'sos_url': url,
        'expiration_hours': 24
    }
    
    try:
        html_content = render_to_string('emails/quick_sos_link.html', context)
        text_content = strip_tags(html_content)
        
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True, "送信成功"
    except Exception as e:
        return False, str(e)
