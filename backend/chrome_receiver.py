"""
Chrome Extension으로부터 URL 수신 (WebSocket 서버)
"""
import threading
import asyncio
import websockets
import json
from typing import Dict, Any


class ChromeURLReceiver:
    """
    Chrome Extension으로부터 URL 수신 (WebSocket 서버)

    중요: 별도 스레드에서 asyncio 이벤트 루프 실행
    """

    def __init__(self, port: int = 8766):
        """
        WebSocket 서버 초기화

        Args:
            port: WebSocket 서버 포트 (기본: 8766)
        """
        self.latest_data: Dict[str, Any] = {}
        self.port = port
        self.lock = threading.Lock()  # 스레드 안전성 확보
        self.server = None
        self.loop = None

        # WebSocket 서버를 위한 별도 데몬 스레드 시작
        server_thread = threading.Thread(target=self._start_server, daemon=True)
        server_thread.start()

    def _start_server(self):
        """별도 스레드에서 asyncio 이벤트 루프 실행"""
        # 새 이벤트 루프 생성
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # WebSocket 서버 시작 (websockets 13+ 호환)
        async def serve():
            self.server = await websockets.serve(self._handler, "localhost", self.port)
            print(f"[ChromeURLReceiver] WebSocket 서버 시작: ws://localhost:{self.port}")
            await self.server.wait_closed()

        try:
            self.loop.run_until_complete(serve())
        except Exception as e:
            print(f"[ChromeURLReceiver] 서버 종료: {e}")

    async def _handler(self, websocket):
        """
        Chrome Extension 연결 처리

        Args:
            websocket: WebSocket 연결 객체
        """
        print(f"[ChromeURLReceiver] Chrome Extension 연결됨")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get('type') == 'url_change':
                        # 스레드 안전하게 최신 데이터 저장
                        with self.lock:
                            self.latest_data = {
                                'url': data.get('url'),
                                'profile': data.get('profileName'),
                                'title': data.get('title'),
                                'tab_id': data.get('tabId'),
                                'timestamp': data.get('timestamp'),
                            }
                        # 로그 출력
                        profile = data.get('profileName', 'Unknown')
                        url = data.get('url', '')
                        print(f"[ChromeURLReceiver] 📥 [{profile}] URL 수신: {url}")
                except json.JSONDecodeError:
                    pass  # 잘못된 JSON 무시

        except websockets.exceptions.ConnectionClosed:
            print(f"[ChromeURLReceiver] Chrome Extension 연결 종료됨")

    def get_latest_url(self) -> Dict[str, Any]:
        """
        MonitorEngine에서 호출할 스레드 안전한 함수

        Returns:
            dict: {
                'url': str,
                'profile': str,
                'title': str,
                'tab_id': int,
                'timestamp': int
            }
            또는 빈 딕셔너리
        """
        with self.lock:
            return self.latest_data.copy()

    def stop(self):
        """WebSocket 서버 종료"""
        import time
        print("[ChromeURLReceiver] 종료 요청됨")

        if self.loop and self.loop.is_running():
            # 서버 종료
            if self.server:
                self.server.close()

            # 이벤트 루프 종료
            self.loop.call_soon_threadsafe(self.loop.stop)

            # 이벤트 루프가 종료될 때까지 대기 (최대 2초)
            for _ in range(20):
                if not self.loop.is_running():
                    break
                time.sleep(0.1)

        print("[ChromeURLReceiver] WebSocket 서버 종료됨")
