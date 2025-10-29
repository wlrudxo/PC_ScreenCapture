# 활동 추적 시스템 V2 - 아키텍처

## 📋 개요
PC 활동(활성 창, Chrome URL, 화면 잠금 등)을 실시간 추적하여 태그별로 자동 분류하고 통계를 시각화하는 개인용 데스크톱 애플리케이션

**핵심 기능:**
- 2초 간격 실시간 활동 모니터링
- Chrome URL 추적 (WebSocket 기반 확장 프로그램)
- 우선순위 기반 자동 태그 분류
- 대시보드/타임라인 UI
- 시스템 트레이 백그라운드 실행

---

## 🏗️ 전체 구조

```
┌─────────────────────────────────────────────────┐
│              PyQt6 Frontend                      │
│  ┌──────────┬──────────┬──────────┬──────────┐ │
│  │Dashboard │Timeline  │Settings  │  Tray    │ │
│  │   Tab    │   Tab    │   Tab    │  Icon    │ │
│  └──────────┴──────────┴──────────┴──────────┘ │
└─────────────────┬───────────────────────────────┘
                  │ (Qt Signals)
┌─────────────────▼───────────────────────────────┐
│              Backend Core                        │
│  ┌────────────────────────────────────────────┐ │
│  │  MonitorEngine (QThread)                   │ │
│  │  - WindowTracker (ctypes + psutil)         │ │
│  │  - ScreenDetector (lock/idle 감지)         │ │
│  │  - ChromeURLReceiver (WebSocket 서버)      │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  RuleEngine                                │ │
│  │  - 우선순위 기반 룰 매칭                    │ │
│  │  - 와일드카드 패턴 지원                     │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  DatabaseManager (Thread-safe)             │ │
│  │  - SQLite WAL 모드                         │ │
│  │  - threading.local 연결 관리                │ │
│  └────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              SQLite Database                     │
│  - tags (태그 정의)                              │
│  - activities (활동 기록)                        │
│  - rules (분류 룰)                               │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│      Chrome Extension (Manifest V3)              │
│  - WebSocket 클라이언트 (ws://localhost:8766)    │
│  - 활성 탭 URL/프로필 전송                       │
│  - 자동 재연결 로직                               │
└──────────────────────────────────────────────────┘
```

---

## 🗄️ 데이터베이스 스키마

### 1. `tags` - 태그 정의
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**기본 태그:** 업무(#4CAF50), 딴짓(#FF5722), 자리비움(#9E9E9E), 미분류(#607D8B)

**설계 특징:**
- ID 기반 참조로 이름 변경 시에도 기존 활동 기록 유지
- UI에서 자유롭게 CRUD 가능

---

### 2. `activities` - 활동 기록
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,                -- NULL = 진행 중

    process_name TEXT,                 -- "chrome.exe", "__LOCKED__", "__IDLE__"
    window_title TEXT,
    chrome_url TEXT,
    chrome_profile TEXT,

    tag_id INTEGER,                    -- FK: tags(id)
    rule_id INTEGER,                   -- FK: rules(id)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL,
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE SET NULL
);

CREATE INDEX idx_activities_time ON activities(start_time, end_time);
CREATE INDEX idx_activities_tag ON activities(tag_id);
CREATE INDEX idx_activities_process ON activities(process_name);
```

**설계 특징:**
- `start_time ~ end_time` 구간 저장으로 정확한 시간 계산
- 특수 상태는 `process_name`으로 구분: `__LOCKED__`, `__IDLE__`
- Chrome 프로필/URL 별도 저장으로 세밀한 분류 가능

---

### 3. `rules` - 자동 분류 룰
```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority INTEGER DEFAULT 0,        -- 높을수록 우선 적용
    enabled BOOLEAN DEFAULT 1,

    -- 매칭 조건 (OR 관계, 쉼표로 다중 패턴 가능)
    process_pattern TEXT,              -- "chrome.exe,firefox.exe"
    url_pattern TEXT,                  -- "*youtube.com*,*netflix.com*"
    window_title_pattern TEXT,
    chrome_profile TEXT,

    tag_id INTEGER NOT NULL,           -- FK: tags(id)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

**기본 룰:**
- Priority 100: `__LOCKED__` → 자리비움
- Priority 90: `__IDLE__` → 자리비움

