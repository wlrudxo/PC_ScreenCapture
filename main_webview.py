"""
Activity Tracker V2 - PyWebView Edition

PyWebView + FastAPI + pystray 기반 앱
기존 PyQt6 UI를 웹 UI로 대체
"""
import sys
import os
import threading
import time
from pathlib import Path

import webview
import pystray
from PIL import Image
import uvicorn

from backend.api_server import app as fastapi_app
from backend.database import DatabaseManager
from backend.monitor_engine import MonitorEngine
from backend.config import AppConfig


class ActivityTrackerApp:
    """PyWebView 기반 Activity Tracker 앱"""

    def __init__(self):
        self.window = None
        self.tray_icon = None
        self.api_server_thread = None
        self.monitor_engine = None
        self.db_manager = None
        self.running = True

        # 포트 설정
        self.api_port = 8000
        self.webui_url = self._get_webui_url()

    def _get_webui_url(self) -> str:
        """웹 UI URL 결정"""
        # 개발 모드: Vite dev server
        if os.environ.get('DEV_MODE') == '1':
            return 'http://localhost:5173'

        # 프로덕션: 빌드된 dist 폴더
        dist_path = Path(__file__).parent / 'webui' / 'dist' / 'index.html'
        if dist_path.exists():
            return str(dist_path)

        # 폴백: 개발 서버
        return 'http://localhost:5173'

    def start_api_server(self):
        """FastAPI 서버를 백그라운드 스레드에서 실행"""
        config = uvicorn.Config(
            fastapi_app,
            host="127.0.0.1",
            port=self.api_port,
            log_level="warning"
        )
        server = uvicorn.Server(config)

        def run():
            # 이벤트 루프 새로 생성 (스레드에서 필요)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())

        self.api_server_thread = threading.Thread(target=run, daemon=True)
        self.api_server_thread.start()
        print(f"[API Server] Started on port {self.api_port}")

    def start_monitor_engine(self):
        """모니터링 엔진 시작"""
        self.db_manager = DatabaseManager()
        self.db_manager.cleanup_unfinished_activities()

        # MonitorEngine은 QThread 기반이라 별도 처리 필요
        # 여기서는 간단히 import만 해둠 (실제 구동은 PyQt 없이 별도 구현 필요)
        print("[Monitor Engine] Ready (requires separate implementation for non-Qt)")

    def create_tray_icon(self):
        """시스템 트레이 아이콘 생성"""
        # 아이콘 이미지 생성 (간단한 녹색 원)
        icon_path = Path(__file__).parent / 'resources' / 'icon.png'
        if icon_path.exists():
            image = Image.open(icon_path)
        else:
            # 기본 아이콘 생성
            image = Image.new('RGB', (64, 64), color='#4CAF50')

        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_window),
            pystray.MenuItem("종료", self.quit_app)
        )

        self.tray_icon = pystray.Icon(
            "ActivityTracker",
            image,
            "Activity Tracker",
            menu
        )

    def show_window(self, icon=None, item=None):
        """윈도우 표시"""
        if self.window:
            self.window.show()
            self.window.restore()

    def hide_window(self):
        """윈도우 숨기기 (트레이로)"""
        if self.window:
            self.window.hide()

    def quit_app(self, icon=None, item=None):
        """앱 종료"""
        self.running = False

        if self.tray_icon:
            self.tray_icon.stop()

        if self.window:
            self.window.destroy()

        print("[App] Shutting down...")
        os._exit(0)

    def on_closing(self):
        """창 닫기 이벤트 핸들러"""
        # 창을 닫으면 트레이로 최소화
        self.hide_window()
        return False  # 창 닫기 방지

    def run_tray(self):
        """트레이 아이콘 실행 (별도 스레드)"""
        self.create_tray_icon()
        self.tray_icon.run()

    def run(self):
        """앱 실행"""
        print("[App] Starting Activity Tracker V2 (PyWebView Edition)")

        # API 서버 시작
        self.start_api_server()
        time.sleep(1)  # 서버 시작 대기

        # 트레이 아이콘 시작 (별도 스레드)
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()

        # PyWebView 창 생성
        self.window = webview.create_window(
            title="Activity Tracker",
            url=self.webui_url,
            width=1200,
            height=800,
            min_size=(800, 600),
            resizable=True,
            confirm_close=True
        )

        # 창 닫기 이벤트
        self.window.events.closing += self.on_closing

        # WebView 시작 (메인 스레드에서 실행)
        webview.start(debug=os.environ.get('DEV_MODE') == '1')


def main():
    """메인 함수"""
    # 개발 모드 설정
    if '--dev' in sys.argv:
        os.environ['DEV_MODE'] = '1'
        print("[Mode] Development mode enabled")

    app = ActivityTrackerApp()
    app.run()


if __name__ == "__main__":
    main()
