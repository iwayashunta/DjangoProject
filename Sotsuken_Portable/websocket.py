import asyncio
import websockets
import json

# 接続中のクライアントを管理する辞書 {websocket_obj: username}
clients = {}
# チャット履歴を保持するリスト
chat_history = []


async def handle_client(websocket):
    print("クライアントが接続しました。")
    try:
        # 最初のメッセージはユーザー情報（JSON）として受け取る
        join_data = await websocket.recv()
        join_data = json.loads(join_data)

        username = join_data.get('username')
        if not username:
            print("ユーザー名が不正なため接続を拒否しました。")
            return

        print(f"ユーザー '{username}' が参加しました。")
        clients[websocket] = username

        # 参加メッセージを全員に送信
        await broadcast({"sender": "【サーバー】", "message": f"{username} が参加しました。"})

        # 過去のチャット履歴を新規参加者に送信
        for message in chat_history:
            await websocket.send(json.dumps(message))

        # メッセージ受信ループ
        async for message_json in websocket:
            message_data = json.loads(message_json)
            message_content = message_data.get('message')

            print(f"'{username}'からのメッセージ: {message_content}")

            # 全員にメッセージをブロードキャスト
            await broadcast({"sender": username, "message": message_content})

    except websockets.exceptions.ConnectionClosed:
        print(f"'{clients.get(websocket, '不明なユーザー')}' との接続が切れました。")
    finally:
        # 接続が切れたクライアントをclients辞書から削除
        disconnected_user = clients.pop(websocket, None)
        if disconnected_user:
            await broadcast({"sender": "【サーバー】", "message": f"{disconnected_user} が退出しました。"})


async def broadcast(message):
    # チャット履歴にメッセージを追加（サーバーメッセージは除く）
    if message['sender'] != "【サーバー】":
        chat_history.append(message)
        # 履歴が長くなりすぎないように制御（例: 最新100件）
        if len(chat_history) > 100:
            chat_history.pop(0)

    # 接続中の全クライアントにメッセージを送信
    if clients:
        message_json = json.dumps(message)
        # asyncio.gather を使って、複数の送信処理を並行して実行する
        await asyncio.gather(
            *[client.send(message_json) for client in clients]
        )


async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        print("WebSocketサーバーが localhost:8765 で起動しました...")
        await asyncio.Future()  # サーバーを永続的に実行


if __name__ == "__main__":
    asyncio.run(main())