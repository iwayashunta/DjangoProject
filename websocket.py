import asyncio
import websockets
import json

clients = set()
chat_history = []


async def handle_client(websocket):
    # 接続が確立された
    print("クライアントが接続しました。")

    try:
        # クライアントからIDを受信する
        client_id = await websocket.recv()
        print(f"クライアントID: {client_id}")

        # 参加メッセージを送信
        await broadcast({"client_id": "【server】", "message": f"{client_id} が参加しました。"})

        # 過去のチャット履歴を送信
        for message in chat_history:
            await websocket.send(json.dumps(message))

        # 新しいクライアントのWebSocket接続をclientsセットに追加
        clients.add(websocket)

        while True:
            # クライアントからメッセージを受信する
            message = await websocket.recv()

            try:
                print(f"{client_id}からのメッセージ: {message}")
                await broadcast({"client_id": client_id, "message": message})

            except json.JSONDecodeError:
                # 受信したデータがJSON形式でない場合のエラー処理
                await broadcast({"client_id": client_id, "message": message})
                print(f"{client_id}からのメッセージ: {message}")

    except websockets.exceptions.ConnectionClosedOK:
        # 接続が切断されたら実行される処理
        print(f"クライアントID: {client_id}との接続が切断されました。")
        clients.remove(websocket)
        await broadcast({"client_id": "【server】", "message": f"{client_id}が退出しました。"})


async def broadcast(message):
    chat_history.append(message)

    message_json = json.dumps(message)

    for client in clients:
        await client.send(message_json)

async def main():
    # サーバの起動
    async with websockets.serve(handle_client, "localhost", 8765):
        print("サーバー起動中...")
        # サーバーを実行し続けるために、終了しないFutureをawaitする
        await asyncio.Future()  # サーバーが実行を続ける限りブロックする

# イベントループの開始
if __name__ == "__main__":
    asyncio.run(main())