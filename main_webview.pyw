"""
Activity Tracker - PyWebView Edition

PyWebView + FastAPI + pystray 기반 앱
기존 PyQt6 UI를 웹 UI로 대체
"""
import sys
import os
import shutil
import sqlite3
import urllib.request
import urllib.error
import threading
import time
import asyncio
import signal
import webbrowser
import socket
import signal
import ctypes
import logging
from datetime import datetime
from pathlib import Path

if getattr(sys, 'frozen', False) or not sys.stdout:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')


class _StreamFilter:
    """Filter noisy pywebview native introspection errors from output."""

    def __init__(self, stream, drop_substrings):
        self._stream = stream
        self._drop_substrings = drop_substrings
        self._buffer = ""

    def write(self, message):
        if not message:
            return 0
        self._buffer += message
        written = 0
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line += "\n"
            if any(sub in line for sub in self._drop_substrings):
                written += len(line)
                continue
            self._stream.write(line)
            written += len(line)
        return written

    def flush(self):
        if self._buffer:
            if not any(sub in self._buffer for sub in self._drop_substrings):
                self._stream.write(self._buffer)
            self._buffer = ""
        self._stream.flush()

    def isatty(self):
        return self._stream.isatty()

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", None)


class _LogFilter(logging.Filter):
    """Filter noisy pywebview native introspection errors from logs."""

    def __init__(self, drop_substrings):
        super().__init__()
        self._drop_substrings = drop_substrings

    def filter(self, record):
        message = record.getMessage()
        return not any(sub in message for sub in self._drop_substrings)

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

# Silence pywebview error spam (native object introspection).
logging.getLogger("pywebview").disabled = True
logging.getLogger("webview").disabled = True
_pywebview_noise = [
    "[pywebview] Error while processing app.window.native.",
    "maximum recursion depth exceeded while calling a Python object",
    "AccessibilityObject.Bounds",
    "__abstractmethods__",
]
sys.stdout = _StreamFilter(sys.stdout, _pywebview_noise)
sys.stderr = _StreamFilter(sys.stderr, _pywebview_noise)
from backend.import_export import ImportExportManager


class ApiServerThread(threading.Thread):
    """FastAPI 서버를 스레드로 실행 (메인 프로세스 공유)"""

    def __init__(self, app, port: int):
        super().__init__(daemon=True)
        self._app = app
        self._port = port
        self._server = None

    def run(self):
        config = uvicorn.Config(
            self._app,
            host="127.0.0.1",
            port=self._port,
            log_level="warning",
            access_log=False
        )
        if hasattr(config, "handle_signals"):
            config.handle_signals = False
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self):
        if self._server:
            self._server.should_exit = True


class PyWebViewApi:
    """PyWebView JavaScript API - 네이티브 다이얼로그 제공"""

    def __init__(self, app: 'ActivityTrackerApp'):
        self.app = app

    def save_backup(self) -> dict:
        """DB 백업 - 저장 다이얼로그로 경로 선택"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"activity_tracker_backup_{timestamp}.db"

            result = self.app.window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_name,
                file_types=('Database Files (*.db)', 'All files (*.*)')
            )

            if not result:
                return {"success": False, "message": "취소됨"}

            save_path = result if isinstance(result, str) else result[0]

            ie_manager = ImportExportManager(self.app.db_manager)
            success = ie_manager.export_database(save_path)

            if success:
                return {"success": True, "message": f"백업 완료: {save_path}"}
            else:
                return {"success": False, "message": "백업 실패"}

        except Exception as e:
            return {"success": False, "message": f"오류: {str(e)}"}

    def save_rules_export(self) -> dict:
        """룰 내보내기 - 저장 다이얼로그로 경로 선택"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"rules_export_{timestamp}.json"

            result = self.app.window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_name,
                file_types=('JSON Files (*.json)', 'All files (*.*)')
            )

            if not result:
                return {"success": False, "message": "취소됨"}

            save_path = result if isinstance(result, str) else result[0]

            ie_manager = ImportExportManager(self.app.db_manager)
            success = ie_manager.export_rules(save_path)

            if success:
                tags = self.app.db_manager.get_all_tags()
                rules = self.app.db_manager.get_all_rules()
                return {
                    "success": True,
                    "message": f"내보내기 완료: {save_path}",
                    "stats": {"tags": len(tags), "rules": len(rules)}
                }
            else:
                return {"success": False, "message": "내보내기 실패"}

        except Exception as e:
            return {"success": False, "message": f"오류: {str(e)}"}

    def exit_app(self) -> dict:
        """앱 종료"""
        print("[PyWebViewApi] exit_app called")
        try:
            self.app.quit_app()
            return {"success": True}
        except Exception as e:
            print(f"[PyWebViewApi] exit_app error: {e}")
            return {"success": False, "message": str(e)}


