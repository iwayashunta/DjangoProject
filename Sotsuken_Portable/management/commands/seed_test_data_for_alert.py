from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Sotsuken_Portable.models import JmaArea

User = get_user_model()

class Command(BaseCommand):
    help = '警報メール送信テスト用のエリアとユーザーのダミーデータを作成します'

    def handle(self, *args, **options):
        self.stdout.write("テストデータの作成を開始します...")

        # 1. テスト用のエリア情報を作成 (広島市役所)
        # update_or_create: 既にあれば更新、なければ作成
        area, created = JmaArea.objects.update_or_create(
            code='3410000',  # 広島県のコード
            defaults={
                'name': '広島県',
                'latitude': 34.3852,  # 広島市役所の緯度
                'longitude': 132.4553, # 広島市役所の経度
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"テストエリア '{area.name}' を作成しました。"))
        else:
            self.stdout.write(self.style.WARNING(f"テストエリア '{area.name}' は既に存在します。"))

        # 2. エリアに近いユーザーを作成
        nearby_user_data = {
            'username': 'nearby_user',
            'email': 'nearby_user@example.com', # ★メールが届く自分のアドレスに変更するとテストしやすい
            'full_name': '近隣 太郎',
            'last_known_latitude': 34.386, # エリアに非常に近い
            'last_known_longitude': 132.456,
        }
        user1, created = User.objects.update_or_create(
            username=nearby_user_data['username'],
            defaults=nearby_user_data
        )
        if created:
            user1.set_password('password') # パスワードを設定
            user1.save()
            self.stdout.write(self.style.SUCCESS(f"テストユーザー '{user1.username}' を作成しました。"))
        else:
            self.stdout.write(self.style.WARNING(f"テストユーザー '{user1.username}' は既に存在します。"))


        # 3. エリアから遠いユーザーを作成
        far_user_data = {
            'username': 'far_user',
            'email': 'far_user@example.com',
            'full_name': '遠方 次郎',
            'last_known_latitude': 35.0, # エリアから遠い
            'last_known_longitude': 135.0,
        }
        user2, created = User.objects.update_or_create(
            username=far_user_data['username'],
            defaults=far_user_data
        )
        if created:
            user2.set_password('password')
            user2.save()
            self.stdout.write(self.style.SUCCESS(f"テストユーザー '{user2.username}' を作成しました。"))
        else:
            self.stdout.write(self.style.WARNING(f"テストユーザー '{user2.username}' は既に存在します。"))

        self.stdout.write(self.style.SUCCESS("テストデータの準備が完了しました。"))
