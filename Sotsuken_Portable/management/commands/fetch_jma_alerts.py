import math

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from Sotsuken_Portable.models import OfficialAlert, JmaArea
from Sotsuken_Portable_Project import settings


class Command(BaseCommand):
    help = '気象庁の防災情報を取得します。 --demo をつけるとテスト用ダミーデータを作成します。'

    def add_arguments(self, parser):
        # テスト用の引数 --demo を定義
        parser.add_argument(
            '--demo',
            action='store_true',
            help='実際のAPIにはアクセスせず、テスト用の警報データを作成します',
        )

    def handle(self, *args, **options):
        # --- A. デモモード（テスト用） ---
        if options['demo']:
            self.create_demo_alert()
            return

        # --- B. 本番モード（気象庁API） ---
        self.fetch_real_data()

    def create_demo_alert(self):
        """プレゼン・テスト用に、強制的に警報データを作る"""
        title = "【訓練】大雨特別警報"
        content = (
            "これはテストデータです。\n"
            "これまでに経験したことのないような大雨となっています。\n"
            "命の危険が差し迫っています。直ちに身の安全を確保してください。"
        )

        # 重複チェック（同じ内容が連投されないように）
        if not OfficialAlert.objects.filter(title=title, is_active=True).exists():
            OfficialAlert.objects.create(
                title=title,
                content=content,
                severity='critical',  # モデルの定義に合わせて (high/criticalなど)
                publisher='気象庁(デモ)',
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS('デモ用の警報データを作成しました。ブラウザで確認してください。'))
        else:
            self.stdout.write(self.style.WARNING('デモ用データは既に存在します。'))

    def fetch_real_data(self):
        # 1. 登録されている全エリアを取得
        target_areas = JmaArea.objects.all()

        if not target_areas.exists():
            self.stderr.write("JmaAreaが登録されていません。load_jma_areasを実行してください。")
            return

        self.stdout.write(f"{target_areas.count()} 箇所のエリア情報を取得開始...")

        # 2. エリアごとにループして取得
        for area in target_areas:
            url = f"https://www.jma.go.jp/bosai/warning/data/warning/{area.code}.json"

            try:
                response = requests.get(url, timeout=5)  # タイムアウトは短めに
                if response.status_code != 200:
                    continue  # エラーなら次のエリアへ

                data = response.json()

                # --- データ解析と保存 ---
                if 'headline' in data and data['headline']:
                    headline_text = data['headline'][0].get('text', '')
                    if not headline_text:
                        continue

                    # 最新チェック (同じエリア、同じ内容なら保存しない)
                    if not OfficialAlert.objects.filter(
                            area=area,  # ★ エリアで絞り込み
                            content=headline_text,
                            published_at__date=timezone.now().date()
                    ).exists():
                        OfficialAlert.objects.create(
                            title=f"気象警報 ({area.name})",  # タイトルに地域名を入れると親切
                            content=headline_text,
                            severity='high',  # 簡易判定
                            publisher='気象庁',
                            is_active=True,
                            area=area  # ★ エリアを紐付け
                        )
                        self.stdout.write(self.style.SUCCESS(f"[{area.name}] 新しい警報を保存"))

            except Exception as e:
                self.stderr.write(f"[{area.name}] エラー: {e}")

    def get_nearest_area(self, lat, lon):
        """現在地から最も近いJmaAreaを返す"""
        min_distance = float('inf')
        nearest = None

        all_areas = JmaArea.objects.all()
        for area in all_areas:
            # 簡易的な距離計算（三平方の定理）
            # ※厳密な距離計算ではありませんが、一番近い場所を探すだけならこれで十分です
            d_lat = area.latitude - lat
            d_lon = area.longitude - lon
            distance = math.sqrt(d_lat ** 2 + d_lon ** 2)

            if distance < min_distance:
                min_distance = distance
                nearest = area

        return nearest
