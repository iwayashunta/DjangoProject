from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Sotsuken_Portable.utils import send_email_to_user, send_email_to_users

User = get_user_model()

class Command(BaseCommand):
    help = 'ユーザーにメールを送信します'

    def add_arguments(self, parser):
        parser.add_argument('--subject', type=str, default='お知らせ', help='件名')
        parser.add_argument('--body', type=str, default='テストメールです。', help='本文')
        
        # 送信先の指定方法
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--all', action='store_true', help='全ユーザーに送信')
        group.add_argument('--user-id', type=int, nargs='+', help='特定のユーザーID（複数可）')
        group.add_argument('--email', type=str, help='直接メールアドレスを指定（テスト用）')

    def handle(self, *args, **options):
        subject = options['subject']
        body = options['body']

        if options['all']:
            # 全ユーザー送信
            users = User.objects.all()
            self.stdout.write(f'{users.count()}人のユーザーに送信を開始します...')
            result = send_email_to_users(users, subject, body)
            self.stdout.write(self.style.SUCCESS(f"成功: {result['success']}, 失敗: {result['failure']}"))
            if result['errors']:
                self.stdout.write(self.style.WARNING("エラー詳細:\n" + "\n".join(result['errors'])))

        elif options['user_id']:
            # 特定ユーザー送信
            users = User.objects.filter(id__in=options['user_id'])
            if not users.exists():
                self.stdout.write(self.style.ERROR('指定されたIDのユーザーが見つかりません。'))
                return
            
            result = send_email_to_users(users, subject, body)
            self.stdout.write(self.style.SUCCESS(f"成功: {result['success']}, 失敗: {result['failure']}"))

        elif options['email']:
            # 直接アドレス指定（既存のsend_mailをラップする簡易的な処理）
            from django.core.mail import send_mail
            from django.conf import settings
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [options['email']])
                self.stdout.write(self.style.SUCCESS(f"{options['email']} に送信しました。"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"送信失敗: {e}"))
