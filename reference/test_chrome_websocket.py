"""
Chrome Extension에서 URL을 받는 WebSocket 서버 테스트
"""

import asyncio
import websockets
import json
from datetime import datetime

connected_clients = set()

async def handle_client(websocket, path):
    """Chrome Extension 연결 처리"""
    connected_clients.add(websocket)
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ Chrome Extension 연결됨!")
    print(f"   연결된 클라이언트 수: {len(connected_clients)}")

    try:
        async for message in websocket:
            data = json.loads(message)

            if data.get('type') == 'url_change':
                profile = data.get('profileName', 'Unknown')
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🌐 URL 변경 감지!")
                print(f"   👤 프로필: {profile}")
                print(f"   🔗 URL: {data.get('url')}")
                print(f"   📄 제목: {data.get('title')}")
                print(f"   🆔 탭 ID: {data.get('tabId')}")

    except websockets.exceptions.ConnectionClosed:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ 연결 종료됨")
    finally:
        connected_clients.remove(websocket)
        print(f"   남은 클라이언트: {len(connected_clients)}")

async def main():
    print("=" * 70)
    print("🚀 Chrome URL WebSocket 서버 시작")
    print("=" * 70)
    print()
    print("📌 포트: 8766")
    print("📌 Chrome Extension을 설치하고 테스트하세요.")
    print()
    print("종료: Ctrl+C")
    print("=" * 70)

    async with websockets.serve(handle_client, "localhost", 8766):
        await asyncio.Future()  # 무한 대기

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n서버 종료!")
