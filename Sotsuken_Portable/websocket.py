import asyncio
import websockets
import json
from collections import defaultdict

# --- データ構造を変更 ---
# { group_id: {websocket_obj, websocket_obj, ...} }
rooms = defaultdict(set)
# { group_id: [message, message, ...] }
chat_histories = defaultdict(list)


async def handle_client(websocket):
    current_group_id = None
    username = None

    try:
        # 1. 最初のメッセージで group_id と username を受け取る
        join_data_json = await websocket.recv()
        join_data = json.loads(join_data_json)

        current_group_id = join_data.get('group_id')
        username = join_data.get('username')

        if not current_group_id or not username:
            print("グループIDまたはユーザー名が不正なため接続を拒否しました。")
            await websocket.close()
            return

        print(f"ユーザー '{username}' がグループ '{current_group_id}' に参加しようとしています。")

        # 2. クライアントを適切なルームに追加
        rooms[current_group_id].add(websocket)

        # 3. 参加メッセージをそのルームの全員に送信
        await broadcast(current_group_id, {"sender": "【サーバー】", "message": f"{username} が参加しました。"})

        # 4. 過去のチャット履歴を新規参加者に送信
        history = chat_histories[current_group_id]
        if history:
            # 履歴を一度に送信する方が効率的
            await websocket.send(json.dumps({"type": "history", "messages": history}))

        print(f"'{username}' がグループ '{current_group_id}' に参加完了。")

        # 5. メッセージ受信ループ
        async for message_json in websocket:
            message_data = json.loads(message_json)
            message_content = message_data.get('message')

            print(f"グループ '{current_group_id}' の '{username}' からのメッセージ: {message_content}")

            # 6. メッセージをそのルームの全員にブロードキャスト
            await broadcast(current_group_id, {"sender": username, "message": message_content})

    except websockets.exceptions.ConnectionClosed:
        print(f"接続が切れました。")
    finally:
        # 7. 接続が切れたクライアントをルームから削除
        if current_group_id and websocket in rooms[current_group_id]:
            rooms[current_group_id].remove(websocket)
            # もしルームが空になったら、メモリから削除（任意）
            if not rooms[current_group_id]:
                del rooms[current_group_id]
                del chat_histories[current_group_id]  # 履歴も削除

            # 退出メッセージをブロードキャスト
            await broadcast(current_group_id, {"sender": "【サーバー】", "message": f"{username} が退出しました。"})
        print(f"'{username}' の接続処理を終了しました。")


async def broadcast(group_id, message):
    # 該当グループの履歴にメッセージを追加
    if message['sender'] != "【サーバー】":
        history = chat_histories[group_id]
        history.append(message)
        # 履歴が長くなりすぎないように制御
        if len(history) > 100:
            chat_histories[group_id] = history[-100:]

    # 該当グループの全クライアントにメッセージを送信
    if group_id in rooms and rooms[group_id]:
        message_json = json.dumps({"type": "message", "data": message})
        # asyncio.gatherを使用して効率的に並行送信
        await asyncio.gather(
            *[client.send(message_json) for client in rooms[group_id]]
        )


async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        print("WebSocketサーバーが localhost:8765 で起動しました...")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())