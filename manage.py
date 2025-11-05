#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sotsuken_Portable_Project.settings')

    try:
        from django.core.management.commands.runserver import Command as runserver
        from daphne.server import Server
        from Sotsuken_Portable_Project.asgi import application  # あなたのasgi.pyをインポート

        # runserverのデフォルトポートを取得
        DEFAULT_PORT = runserver.default_port

        if 'runserver' in sys.argv:
            # --- ここから修正 ---

            # デフォルト値を設定
            host = '127.0.0.1'
            port = runserver.default_port

            # ポート番号やIPアドレスが指定されているかチェック
            if len(sys.argv) > 2:
                addrport = sys.argv[2]
                if ':' in addrport:
                    # '127.0.0.1:8001' のように指定された場合
                    host, port_str = addrport.split(':')
                    port = int(port_str)
                else:
                    # '8001' のようにポート番号だけ指定された場合
                    try:
                        port = int(addrport)
                    except ValueError:
                        # ポート番号ではない引数の場合は、通常のrunserverに任せる
                        pass
            print(f"Starting Daphne ASGI server at http://{host}:{port}/")

            # Daphneサーバーを直接起動する
            Server(
                application=application,
                endpoints=[f"tcp:port={port}:interface={host}"],
            ).run()
            # Daphneが起動したら、ここで処理を終了
            return
    except (ImportError, IndexError):
        # Daphneがない場合や、引数が不足している場合は通常のrunserverにフォールバック
        pass

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
