from django.apps import AppConfig


class SotsukenPortableConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Sotsuken_Portable'

    def ready(self):
        """
        Djangoアプリケーションの準備ができたときに一度だけ呼ばれるメソッド
        """
        # ここでチャンネルレイヤーのセットアップを強制的に行う
        # これにより、同期プロセスでも正しい設定が読み込まれるようになる
        # import django
        # django.setup()

        # 念のため、channel_layersをインポートして初期化をトリガー
        try:
            from channels.layers import channel_layers
            # 実際にアクセスしてインスタンス化を促す
            _ = channel_layers['default']
            print("--- Forcibly initialized Channel Layers in AppConfig ---")
        except Exception as e:
            print(f"--- AppConfig Channel Layer initialization failed: {e} ---")