**설계 특징:**
- 우선순위 기반 순차 매칭 (높은 것부터)
- 와일드카드 패턴 지원 (`*`, `?`)
- 쉼표로 여러 패턴 한 번에 지정 가능
- 조건 필드 중 하나라도 매치되면 적용 (OR)

---

## 📁 디렉토리 구조

```
PC_ScreenCapture_V2/
├── main.py                      # 애플리케이션 진입점
├── requirements.txt
│
├── backend/                     # 백엔드 모듈
│   ├── config.py                # 경로/설정 관리 (dev vs build 모드)
│   ├── database.py              # SQLite 매니저 (thread-safe)
│   ├── monitor_engine.py        # 모니터링 루프 (QThread)
│   ├── window_tracker.py        # 활성 창 감지 (ctypes)
│   ├── screen_detector.py       # 잠금/idle 감지
│   ├── chrome_receiver.py       # WebSocket 서버 (asyncio)
│   ├── rule_engine.py           # 룰 매칭 엔진
│   └── auto_start.py            # Windows 자동 시작 관리
│
├── ui/                          # PyQt6 UI
│   ├── main_window.py           # 메인 윈도우 + 탭 구조
│   ├── dashboard_tab.py         # 통계 대시보드
│   ├── timeline_tab.py          # 활동 타임라인
│   ├── settings_tab.py          # 설정 (태그/룰 관리)
│   ├── tray_icon.py             # 시스템 트레이
│   └── styles.py                # 다크 테마 QSS
│
├── chrome_extension/            # Chrome 확장 (Manifest V3)
│   ├── manifest.json
│   ├── background.js            # Service Worker
│   ├── popup.html/js            # 설정 팝업
│   └── 설치방법.txt
│
├── reference/                   # 테스트/참고 파일
│   ├── test_active_window.py
│   ├── test_screen_lock.py
│   ├── test_chrome_websocket.py
│   └── demo_pyqt6_ui.py
│
├── activity_tracker.db          # SQLite 데이터베이스 (런타임 생성)
├── activity_tracker.db-shm      # WAL 공유 메모리
└── activity_tracker.db-wal      # WAL 로그
```

---

## 🔧 백엔드 모듈

---

### `backend/config.py` - 설정 및 경로 관리
```python
import os
import sys
from pathlib import Path

class AppConfig:
    """
    애플리케이션 설정 및 경로 관리

    개발 모드 vs 빌드 모드 자동 구분:
    - 개발 중: 프로젝트 폴더에 DB/설정 저장 (디버깅 편함)
    - 빌드 후: AppData에 저장 (Windows 표준)
    """

    @staticmethod
    def is_dev_mode():
        """
        개발 모드 체크
        PyInstaller로 빌드되면 sys.frozen = True
        """
        return not getattr(sys, 'frozen', False)

    @staticmethod
    def get_app_dir():
        """
        애플리케이션 데이터 디렉토리

        개발 모드:
            H:\GitProject\PC_ScreenCapture_V2\

        빌드 모드:
            C:\Users\User\AppData\Roaming\ActivityTracker\
        """
        if AppConfig.is_dev_mode():
            # 개발 중: 프로젝트 폴더
            return Path(__file__).parent.parent
        else:
            # 빌드 후: AppData
            if os.name == 'nt':  # Windows
                app_dir = Path(os.getenv('APPDATA')) / "ActivityTracker"
            else:  # macOS, Linux
                app_dir = Path.home() / ".activitytracker"

            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir

    @staticmethod
    def get_db_path():
        """SQLite DB 파일 경로"""
        return AppConfig.get_app_dir() / "activity_tracker.db"

    @staticmethod
    def get_config_path():
        """설정 파일 경로 (JSON)"""
        return AppConfig.get_app_dir() / "config.json"

    @staticmethod
    def get_log_dir():
        """로그 디렉토리"""
        log_dir = AppConfig.get_app_dir() / "logs"
        log_dir.mkdir(exist_ok=True)
        return log_dir

    @staticmethod
    def get_log_path():
        """로그 파일 경로"""
        return AppConfig.get_log_dir() / "app.log"
```

**핵심 기능:**
- 개발 모드: 프로젝트 폴더에 DB/설정 저장
- 빌드 모드: `%APPDATA%/ActivityTracker`에 저장
- `sys.frozen` 자동 감지로 모드 구분

