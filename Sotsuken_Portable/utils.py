from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

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
