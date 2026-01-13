import math
from decimal import Decimal  # ★ Decimalをインポート

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from Sotsuken_Portable.models import OfficialAlert, JmaArea
from Sotsuken_Portable.utils import send_email_to_users

User = get_user_model()

class Command(BaseCommand):
    help = '気象庁の防災情報を取得します。 --demo をつけるとテスト用ダミーデータを作成します。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='広島県に大雨警報が発表されたと仮定して、メール送信テストを実行します。',
        )

    def handle(self, *args, **options):
        if options['demo']:
            self.create_demo_alert()
            return
        self.fetch_real_data()

    def create_demo_alert(self):
        self.stdout.write(self.style.WARNING("--- デモモードで実行 ---"))
        try:
            target_area = JmaArea.objects.get(code='3410000')
        except JmaArea.DoesNotExist:
            self.stderr.write("テスト用のエリア情報（広島県/3410000）が見つかりません。")
            self.stderr.write("先に python manage.py seed_test_data_for_alert を実行してください。")
            return

        title = f"【訓練】大雨警報 ({target_area.name})"
        content = (
            "これは訓練用の通知です。\n"
            "広島県で大雨警報が発表されました。今後の情報に注意してください。"
        )

        today = timezone.now().date()
        alert, created = OfficialAlert.objects.get_or_create(
            area=target_area,
            title=title,
            published_at__date=today,
            defaults={
                'content': content,
                'severity': 'high',
                'publisher': '気象庁(訓練)',
                'is_active': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"訓練用の警報データを作成しました: '{title}'"))
            self.process_updates([target_area])
        else:
            self.stdout.write(self.style.WARNING('本日の訓練用警報は既に作成済みです。'))


    def fetch_real_data(self):
        target_areas = JmaArea.objects.all()
        if not target_areas.exists():
            self.stderr.write("JmaAreaが登録されていません。load_jma_areasを実行してください。")
            return
        self.stdout.write(f"{target_areas.count()} 箇所のエリア情報を取得開始...")
        updated_areas = []
        for area in target_areas:
            url = f"https://www.jma.go.jp/bosai/warning/data/warning/{area.code}.json"
            self.stdout.write(f"{area.name} のエリア情報を取得中...", ending='')
            try:
                response = requests.get(url, timeout=5)
                self.stdout.write(" 完了！")
                if response.status_code != 200:
                    continue
                data = response.json()
                if 'headline' in data and data['headline']:
                    headline_text = data['headline'][0].get('text', '')
                    if not headline_text:
                        continue
                    if not OfficialAlert.objects.filter(
                            area=area,
                            content=headline_text,
                            published_at__date=timezone.now().date()
                    ).exists():
                        OfficialAlert.objects.create(
                            title=f"気象警報 ({area.name})",
                            content=headline_text,
                            severity='high',
                            publisher='気象庁',
                            is_active=True,
                            area=area
                        )
                        self.stdout.write(self.style.SUCCESS(f"[{area.name}] 新しい警報を保存"))
                        updated_areas.append(area)
            except Exception as e:
                self.stderr.write(f"[{area.name}] エラー: {e}")
        
        if updated_areas:
            self.process_updates(updated_areas)
        else:
            self.stdout.write("新しい警報はありませんでした。")

    def process_updates(self, areas):
        self.stdout.write(self.style.SUCCESS(f"計 {len(areas)} 箇所のエリアで更新がありました。対象ユーザーへの通知を開始します。"))
        
        # ★ 修正: Decimal型として定義
        SEARCH_RADIUS = Decimal('0.1')

        for area in areas:
            area_lat = area.latitude
            area_lon = area.longitude
            
            # Decimal同士の計算になるのでエラーにならない
            nearby_users = User.objects.filter(
                last_known_latitude__range=(area_lat - SEARCH_RADIUS, area_lat + SEARCH_RADIUS),
                last_known_longitude__range=(area_lon - SEARCH_RADIUS, area_lon + SEARCH_RADIUS),
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            count = nearby_users.count()
            if count > 0:
                self.stdout.write(f"エリア[{area.name}]周辺の対象ユーザー: {count}名")
                subject = f"【防災速報】{area.name}周辺で気象警報が発表されました"
                body = (
                    f"{area.name}周辺で新しい気象警報が発表されました。\n"
                    f"直ちに最新の情報を確認し、身の安全を確保してください。\n\n"
                    f"確認日時: {timezone.now().strftime('%Y/%m/%d %H:%M')}\n"
                    "※このメールは自動送信されています。"
                )
                result = send_email_to_users(nearby_users, subject, body)
                self.stdout.write(f"  -> 送信成功: {result['success']}, 失敗: {result['failure']}")
            else:
                self.stdout.write(f"エリア[{area.name}]周辺に対象ユーザーはいませんでした。")

    def get_nearest_area(self, lat, lon):
        min_distance = float('inf')
        nearest = None
        all_areas = JmaArea.objects.all()
        for area in all_areas:
            # ここはfloat計算のままでOK（Decimalとfloatの混在計算は、floatにキャストすれば可能）
            d_lat = float(area.latitude) - lat
            d_lon = float(area.longitude) - lon
            distance = math.sqrt(d_lat ** 2 + d_lon ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest = area
        return nearest