---

### `backend/database.py` - 데이터베이스 매니저
```python
class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = AppConfig.get_db_path()

        # Thread-safe: threading.local 사용
        self.local = threading.local()
        self.db_path = db_path
        self.init_database()

    def _get_connection(self):
        """스레드별로 독립적인 연결 반환"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self.local.conn.execute("PRAGMA journal_mode=WAL")
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
```

**주요 메서드:**
- **태그**: `get_all_tags()`, `create_tag()`, `update_tag()`, `delete_tag()`
- **활동**: `create_activity()`, `end_activity()`, `get_activities()`
- **룰**: `get_all_rules()`, `create_rule()`, `update_rule()`, `delete_rule()`
- **통계**: `get_stats_by_tag()`, `get_stats_by_process()`, `get_timeline()`

**설계 특징:**
- `threading.local`로 스레드별 연결 분리
- WAL 모드로 동시 읽기 성능 향상
- `sqlite3.Row`로 딕셔너리 스타일 접근

---

### `backend/monitor_engine.py` - 모니터링 엔진
```python
class MonitorEngine(QThread):
    activity_detected = pyqtSignal(dict)

    def __init__(self, db_manager, rule_engine):
        super().__init__()
        self.window_tracker = WindowTracker()
        self.screen_detector = ScreenDetector()
        self.chrome_receiver = ChromeURLReceiver(port=8766)
        self.db_manager = db_manager
        self.rule_engine = rule_engine
        self.running = False
        self.current_activity = None

    def run(self):
        """2초 간격 모니터링 루프"""
        self.running = True
        while self.running:
            activity_info = self.collect_activity_info()

            if self.is_activity_changed(activity_info):
                self.end_current_activity()
                self.start_new_activity(activity_info)

            time.sleep(2)

    def collect_activity_info(self):
        """현재 활동 정보 수집 (우선순위: 잠금 > idle > 일반)"""
        if self.screen_detector.is_locked():
            return {'process_name': '__LOCKED__', ...}

        idle_seconds = self.screen_detector.get_idle_duration()
        if idle_seconds > 300:  # 5분
            return {'process_name': '__IDLE__', ...}

        window_info = self.window_tracker.get_active_window()
        chrome_data = self.chrome_receiver.get_latest_url()

        return {
            'process_name': window_info['process_name'],
            'window_title': window_info['window_title'],
            'chrome_url': chrome_data.get('url'),
            'chrome_profile': chrome_data.get('profile'),
        }

    def start_new_activity(self, info):
        tag_id, rule_id = self.rule_engine.match(info)
        self.current_activity = self.db_manager.create_activity(
            start_time=datetime.now(),
            **info,
            tag_id=tag_id,
            rule_id=rule_id
        )
        self.activity_detected.emit(info)
```

**핵심 로직:**
- QThread로 메인 UI와 독립 실행
- 우선순위: 화면 잠금 > Idle > 일반 활동
- 활동 변경 감지 시 이전 활동 종료 + 새 활동 시작
- Qt Signal로 UI 업데이트 전달

---

### `backend/window_tracker.py` - 활성 창 추적
```python
class WindowTracker:
    def get_active_window(self):
        """Windows API로 활성 창 정보 수집"""
        hwnd = ctypes.windll.user32.GetForegroundWindow()

        # 창 제목
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        window_title = buff.value

        # 프로세스 정보
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            process = psutil.Process(pid.value)
            process_name = process.name()
            process_path = process.exe()

            # Chrome 프로필 추출
            chrome_profile = self._extract_chrome_profile(process.cmdline())
        except:
            process_name = "Unknown"
            process_path = None
            chrome_profile = None

        return {
            'window_title': window_title,
            'process_name': process_name,
            'process_path': process_path,
            'pid': pid.value,
            'chrome_profile': chrome_profile
        }

    def _extract_chrome_profile(self, cmdline):
        """Chrome 프로세스 커맨드라인에서 프로필명 추출"""
        for arg in cmdline:
            if '--profile-directory=' in arg:
                return arg.split('=')[1]
        return None
```

**기술 스택:**
- `ctypes.windll.user32`: Windows API 호출
- `psutil`: 프로세스 정보 수집
- Chrome 프로필은 `--profile-directory` 플래그에서 추출

---

