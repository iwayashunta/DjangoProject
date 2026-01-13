from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Sotsuken_Portable.utils import send_email_to_users

User = get_user_model()

class Command(BaseCommand):
    help = '条件を指定してユーザーに一斉メールを送信します'

    def add_arguments(self, parser):
        # 必須のメール内容
        parser.add_argument('--subject', type=str, required=True, help='メールの件名')
        parser.add_argument('--body', type=str, required=True, help='メールの本文')

        # フィルタリング条件（任意）
        parser.add_argument('--status', type=str, choices=['safe', 'help', 'unknown'], help='安否状況で絞り込み')
        parser.add_argument('--role', type=str, choices=['general', 'admin', 'rescuer'], help='ユーザーロールで絞り込み')
        parser.add_argument('--is-active', action='store_true', help='有効なユーザーのみに限定（デフォルトは全ユーザー対象）')

    def handle(self, *args, **options):
        subject = options['subject']
        body = options['body']
        
        # クエリセットの構築
        users = User.objects.all()

        # 条件適用
        filters = {}
        if options['status']:
            filters['safety_status'] = options['status']
        if options['role']:
            filters['role'] = options['role']
        if options['is_active']:
            filters['is_active'] = True
        
        if filters:
            users = users.filter(**filters)
            self.stdout.write(f"フィルタ条件: {filters}")
        else:
            self.stdout.write("フィルタ条件なし（全ユーザー対象）")

        # メールアドレスがないユーザーを除外
        users = users.exclude(email='')
        
        count = users.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('条件に一致する送信対象ユーザーがいません。'))
            return

        self.stdout.write(f"送信対象: {count} 名")
        self.stdout.write("-" * 30)
        
        # 送信実行
        # utils.py の send_email_to_users を利用
        result = send_email_to_users(users, subject, body)

        # 結果表示
        self.stdout.write(self.style.SUCCESS(f"送信完了: 成功 {result['success']} 件 / 失敗 {result['failure']} 件"))
        
        if result['errors']:
            self.stdout.write(self.style.WARNING("--- エラー詳細 ---"))
            for err in result['errors']:
                self.stdout.write(err)
