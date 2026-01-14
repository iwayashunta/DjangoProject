from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Sotsuken_Portable.utils import send_quick_sos_email

User = get_user_model()

class Command(BaseCommand):
    help = 'ユーザーにワンクリックSOSリンク付きのメールを送信します'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--user', type=str, help='送信対象のユーザー名(username)')
        group.add_argument('--id', type=str, help='送信対象のユーザーID(UUID)')
        group.add_argument('--email', type=str, help='送信対象のメールアドレス')
        group.add_argument('--all', action='store_true', help='全ユーザーに送信')

    def handle(self, *args, **options):
        users = []

        if options['all']:
            users = User.objects.filter(is_active=True).exclude(email='')
            self.stdout.write(f"全ユーザー({users.count()}名)を対象にします。")
        
        elif options['user']:
            try:
                user = User.objects.get(username=options['user'])
                users = [user]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"ユーザー名 '{options['user']}' は見つかりませんでした。"))
                return

        elif options['id']:
            try:
                user = User.objects.get(id=options['id'])
                users = [user]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"ID '{options['id']}' のユーザーは見つかりませんでした。"))
                return

        elif options['email']:
            users = User.objects.filter(email=options['email'])
            if not users.exists():
                self.stdout.write(self.style.ERROR(f"メールアドレス '{options['email']}' のユーザーは見つかりませんでした。"))
                return
            self.stdout.write(f"メールアドレス '{options['email']}' に一致するユーザー: {users.count()}名")

        # 送信処理
        success_count = 0
        for user in users:
            self.stdout.write(f"{user.username} ({user.email}) に送信中...", ending='')
            
            # メール送信
            success, message = send_quick_sos_email(user)
            
            if success:
                self.stdout.write(self.style.SUCCESS(" 成功"))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR(f" 失敗: {message}"))

        self.stdout.write(self.style.SUCCESS(f"完了: {success_count} / {len(users)} 件送信成功"))