### `backend/screen_detector.py` - 화면 상태 감지
```python
class ScreenDetector:
    def is_locked(self):
        """화면 잠금 상태 체크"""
        hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0)
        return hDesk == 0  # 0이면 잠금 상태

    def get_idle_duration(self):
        """키보드/마우스 입력 없는 시간 (초)"""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', ctypes.c_uint),
                ('dwTime', ctypes.c_uint),
            ]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))

        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
```

**핵심 API:**
- `OpenInputDesktop`: 화면 잠금 감지
- `GetLastInputInfo`: 마지막 입력 시각 조회

---

### `backend/rule_engine.py` - 룰 매칭 엔진
```python
class RuleEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.rules_cache = []
        self.reload_rules()

    def reload_rules(self):
        """DB에서 활성화된 룰 로드 (우선순위 DESC)"""
        self.rules_cache = self.db_manager.get_all_rules(
            enabled_only=True,
            order_by='priority DESC'
        )

    def match(self, activity_info):
        """활동 정보를 룰과 매칭하여 (tag_id, rule_id) 반환"""
        for rule in self.rules_cache:
            if self._is_matched(rule, activity_info):
                return rule['tag_id'], rule['id']

        # 매칭 실패 → 미분류
        unclassified = self.db_manager.get_tag_by_name('미분류')
        return unclassified['id'], None

    def _is_matched(self, rule, info):
        """룰의 조건 중 하나라도 매치되면 True (OR 관계)"""
        # URL 패턴 (쉼표로 다중 패턴 지원)
        if rule['url_pattern'] and info.get('chrome_url'):
            patterns = [p.strip() for p in rule['url_pattern'].split(',')]
            if any(fnmatch.fnmatch(info['chrome_url'], p) for p in patterns):
                return True

        # Chrome 프로필
        if rule['chrome_profile'] and info.get('chrome_profile'):
            if rule['chrome_profile'] == info['chrome_profile']:
                return True

        # 프로세스 패턴
        if rule['process_pattern'] and info.get('process_name'):
            patterns = [p.strip() for p in rule['process_pattern'].split(',')]
            if any(fnmatch.fnmatch(info['process_name'], p) for p in patterns):
                return True

        # 창 제목 패턴
        if rule['window_title_pattern'] and info.get('window_title'):
            patterns = [p.strip() for p in rule['window_title_pattern'].split(',')]
            if any(fnmatch.fnmatch(info['window_title'], p) for p in patterns):
                return True

        return False
```

**매칭 로직:**
- 우선순위 높은 룰부터 순차 검사
- 조건 필드 중 하나라도 매치되면 즉시 반환 (OR)
- 쉼표로 다중 패턴 지원 (`"*youtube.com*,*netflix.com*"`)
- `fnmatch`로 와일드카드 패턴 처리

---

### `backend/chrome_receiver.py` - Chrome WebSocket 서버
```python
class ChromeURLReceiver:
    def __init__(self, port=8766):
        self.latest_data = {}
        self.port = port
        self.lock = threading.Lock()
        self.loop = None
        self.server = None

        # 별도 데몬 스레드에서 WebSocket 서버 실행
        threading.Thread(target=self._start_server, daemon=True).start()

    def _start_server(self):
        """asyncio 이벤트 루프를 별도 스레드에서 실행"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        start_server = websockets.serve(self._handler, "localhost", self.port)
        self.server = self.loop.run_until_complete(start_server)
        print(f"[WebSocket] 서버 시작: ws://localhost:{self.port}")
        self.loop.run_forever()

    async def _handler(self, websocket, path):
        """Chrome Extension 메시지 처리"""
        print("[WebSocket] Chrome Extension 연결됨")
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get('type') == 'url_change':
                    with self.lock:
                        self.latest_data = {
                            'url': data.get('url'),
                            'profile': data.get('profileName'),
                            'title': data.get('title'),
                            'tab_id': data.get('tabId'),
                            'timestamp': data.get('timestamp'),
                        }
        except websockets.ConnectionClosed:
            print("[WebSocket] 연결 종료")

    def get_latest_url(self):
        """스레드 안전하게 최신 URL 반환"""
        with self.lock:
            return self.latest_data.copy()

    def stop(self):
        """서버 종료 (graceful shutdown)"""
        if self.loop and self.server:
            self.loop.call_soon_threadsafe(self.server.close)
```

