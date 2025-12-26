"""
Activity Tracker V2 - PyWebView Edition

PyWebView + FastAPI + pystray 기반 앱
기존 PyQt6 UI를 웹 UI로 대체
"""
import sys
import os
import threading
import time
import asyncio
import webbrowser
import socket
import signal
import ctypes
from datetime import datetime
from pathlib import Path

try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    print("[Warning] pywebview not available, using browser fallback")

import pystray
from PIL import Image
import uvicorn

from backend.api_server import app as fastapi_app, ws_manager, set_runtime_engines, set_exit_callback
from backend.database import DatabaseManager
from backend.monitor_engine_thread import MonitorEngineThread
from backend.rule_engine import RuleEngine
from backend.config import AppConfig
from backend.log_generator import ActivityLogGenerator


class ActivityTrackerApp:
    """PyWebView 기반 Activity Tracker 앱"""

    def __init__(self):
        self.window = None
        self.tray_icon = None
        self.api_server_thread = None
        self.monitor_engine = None
        self.db_manager = None
        self.rule_engine = None
        self.log_generator = None
        self.running = True

        # 포트 설정
        self.api_port = 8000
        self.webui_url = self._get_webui_url()

    def _get_webui_url(self) -> str:
        """웹 UI URL 결정"""
        # 개발 모드: Vite dev server
        if os.environ.get('DEV_MODE') == '1':
            return 'http://localhost:5173'

        # 프로덕션: FastAPI가 dist를 서빙
        return f'http://127.0.0.1:{self.api_port}'

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

        # 룰 엔진 초기화
        self.rule_engine = RuleEngine(self.db_manager)

        # 모니터링 엔진 초기화 (threading 기반)
        self.monitor_engine = MonitorEngineThread(
            db_manager=self.db_manager,
            rule_engine=self.rule_engine,
            on_activity_detected=self._on_activity_detected,
            on_toast_requested=self._on_toast_requested
        )

        # 모니터링 시작
        self.monitor_engine.start()
        print("[Monitor Engine] Started (threading-based)")

        # API 서버에 런타임 엔진 인스턴스 전달 (룰/집중 설정 변경 시 reload 용)
        set_runtime_engines(self.rule_engine, self.monitor_engine.focus_blocker)

        # 로그 생성기 초기화 및 실행
        self._start_log_generator()

    def _start_log_generator(self):
        """활동 로그 생성기 시작 (백그라운드)"""
        def generate_logs():
            try:
                from datetime import date
                self.log_generator = ActivityLogGenerator(self.db_manager)
                # 오늘 일간 로그 + 최근 로그 생성
                self.log_generator.generate_daily_log(date.today())
                self.log_generator.generate_recent_log()
                print("[Log Generator] Logs generated successfully")
            except Exception as e:
                print(f"[Log Generator] Error: {e}")

        threading.Thread(target=generate_logs, daemon=True).start()

    def _on_activity_detected(self, activity_info: dict):
        """활동 감지 시 WebSocket으로 브로드캐스트"""
        try:
            # asyncio 이벤트 루프에서 실행
            asyncio.run(ws_manager.broadcast({
                "type": "activity_update",
                "data": activity_info
            }))
        except Exception as e:
            print(f"[WebSocket] Broadcast error: {e}")

    def _on_toast_requested(self, tag_id: int, message: str, cooldown: int):
        """토스트 알림 요청 처리"""
        try:
            # NotificationManager는 MonitorEngine 내부에 있음
            self.monitor_engine.notification_manager.show(
                tag_id=tag_id,
                title="Activity Tracker",
                message=message,
                cooldown=cooldown
            )
        except Exception as e:
            print(f"[Notification] Error: {e}")

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

    def _get_active_focus_blocks(self) -> list:
        """현재 활성화된 집중 모드 차단 목록 조회"""
        if not self.db_manager:
            return []

        try:
            tags = self.db_manager.get_all_tags()
            active_blocks = []

            now = datetime.now()
            current_minutes = now.hour * 60 + now.minute

            for tag in tags:
                if not tag.get('block_enabled'):
                    continue
                if tag['name'] in ('자리비움', '미분류'):
                    continue

                start_time = tag.get('block_start_time')
                end_time = tag.get('block_end_time')

                if not start_time or not end_time:
                    continue

                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                # 시간 범위 체크
                if start_minutes <= end_minutes:
                    is_active = start_minutes <= current_minutes < end_minutes
                else:
                    # 자정 넘는 경우 (22:00 ~ 02:00)
                    is_active = current_minutes >= start_minutes or current_minutes < end_minutes

                if is_active:
                    active_blocks.append(tag['name'])

            return active_blocks
        except Exception as e:
            print(f"[App] Error checking focus blocks: {e}")
            return []

    def _confirm_and_quit_from_tray(self, active_blocks: list):
        """트레이에서 종료 시 별도 스레드에서 확인 후 종료"""
        MB_YESNO = 0x04
        MB_ICONWARNING = 0x30
        MB_SYSTEMMODAL = 0x1000
        MB_SETFOREGROUND = 0x10000
        IDYES = 6

        message = (
            f"현재 집중 모드가 활성화되어 있습니다!\n\n"
            f"차단 중인 태그: {', '.join(active_blocks)}\n\n"
            f"앱을 종료하면 집중 모드가 해제됩니다.\n"
            f"정말로 종료하시겠습니까?"
        )

        result = ctypes.windll.user32.MessageBoxW(
            0, message, "Activity Tracker 종료",
            MB_YESNO | MB_ICONWARNING | MB_SYSTEMMODAL | MB_SETFOREGROUND
        )

        if result == IDYES:
            self._do_quit()

    def _do_quit(self):
        """실제 종료 수행"""
        self.running = False

        if self.monitor_engine and self.monitor_engine.is_alive():
            print("[App] Stopping monitor engine...")
            self.monitor_engine.stop(timeout=3.0)

        if self.tray_icon:
            self.tray_icon.stop()

        if self.window:
            self.window.destroy()

        print("[App] Shutting down...")
        os._exit(0)

    def quit_app(self, icon=None, item=None):
        """앱 종료"""
        # 트레이에서 호출된 경우 집중 모드 체크
        if icon is not None:
            active_blocks = self._get_active_focus_blocks()
            if active_blocks:
                # 별도 스레드에서 확인창 띄우기 (트레이 메뉴가 먼저 닫히도록)
                threading.Thread(
                    target=self._confirm_and_quit_from_tray,
                    args=(active_blocks,),
                    daemon=True
                ).start()
                return  # 트레이 콜백 즉시 반환

        self._do_quit()

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

        # 종료 콜백 설정
        set_exit_callback(self.quit_app)

        # 모니터링 엔진 시작
        self.start_monitor_engine()

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
        # EdgeChromium 백엔드 사용 (Windows 10/11 기본 탑재)
        webview.start(debug=os.environ.get('DEV_MODE') == '1', gui='edgechromium')


def is_port_in_use(port: int) -> bool:
    """포트가 사용 중인지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def main():
    """메인 함수"""
    # 중복 실행 방지 (포트 8000 체크)
    if is_port_in_use(8000):
        print("[App] Already running (port 8000 in use). Exiting.")
        sys.exit(0)

    # 개발 모드 설정
    if '--dev' in sys.argv:
        os.environ['DEV_MODE'] = '1'
        print("[Mode] Development mode enabled")

    app = ActivityTrackerApp()

    # Ctrl+C 핸들러
    def signal_handler(signum, frame):
        print("\n[App] Ctrl+C received, shutting down...")
        app.quit_app()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app.run()


if __name__ == "__main__":
    main()