class ActivityTrackerApp:
    """PyWebView 기반 Activity Tracker 앱"""

    def __init__(self):
        self.window = None
        self.tray_icon = None
        self.api_server_thread = None
        self._api_pid_path = AppConfig.get_api_pid_path()
        self.monitor_engine = None
        self.db_manager = None
        self.rule_engine = None
        self.log_generator = None
        self.running = True

        # 포트 설정
        self.api_port = 8000
        self.webui_url = self._get_webui_url()
        self._webview_profile_dir = AppConfig.get_app_dir() / "webview_profile"

    def _get_webui_url(self) -> str:
        """웹 UI URL 결정"""
        # 개발 모드: Vite dev server
        if os.environ.get('DEV_MODE') == '1':
            return 'http://localhost:5173'

        # 프로덕션: FastAPI가 dist를 서빙
        return f'http://127.0.0.1:{self.api_port}'

    def start_api_server(self):
        """FastAPI 서버를 스레드로 실행"""
        logging.info("[API Server] Starting...")
        self.api_server_thread = ApiServerThread(fastapi_app, self.api_port)
        self.api_server_thread.start()
        print(f"[API Server] Started on port {self.api_port}")

    def start_monitor_engine(self):
        """모니터링 엔진 시작"""
        self.db_manager = DatabaseManager()
        self.db_manager.cleanup_unfinished_activities()

        # 룰 엔진 초기화
        self.rule_engine = RuleEngine(self.db_manager)

        # 로그 생성기 초기화 (monitor_engine보다 먼저)
        self.log_generator = ActivityLogGenerator(self.db_manager)

        # 모니터링 엔진 초기화 (threading 기반)
        self.monitor_engine = MonitorEngineThread(
            db_manager=self.db_manager,
            rule_engine=self.rule_engine,
            on_activity_detected=self._on_activity_detected,
            on_toast_requested=self._on_toast_requested,
            log_generator=self.log_generator
        )

        # 모니터링 시작
        self.monitor_engine.start()
        print("[Monitor Engine] Started (threading-based)")

        # API 서버에 런타임 엔진 인스턴스 전달 (룰/집중 설정 변경 시 reload 용)
        set_runtime_engines(
            self.rule_engine,
            self.monitor_engine.focus_blocker,
            self.log_generator,
            self.monitor_engine,
            self.quit_app  # exit callback도 함께 전달
        )

        # 로그 생성 (백그라운드)
        self._start_log_generator()
        # 초기화에서 열었던 메인 스레드 DB 연결을 닫아 잠금 최소화
        self.db_manager.close()

    def _start_log_generator(self):
        """활동 로그 생성 (백그라운드)"""
        def generate_logs():
            try:
                self.log_generator.update_all_logs()
                print("[Log Generator] Logs generated successfully")
            except Exception as e:
                print(f"[Log Generator] Error: {e}")

        threading.Thread(target=generate_logs, daemon=True).start()

    def _wait_for_api_ready(self, timeout: float = 10.0) -> bool:
        """API 서버 준비 대기"""
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{self.api_port}/api/health"
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        logging.info("[API Server] Health check OK")
                        return True
            except Exception as e:
                last_error = e
                time.sleep(0.5)
        if last_error:
            logging.error("[API Server] Health check failed: %s", last_error)
        return False

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
            pystray.MenuItem("열기", self.show_window, default=True),
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

        if self.api_server_thread and self.api_server_thread.is_alive():
            self.api_server_thread.stop()
            self.api_server_thread.join(timeout=3.0)
        if self._api_pid_path.exists():
            try:
                self._api_pid_path.unlink()
            except Exception:
                pass

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
        print("[App] Starting Activity Tracker (PyWebView Edition)")

        # Reduce noisy pywebview native introspection logs.
        logging.getLogger("pywebview").setLevel(logging.ERROR)
        logging.getLogger("webview").setLevel(logging.ERROR)

        # API 서버 시작
        self.start_api_server()
        time.sleep(1)  # 서버 시작 대기
        if not self._wait_for_api_ready(timeout=12.0):
            logging.error("[API Server] Health check failed")
            if self.api_server_thread and self.api_server_thread.is_alive():
                self.api_server_thread.stop()
                self.api_server_thread.join(timeout=3.0)
            ctypes.windll.user32.MessageBoxW(
                0,
                "API server did not respond. Please restart the app.",
                "Activity Tracker",
                0x10 | 0x1000
            )
            return

        # 종료 콜백 설정
        set_exit_callback(self.quit_app)

        # 모니터링 엔진 시작
        self.start_monitor_engine()

        # 트레이 아이콘 시작 (별도 스레드)
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()

        # JS API 인스턴스 생성
        self.js_api = PyWebViewApi(self)

        # PyWebView 창 생성
        self.window = webview.create_window(
            title="Activity Tracker",
            url=self.webui_url,
            width=1200,
            height=800,
            min_size=(800, 600),
            resizable=True,
            confirm_close=True,
            js_api=self.js_api
        )

        # 창 닫기 이벤트
        self.window.events.closing += self.on_closing

        # WebView 시작 (메인 스레드에서 실행)
        # EdgeChromium 백엔드 사용 (Windows 10/11 기본 탑재)
        webview.start(
            debug=os.environ.get('DEV_MODE') == '1',
            gui='edgechromium',
            storage_path=str(self._webview_profile_dir)
        )