**설계 특징:**
- 별도 데몬 스레드에서 asyncio 이벤트 루프 실행
- MonitorEngine (QThread)와 완전 독립
- `threading.Lock`으로 데이터 경합 방지
- Chrome 연결 끊김에도 메인 프로그램 영향 없음

---

### `backend/auto_start.py` - 자동 시작 관리
```python
class AutoStartManager:
    @staticmethod
    def add_to_startup():
        """Windows 레지스트리에 자동 시작 등록"""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ActivityTracker", 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(key)

    @staticmethod
    def remove_from_startup():
        """자동 시작 제거"""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, "ActivityTracker")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)

    @staticmethod
    def is_in_startup():
        """현재 자동 시작 상태 확인"""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "ActivityTracker")
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
```

---

## 🖥️ 프론트엔드 (PyQt6)

### `ui/main_window.py` - 메인 윈도우
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activity Tracker")
        self.setGeometry(100, 100, 1200, 800)

        # 백엔드 초기화
        self.db_manager = DatabaseManager()
        self.rule_engine = RuleEngine(self.db_manager)
        self.monitor_engine = MonitorEngine(self.db_manager, self.rule_engine)

        # UI 구성
        self.create_tabs()
        self.tray_icon = SystemTrayIcon(self)

        # 모니터링 시작
        self.monitor_engine.activity_detected.connect(self.on_activity_update)
        self.monitor_engine.start()

    def create_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(DashboardTab(self.db_manager), "📊 대시보드")
        tabs.addTab(TimelineTab(self.db_manager, self.monitor_engine), "⏱️ 타임라인")
        tabs.addTab(SettingsTab(self.db_manager, self.rule_engine), "⚙️ 설정")
        self.setCentralWidget(tabs)

    def closeEvent(self, event):
        """Shift+닫기 = 종료, 일반 닫기 = 트레이로"""
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.quit_app()
        else:
            event.ignore()
            self.hide()

    def quit_app(self):
        """애플리케이션 종료"""
        self.monitor_engine.stop()
        QApplication.quit()
```

---

### `ui/dashboard_tab.py` - 대시보드 탭
**주요 구성 요소:**
1. **날짜 선택기** - QDateEdit로 날짜 선택
2. **태그별 통계 카드** - 진행률 바 + 사용 시간
3. **파이 차트** - matplotlib 기반 태그 비율 시각화
4. **프로세스 TOP 5** - QTableWidget 테이블

**코드 구조:**
```python
class DashboardTab(QWidget):
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.selected_date = datetime.now().date()

        # 레이아웃
        layout = QVBoxLayout()
        layout.addWidget(self.create_date_selector())
        layout.addLayout(self.create_stat_cards())
        layout.addWidget(self.create_chart_area())
        self.setLayout(layout)

        # 10초 자동 갱신
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(10000)

    def create_chart_area(self):
        """Matplotlib 파이 차트"""
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        return self.canvas

    def refresh_stats(self):
        stats = self.db_manager.get_stats_by_tag(
            self.selected_date,
            self.selected_date + timedelta(days=1)
        )
        self.update_cards(stats)
        self.update_pie_chart(stats)
```

**한글 폰트 처리:**
- `matplotlib.rc('font', family='Malgun Gothic')` 설정
- 차트 한글 깨짐 방지

---

### `ui/timeline_tab.py` - 타임라인 탭
**주요 기능:**
- 날짜/태그 필터링
- 실시간 활동 추가 (MonitorEngine 시그널 연결)
- QTableWidget 기반 테이블 뷰
- 태그 셀에 색상 배경 표시

```python
class TimelineTab(QWidget):
    def __init__(self, db_manager, monitor_engine):
        self.db_manager = db_manager
        self.selected_date = datetime.now().date()

        # 테이블 구성
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "시작", "종료", "프로세스", "제목/URL", "태그", "시간"
        ])

        # 실시간 업데이트 연결
        monitor_engine.activity_detected.connect(self.on_new_activity)

        self.load_timeline()

    def load_timeline(self):
        activities = self.db_manager.get_timeline(self.selected_date, limit=100)
        self.table.setRowCount(len(activities))

        for row, act in enumerate(activities):
            self.table.setItem(row, 0, QTableWidgetItem(act['start_time']))
            self.table.setItem(row, 1, QTableWidgetItem(act['end_time'] or '진행중'))
            # ... 태그 셀 색상 적용
```

---

### `ui/settings_tab.py` - 설정 탭

**구성:**
1. **일반 설정** - Windows 시작 시 자동 실행 체크박스
2. **태그 관리** - 태그 추가/수정/삭제 (QColorDialog)
3. **룰 관리** - 룰 추가/수정/삭제 (우선순위, 패턴 입력)

```python
class SettingsTab(QWidget):
    def __init__(self, db_manager, rule_engine):
        self.db_manager = db_manager
        self.rule_engine = rule_engine

        layout = QVBoxLayout()
        layout.addWidget(self.create_general_settings())

        # 하단: 태그/룰 관리를 좌우로 배치
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.create_tag_manager())
        bottom_layout.addWidget(self.create_rule_manager())
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def create_general_settings(self):
        """Windows 자동 시작 설정"""
        group = QGroupBox("일반 설정")
        layout = QVBoxLayout()

        self.autostart_cb = QCheckBox("Windows 시작 시 자동 실행")
        self.autostart_cb.setChecked(AutoStartManager.is_in_startup())
        self.autostart_cb.toggled.connect(self.on_autostart_toggled)

        layout.addWidget(self.autostart_cb)
        group.setLayout(layout)
        return group

    def on_rule_changed(self):
        """룰 변경 시 RuleEngine 즉시 리로드"""
        self.rule_engine.reload_rules()
```

---

### `ui/tray_icon.py` - 시스템 트레이
```python
class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super().__init__(parent)
        self.setIcon(QIcon("icon.png"))
        self.setToolTip("Activity Tracker")

        # 컨텍스트 메뉴
        menu = QMenu()
        menu.addAction("열기", parent.show)
        menu.addAction("종료", parent.quit_app)
        self.setContextMenu(menu)

        # 더블클릭으로 창 열기
        self.activated.connect(self.on_activated)
        self.show()

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.parent().show()
```

---

### `ui/styles.py` - 다크 테마
```python
def apply_dark_theme(app):
    """GitHub 스타일 다크 테마 적용"""
    qss = """
    QWidget {
        background-color: #1e1e1e;
        color: #d4d4d4;
        font-family: "Segoe UI", sans-serif;
    }
    QPushButton {
        background-color: #007acc;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #005a9e;
    }
    QTableWidget {
        gridline-color: #3c3c3c;
        selection-background-color: #094771;
    }
    ...
    """
    app.setStyleSheet(qss)
```

---

## 🌐 Chrome Extension (Manifest V3)

### `manifest.json` - 확장 프로그램 설정
```json
{
  "manifest_version": 3,
  "name": "Activity Tracker URL Sender",
  "version": "1.0",
  "permissions": ["tabs", "webNavigation", "storage"],
  "host_permissions": ["<all_urls>"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html"
  }
}
```

---

### `background.js` - Service Worker

**핵심 기능:**
1. WebSocket 연결 관리 (`ws://localhost:8766`)
2. 탭 활성화/업데이트/포커스 이벤트 감지
3. URL 변경 시 JSON 메시지 전송
4. 자동 재연결 (5초 간격)

```javascript
let ws = null;
let profileName = '';

// 스토리지에서 프로필명 로드
chrome.storage.local.get(['profileName'], (result) => {
  profileName = result.profileName || '';
  connectWebSocket();
});

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8766');

  ws.onopen = () => console.log('[WS] 연결됨');

  ws.onclose = () => {
    console.log('[WS] 연결 끊김, 5초 후 재연결');
    setTimeout(connectWebSocket, 5000);
  };
}

function sendURL(tabId, url, title) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'url_change',
      profileName: profileName,
      tabId: tabId,
      url: url,
      title: title,
      timestamp: Date.now()
    }));
  }
}

// 탭 활성화 시
chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    sendURL(tab.id, tab.url, tab.title);
  });
});

// 탭 URL 업데이트 시
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url && tab.active) {
    sendURL(tab.id, changeInfo.url, tab.title);
  }
});

// 창 포커스 변경 시
chrome.windows.onFocusChanged.addListener((windowId) => {
  if (windowId !== chrome.windows.WINDOW_ID_NONE) {
    chrome.tabs.query({active: true, windowId: windowId}, (tabs) => {
      if (tabs[0]) sendURL(tabs[0].id, tabs[0].url, tabs[0].title);
    });
  }
});
```