def is_port_in_use(port: int) -> bool:
    """포트가 사용 중인지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def ensure_single_instance() -> bool:
    """중복 실행 방지 (Windows mutex)"""
    mutex_name = "Global\\ActivityTracker_SingleInstance"
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if not handle:
        return True  # 실패 시 앱 실행 허용

    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False

    return True


def activate_existing_window() -> bool:
    """이미 실행 중인 창을 활성화"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Activity Tracker")
        if not hwnd:
            return False

        SW_SHOW = 5
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_SHOW)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def main():
    """메인 함수"""
    def terminate_pid(pid: int) -> bool:
        if os.name != 'nt':
            try:
                os.kill(pid, signal.SIGTERM)
                return True
            except Exception:
                return False
        try:
            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False

    # 이전 API 프로세스가 남아있으면 정리
    api_pid_path = AppConfig.get_api_pid_path()
    if api_pid_path.exists():
        try:
            pid = int(api_pid_path.read_text(encoding="utf-8").strip())
            if terminate_pid(pid):
                time.sleep(0.5)
            api_pid_path.unlink()
        except Exception:
            pass

    # 중복 실행 방지 (포트 열기 전 mutex 체크)
    if not ensure_single_instance():
        activate_existing_window()
        print("[App] Already running (mutex exists). Exiting.")
        sys.exit(0)

    # 중복 실행 방지 (포트 8000 체크)
    if is_port_in_use(8000):
        print("[App] Already running (port 8000 in use). Exiting.")
        sys.exit(0)

    # 복원 예약이 있으면 앱 시작 전에 적용
    pending_meta_path = AppConfig.get_restore_pending_path()
    pending_db_path = AppConfig.get_restore_pending_db_path()
    if pending_meta_path.exists() and pending_db_path.exists():
        try:
            conn = sqlite3.connect(str(pending_db_path))
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            conn.close()
            if result != "ok":
                print(f"[Restore] Pending DB integrity failed: {result}")
            else:
                db_path = AppConfig.get_db_path()
                wal_path = db_path.with_suffix(".db-wal")
                shm_path = db_path.with_suffix(".db-shm")
                if wal_path.exists():
                    wal_path.unlink()
                if shm_path.exists():
                    shm_path.unlink()
                shutil.copy2(pending_db_path, db_path)
                pending_db_path.unlink()
                pending_meta_path.unlink()
                print("[Restore] Pending DB applied successfully")
        except Exception as e:
            print(f"[Restore] Pending DB apply failed: {e}")

    # 개발 모드 설정
    if '--dev' in sys.argv:
        os.environ['DEV_MODE'] = '1'
        print("[Mode] Development mode enabled")

    from logging.handlers import RotatingFileHandler
    log_path = AppConfig.get_log_path()
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    logging.getLogger("pywebview").setLevel(logging.CRITICAL)
    logging.getLogger("webview").setLevel(logging.CRITICAL)
    log_filter = _LogFilter(_pywebview_noise)
    root_logger.addFilter(log_filter)
    for handler in root_logger.handlers:
        handler.addFilter(log_filter)
    logging.getLogger("pywebview").addFilter(log_filter)
    logging.getLogger("webview").addFilter(log_filter)

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