---

### `popup.html/js` - 설정 팝업

**기능:** 프로필명 입력 및 저장

```html
<input type="text" id="profileInput" placeholder="프로필명 입력">
<button id="saveBtn">저장</button>
<div id="status"></div>
```

```javascript
// 저장
document.getElementById('saveBtn').addEventListener('click', () => {
  const name = document.getElementById('profileInput').value;
  chrome.storage.local.set({profileName: name}, () => {
    document.getElementById('status').textContent = '저장됨!';
  });
});

// 로드
chrome.storage.local.get(['profileName'], (result) => {
  document.getElementById('profileInput').value = result.profileName || '';
});
```

---

## 🔄 데이터 흐름

### 1. 프로그램 시작
```
main.py
  → QApplication 생성
  → apply_dark_theme()
  → MainWindow 생성
    → DatabaseManager 초기화
    → RuleEngine 초기화
    → MonitorEngine.start() (QThread)
    → ChromeURLReceiver 시작 (별도 스레드)
    → SystemTrayIcon 표시
```

### 2. 활동 추적 루프 (2초마다)
```
MonitorEngine.run()
  → collect_activity_info()
    ├─ ScreenDetector.is_locked() → __LOCKED__?
    ├─ ScreenDetector.get_idle_duration() → __IDLE__?
    └─ WindowTracker.get_active_window() + ChromeURLReceiver.get_latest_url()

  → is_activity_changed() 체크
    → YES: end_current_activity() + start_new_activity()
      → RuleEngine.match(activity_info)
        → DatabaseManager.create_activity()
      → emit activity_detected signal
        → UI 업데이트 (Dashboard/Timeline)
```

### 3. Chrome URL 전송
```
Chrome Extension (background.js)
  → chrome.tabs.onActivated/onUpdated
  → sendURL(tabId, url, title)
    → WebSocket.send(JSON)
      → ChromeURLReceiver._handler()
        → latest_data 업데이트 (threading.Lock)
          → MonitorEngine.collect_activity_info()에서 참조
```

### 4. 룰 변경
```
SettingsTab
  → 사용자가 룰 추가/수정/삭제
  → DatabaseManager.create_rule() / update_rule() / delete_rule()
  → RuleEngine.reload_rules()
    → rules_cache 갱신
      → 다음 활동부터 새 룰 적용
```

---

## 📐 핵심 설계 원칙

### 1. 스레드 안전성
- **DatabaseManager**: `threading.local`로 스레드별 연결 분리
- **ChromeURLReceiver**: `threading.Lock`으로 데이터 보호
- **MonitorEngine**: QThread로 메인 UI와 격리

### 2. 느슨한 결합
- Backend 모듈은 UI 의존성 없음 (헤드리스 실행 가능)
- Qt Signal/Slot으로 UI 업데이트 전달
- RuleEngine은 DB만 참조, 다른 모듈과 독립

### 3. 확장 가능성
- 태그/룰 시스템으로 무한한 분류 가능
- 우선순위 기반 룰 매칭으로 복잡한 조건 표현
- 쉼표 구분 패턴으로 한 룰에 여러 조건 통합

### 4. 사용자 제어
- 모든 태그/룰 UI에서 CRUD
- 실시간 룰 변경 즉시 반영
- 수동 태그 변경 가능 (타임라인)

---

## 🛠️ 기술 스택

**Backend:**
- Python 3.x
- SQLite3 (WAL 모드)
- threading (멀티스레딩)
- asyncio + websockets (WebSocket 서버)
- ctypes (Windows API)
- psutil (프로세스 정보)

**Frontend:**
- PyQt6 (GUI)
- matplotlib (차트)
- QSS (스타일시트)

**Chrome Extension:**
- Manifest V3
- Service Worker (background.js)
- chrome.tabs/webNavigation API
- WebSocket 클라이언트

**빌드/배포:**
- PyInstaller (단일 exe)
- Windows Registry (자동 시작)

---

## 🔐 보안 및 프라이버시

- 모든 데이터 로컬 저장 (외부 전송 없음)
- WebSocket 통신은 localhost만 허용
- Chrome Extension은 로컬 연결만 사용
- 개인 사용 목적, 배포 없음
