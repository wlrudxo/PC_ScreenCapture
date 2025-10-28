# 활동 추적 시스템 V2 - 아키텍처 설계

## 📋 목표
연구실에서 업무 vs 딴짓 비율을 추적하는 개인용 데스크톱 애플리케이션

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
                  │
┌─────────────────▼───────────────────────────────┐
│              Backend Core                        │
│  ┌────────────────────────────────────────────┐ │
│  │  MonitorEngine (Thread)                    │ │
│  │  - WindowTracker                           │ │
│  │  - ScreenLockDetector                      │ │
│  │  - ChromeURLReceiver (WebSocket)           │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  RuleEngine                                │ │
│  │  - 프로그램/URL → 태그 매칭                 │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  DatabaseManager                           │ │
│  │  - SQLite 저장/조회                         │ │
│  └────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              SQLite Database                     │
│  - tags                                          │
│  - activities                                    │
│  - rules                                         │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│          Chrome Extension                        │
│  - 활성 탭 URL 전송 (WebSocket)                  │
│  - 프로필명 포함                                  │
└──────────────────────────────────────────────────┘
```

---

## 🗄️ 데이터베이스 스키마

### 1. `tags` - 태그 정의 테이블
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,        -- 태그 이름 (예: "업무", "딴짓", "자리비움")
    color TEXT NOT NULL,               -- UI 표시 색상 (예: "#4CAF50")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 태그
INSERT INTO tags (name, color) VALUES
    ('업무', '#4CAF50'),
    ('딴짓', '#FF5722'),
    ('자리비움', '#9E9E9E'),
    ('미분류', '#607D8B');
```

**특징:**
- ID 기반 참조 → 태그 이름 변경 시 activities 테이블은 영향 없음
- 사용자가 자유롭게 태그 추가/삭제/이름변경 가능

---

### 2. `activities` - 활동 기록 테이블
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,                -- NULL이면 현재 진행 중

    -- 활동 정보
    process_name TEXT,                 -- 예: "chrome.exe", "__LOCKED__", "__IDLE__"
    window_title TEXT,                 -- 예: "YouTube - Chrome"
    chrome_profile TEXT,               -- 예: "업무용", "딴짓용"
    chrome_url TEXT,                   -- 예: "https://youtube.com/watch?v=..."

    -- 분류
    tag_id INTEGER,                    -- tags 테이블 외래키
    rule_id INTEGER,                   -- 어떤 룰에 의해 분류됐는지

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL,
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE SET NULL
);

-- 인덱스 (성능 최적화)
CREATE INDEX idx_activities_time ON activities(start_time, end_time);
CREATE INDEX idx_activities_tag ON activities(tag_id);
CREATE INDEX idx_activities_process ON activities(process_name);
```

**특징:**
- `start_time` ~ `end_time` 구간으로 활동 시간 계산
- Chrome URL과 프로필 정보 저장
- 화면 잠금/idle은 `process_name`을 `__LOCKED__` / `__IDLE__`로 저장하여 룰 엔진에서 통일된 방식으로 처리
- tag_id로 태그 참조 (태그 이름 변경해도 기록 유지)

---

### 3. `rules` - 자동 분류 룰 테이블
```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                -- 룰 이름 (예: "YouTube는 딴짓")
    priority INTEGER DEFAULT 0,        -- 우선순위 (높을수록 먼저 적용)
    enabled BOOLEAN DEFAULT 1,         -- 활성화 여부

    -- 매칭 조건 (OR 관계)
    process_pattern TEXT,              -- 프로세스 매칭 (예: "chrome.exe")
    url_pattern TEXT,                  -- URL 매칭 (예: "*youtube.com*")
    window_title_pattern TEXT,         -- 창 제목 매칭 (예: "*YouTube*")
    chrome_profile TEXT,               -- Chrome 프로필 (예: "딴짓용")

    -- 분류 결과
    tag_id INTEGER NOT NULL,           -- 적용할 태그

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 기본 룰 예시
INSERT INTO rules (name, priority, process_pattern, tag_id) VALUES
    ('화면 잠금', 100, '__LOCKED__', (SELECT id FROM tags WHERE name='자리비움')),
    ('Idle 상태', 90, '__IDLE__', (SELECT id FROM tags WHERE name='자리비움'));

INSERT INTO rules (name, priority, url_pattern, tag_id) VALUES
    ('YouTube는 딴짓', 50, '*youtube.com*', (SELECT id FROM tags WHERE name='딴짓')),
    ('GitHub는 업무', 50, '*github.com*', (SELECT id FROM tags WHERE name='업무'));

INSERT INTO rules (name, priority, chrome_profile, tag_id) VALUES
    ('업무용 Chrome', 30, '업무용', (SELECT id FROM tags WHERE name='업무')),
    ('딴짓용 Chrome', 30, '딴짓용', (SELECT id FROM tags WHERE name='딴짓'));
```

**특징:**
- 우선순위(priority) 기반 적용 (높은 것 먼저)
- 여러 조건 중 하나라도 매치되면 적용
- 와일드카드 패턴 지원 (`*youtube.com*`)
- 사용자가 UI에서 자유롭게 추가/수정/삭제

---

## 🔧 백엔드 모듈 구조

### 📁 파일 구조
```
PC_ScreenCapture_V2/
├── main.py                      # 메인 진입점
├── backend/
│   ├── __init__.py
│   ├── config.py                # 설정 및 경로 관리 ⭐
│   ├── monitor_engine.py        # 모니터링 엔진 (스레드)
│   ├── window_tracker.py        # 활성 창 감지
│   ├── screen_detector.py       # 화면 잠금/idle 감지
│   ├── chrome_receiver.py       # Chrome WebSocket 서버
│   ├── rule_engine.py           # 룰 매칭 엔진
│   └── database.py              # DB 매니저
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # 메인 윈도우
│   ├── dashboard_tab.py         # 대시보드 탭
│   ├── timeline_tab.py          # 타임라인 탭
│   ├── settings_tab.py          # 설정 탭
│   ├── tray_icon.py             # 시스템 트레이
│   └── styles.py                # QSS 스타일
├── chrome_extension/            # Chrome 확장
│   ├── manifest.json
│   ├── background.js
│   ├── popup.html
│   └── popup.js
└── activity_tracker.db          # SQLite DB
```

---

### 0️⃣ `backend/config.py` - 설정 및 경로 관리
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

**특징:**
- `sys.frozen` 체크로 개발/빌드 모드 자동 구분
- 개발 중: 프로젝트 폴더에 저장 → 디버깅 편함
- 빌드 후: AppData 사용 → Windows 표준, 권한 문제 없음
- 경로 변경 시 한 곳만 수정하면 전체 반영

**사용 예시:**
```python
from backend.config import AppConfig

# DB 경로 자동 설정
db_manager = DatabaseManager(db_path=AppConfig.get_db_path())

# 현재 모드 확인
if AppConfig.is_dev_mode():
    print("개발 모드로 실행 중")
```

---

### 1️⃣ `backend/monitor_engine.py` - 모니터링 엔진
```python
class MonitorEngine(QThread):
    """
    백그라운드 스레드로 실행
    - 활성 창 감지
    - 화면 잠금/idle 감지
    - Chrome URL 수신
    - 룰 엔진으로 분류 → DB 저장
    """

    activity_detected = pyqtSignal(dict)  # UI 업데이트용 시그널

    def __init__(self, db_manager, rule_engine):
        self.window_tracker = WindowTracker()
        self.screen_detector = ScreenDetector()
        self.chrome_receiver = ChromeURLReceiver(port=8766)
        self.db_manager = db_manager
        self.rule_engine = rule_engine

        self.current_activity = None
        self.last_check_time = None

    def run(self):
        """2초마다 현재 활동 체크"""
        while self.running:
            activity_info = self.collect_activity_info()

            # 활동이 변경되었으면 이전 활동 종료 + 새 활동 시작
            if self.is_activity_changed(activity_info):
                self.end_current_activity()
                self.start_new_activity(activity_info)

            time.sleep(2)

    def collect_activity_info(self):
        """
        현재 활동 정보 수집
        중요: 화면 잠금/idle 상태를 먼저 판단하여 process_name으로 설정
        """
        # 1. 최우선: 화면 잠금 상태
        if self.screen_detector.is_locked():
            return {
                'process_name': '__LOCKED__',
                'window_title': 'Screen Locked',
                'chrome_url': None,
                'chrome_profile': None,
            }

        # 2. 유휴(idle) 상태 체크 (5분 임계값)
        idle_seconds = self.screen_detector.get_idle_duration()
        if idle_seconds > 300:
            return {
                'process_name': '__IDLE__',
                'window_title': f'Idle ({idle_seconds}s)',
                'chrome_url': None,
                'chrome_profile': None,
            }

        # 3. 일반 활동
        window_info = self.window_tracker.get_active_window()
        chrome_data = self.chrome_receiver.get_latest_url()  # {'url': ..., 'profile': ...}

        return {
            'process_name': window_info['process_name'],
            'window_title': window_info['window_title'],
            'chrome_url': chrome_data.get('url'),
            'chrome_profile': chrome_data.get('profile'),
        }

    def start_new_activity(self, info):
        """새 활동 시작 → DB 저장"""
        tag_id, rule_id = self.rule_engine.match(info)

        self.current_activity = self.db_manager.create_activity(
            process_name=info['process_name'],
            window_title=info['window_title'],
            chrome_url=info['chrome_url'],
            chrome_profile=info['chrome_profile'],
            tag_id=tag_id,
            rule_id=rule_id
        )

        self.activity_detected.emit(info)  # UI 업데이트
```

---

### 2️⃣ `backend/rule_engine.py` - 룰 매칭 엔진
```python
class RuleEngine:
    """
    활동 정보 → 태그 자동 분류
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.rules_cache = []
        self.reload_rules()

    def reload_rules(self):
        """DB에서 룰 불러오기 (우선순위 정렬)"""
        self.rules_cache = self.db_manager.get_all_rules(
            enabled_only=True,
            order_by='priority DESC'
        )

    def match(self, activity_info):
        """
        활동 정보와 룰을 매칭해서 tag_id, rule_id 반환

        단순화된 로직:
        - 모든 상태(__LOCKED__, __IDLE__ 포함)를 통일된 방식으로 처리
        - priority 높은 룰부터 순회하며 첫 매칭 반환
        """

        # 룰 순회 (우선순위 높은 것부터)
        for rule in self.rules_cache:
            if self.is_matched(rule, activity_info):
                return rule['tag_id'], rule['id']

        # 매칭 실패 → "미분류" 태그
        unclassified_tag_id = self.db_manager.get_tag_by_name('미분류')['id']
        return unclassified_tag_id, None

    def is_matched(self, rule, activity_info):
        """룰 조건과 활동 정보 매칭 (OR 관계)"""

        # URL 패턴 매칭
        if rule['url_pattern']:
            if fnmatch(activity_info['chrome_url'], rule['url_pattern']):
                return True

        # Chrome 프로필 매칭
        if rule['chrome_profile']:
            if activity_info['chrome_profile'] == rule['chrome_profile']:
                return True

        # 프로세스 이름 매칭
        if rule['process_pattern']:
            if fnmatch(activity_info['process_name'], rule['process_pattern']):
                return True

        # 창 제목 매칭
        if rule['window_title_pattern']:
            if fnmatch(activity_info['window_title'], rule['window_title_pattern']):
                return True

        return False
```

---

### 2.5️⃣ `backend/chrome_receiver.py` - Chrome WebSocket 수신기
```python
import threading
import asyncio
import websockets
import json

class ChromeURLReceiver:
    """
    Chrome Extension으로부터 URL 수신 (WebSocket 서버)

    중요: 별도 스레드에서 asyncio 이벤트 루프 실행
    """

    def __init__(self, port=8766):
        self.latest_data = {}
        self.port = port
        self.lock = threading.Lock()  # 스레드 안전성 확보

        # WebSocket 서버를 위한 별도 데몬 스레드 시작
        threading.Thread(target=self._start_server, daemon=True).start()

    def _start_server(self):
        """별도 스레드에서 asyncio 이벤트 루프 실행"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        start_server = websockets.serve(self._handler, "localhost", self.port)
        loop.run_until_complete(start_server)
        print(f"[ChromeURLReceiver] WebSocket 서버 시작: ws://localhost:{self.port}")
        loop.run_forever()

    async def _handler(self, websocket, path):
        """Chrome Extension 연결 처리"""
        print(f"[ChromeURLReceiver] Chrome Extension 연결됨")
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
                            'timestamp': data.get('timestamp'),
                        }
            except json.JSONDecodeError:
                pass

    def get_latest_url(self):
        """
        MonitorEngine에서 호출할 스레드 안전한 함수
        Returns: {'url': ..., 'profile': ...} or {}
        """
        with self.lock:
            return self.latest_data.copy()
```

**특징:**
- `threading.Thread`로 별도 스레드에서 WebSocket 서버 실행
- `MonitorEngine` (QThread)과 독립적으로 동작
- `threading.Lock`으로 스레드 안전성 확보
- Chrome Extension이 연결 끊어져도 프로그램은 정상 동작

---

### 3️⃣ `backend/database.py` - DB 매니저
```python
from backend.config import AppConfig
import sqlite3

class DatabaseManager:
    """SQLite 데이터베이스 관리"""

    def __init__(self, db_path=None):
        # db_path 지정 안 하면 AppConfig에서 자동 설정
        if db_path is None:
            db_path = AppConfig.get_db_path()

        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_database()

    def init_database(self):
        """테이블 생성 + 기본 데이터 삽입"""
        # 위의 SQL 스키마 실행

    # === 태그 관리 ===
    def get_all_tags(self):
        """모든 태그 조회"""

    def create_tag(self, name, color):
        """태그 생성"""

    def update_tag(self, tag_id, name=None, color=None):
        """태그 수정 (이름 변경해도 activities는 영향 없음)"""

    def delete_tag(self, tag_id):
        """태그 삭제 (activities.tag_id는 NULL로)"""

    # === 활동 기록 ===
    def create_activity(self, **kwargs):
        """새 활동 시작 (start_time=now, end_time=NULL)"""

    def end_activity(self, activity_id):
        """활동 종료 (end_time=now)"""

    def get_activities(self, start_date, end_date):
        """기간별 활동 조회"""

    # === 통계 ===
    def get_stats_by_tag(self, start_date, end_date):
        """태그별 사용 시간 통계"""
        sql = """
        SELECT
            t.name AS tag_name,
            t.color AS tag_color,
            SUM((julianday(COALESCE(end_time, datetime('now'))) -
                 julianday(start_time)) * 86400) AS total_seconds
        FROM activities a
        JOIN tags t ON a.tag_id = t.id
        WHERE start_time >= ? AND start_time < ?
        GROUP BY t.id
        ORDER BY total_seconds DESC
        """

    def get_stats_by_process(self, start_date, end_date):
        """프로세스별 사용 시간 통계"""

    def get_timeline(self, date, limit=100):
        """특정 날짜의 타임라인"""

    # === 룰 관리 ===
    def get_all_rules(self, enabled_only=False, order_by='priority DESC'):
        """모든 룰 조회"""

    def create_rule(self, **kwargs):
        """룰 생성"""

    def update_rule(self, rule_id, **kwargs):
        """룰 수정"""

    def delete_rule(self, rule_id):
        """룰 삭제"""
```

---

## 🖥️ 프론트엔드 (PyQt6) 구조

### 1️⃣ `ui/main_window.py` - 메인 윈도우
```python
class MainWindow(QMainWindow):
    """
    메인 윈도우
    - 탭 구조 (Dashboard, Timeline, Settings)
    - 시스템 트레이 통합
    - 백그라운드 모니터링 시작
    """

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.rule_engine = RuleEngine(self.db_manager)
        self.monitor_engine = MonitorEngine(self.db_manager, self.rule_engine)

        # UI 구성
        self.create_tabs()
        self.create_tray_icon()

        # 모니터링 시작
        self.monitor_engine.activity_detected.connect(self.on_activity_update)
        self.monitor_engine.start()

    def create_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(DashboardTab(self.db_manager), "📊 대시보드")
        tabs.addTab(TimelineTab(self.db_manager), "⏱️ 타임라인")
        tabs.addTab(SettingsTab(self.db_manager, self.rule_engine), "⚙️ 설정")
        self.setCentralWidget(tabs)

    def create_tray_icon(self):
        """시스템 트레이 아이콘"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon("icon.png"))

        menu = QMenu()
        menu.addAction("열기", self.show)
        menu.addAction("종료", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def closeEvent(self, event):
        """창 닫기 → 트레이로 최소화"""
        event.ignore()
        self.hide()
```

---

### 2️⃣ `ui/dashboard_tab.py` - 대시보드 탭
```python
class DashboardTab(QWidget):
    """
    오늘의 통계 대시보드
    - 태그별 사용 시간 (카드 + 진행률 바)
    - 파이 차트 (matplotlib)
    - 프로세스별 TOP 5
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # 날짜 선택
        layout.addWidget(self.create_date_selector())

        # 통계 카드
        layout.addLayout(self.create_stat_cards())

        # 차트 영역
        layout.addWidget(self.create_chart_area())

        self.setLayout(layout)

        # 10초마다 자동 갱신
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(10000)

    def refresh_stats(self):
        """통계 데이터 갱신"""
        today = datetime.now().date()
        stats = self.db_manager.get_stats_by_tag(today, today + timedelta(days=1))
        self.update_cards(stats)
        self.update_chart(stats)
```

---

### 3️⃣ `ui/timeline_tab.py` - 타임라인 탭
```python
class TimelineTab(QWidget):
    """
    활동 타임라인 (테이블)
    - 시간, 프로세스, 제목/URL, 태그, 시간 표시
    - 필터링 (날짜, 태그)
    - 수동 태그 변경 가능
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # 필터
        layout.addLayout(self.create_filters())

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "시작 시간", "종료 시간", "프로세스", "제목/URL", "태그", "시간"
        ])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_timeline()

    def load_timeline(self):
        """타임라인 데이터 로드"""
        activities = self.db_manager.get_timeline(self.selected_date)
        self.populate_table(activities)
```

---

### 4️⃣ `ui/settings_tab.py` - 설정 탭
```python
class SettingsTab(QWidget):
    """
    설정 탭
    - 태그 관리 (추가/수정/삭제)
    - 룰 관리 (추가/수정/삭제/우선순위)
    """

    def __init__(self, db_manager, rule_engine):
        self.db_manager = db_manager
        self.rule_engine = rule_engine

        layout = QHBoxLayout()

        # 왼쪽: 태그 관리
        layout.addWidget(self.create_tag_manager())

        # 오른쪽: 룰 관리
        layout.addWidget(self.create_rule_manager())

        self.setLayout(layout)

    def create_tag_manager(self):
        """태그 추가/수정/삭제 UI"""
        widget = QGroupBox("태그 관리")
        layout = QVBoxLayout()

        # 태그 리스트
        self.tag_list = QListWidget()
        self.load_tags()

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("추가", clicked=self.add_tag))
        btn_layout.addWidget(QPushButton("수정", clicked=self.edit_tag))
        btn_layout.addWidget(QPushButton("삭제", clicked=self.delete_tag))

        layout.addWidget(self.tag_list)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def create_rule_manager(self):
        """룰 추가/수정/삭제 UI"""
        widget = QGroupBox("분류 룰 관리")
        layout = QVBoxLayout()

        # 룰 테이블
        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(5)
        self.rule_table.setHorizontalHeaderLabels([
            "우선순위", "이름", "조건", "태그", "활성화"
        ])
        self.load_rules()

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("추가", clicked=self.add_rule))
        btn_layout.addWidget(QPushButton("수정", clicked=self.edit_rule))
        btn_layout.addWidget(QPushButton("삭제", clicked=self.delete_rule))

        layout.addWidget(self.rule_table)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def add_rule(self):
        """룰 추가 다이얼로그"""
        dialog = RuleEditDialog(self.db_manager)
        if dialog.exec():
            rule_data = dialog.get_rule_data()
            self.db_manager.create_rule(**rule_data)
            self.rule_engine.reload_rules()  # 룰 엔진 갱신!
            self.load_rules()
```

---

## 🔄 실행 흐름

### 프로그램 시작
1. `main.py` 실행
2. SQLite DB 초기화 (테이블 생성, 기본 데이터)
3. PyQt6 메인 윈도우 생성
4. 백그라운드 모니터링 스레드 시작
5. Chrome Extension WebSocket 서버 시작 (포트 8766)
6. 시스템 트레이에 아이콘 표시

### 활동 추적 루프 (2초마다)
1. **WindowTracker** - 활성 창 정보 수집
2. **ScreenDetector** - 화면 잠금/idle 체크
3. **ChromeURLReceiver** - 최신 Chrome URL 가져오기
4. **활동 변경 감지**
   - 이전 활동과 다르면?
     - 이전 활동 종료 (end_time 업데이트)
     - 새 활동 시작 (DB INSERT)
5. **RuleEngine** - 룰 매칭해서 태그 자동 분류
6. **UI 업데이트** - 시그널로 프론트엔드에 알림

### 사용자 인터랙션
- **대시보드**: 실시간 통계 확인
- **타임라인**: 과거 활동 검색, 수동 태그 변경
- **설정**: 태그/룰 추가/수정/삭제 → RuleEngine 즉시 리로드

---

## 🎨 UI/UX 특징

### 시스템 트레이 통합
- 백그라운드 실행 (항상 모니터링)
- 트레이 아이콘 클릭 → 메인 창 열기
- 창 닫기 → 트레이로 최소화

### 실시간 업데이트
- 대시보드: 10초마다 통계 갱신
- 타임라인: 새 활동 추가 시 자동 추가
- 설정: 룰 변경 → 즉시 적용

### 다크 테마
- GitHub 스타일 다크 모드
- QSS로 통일된 디자인

---

## 🚀 구현 순서

### Phase 1: 백엔드 코어
1. ✅ 데이터베이스 스키마 구현
2. ✅ DatabaseManager 구현
3. ✅ 테스트 파일 3개 통합 → MonitorEngine
4. ✅ RuleEngine 구현

### Phase 2: 프론트엔드 기본
5. ✅ MainWindow + 탭 구조
6. ✅ DashboardTab (기본 통계)
7. ✅ TimelineTab (테이블)

### Phase 3: 설정 기능
8. ✅ SettingsTab - 태그 관리
9. ✅ SettingsTab - 룰 관리
10. ✅ RuleEditDialog (룰 추가/수정 UI)

### Phase 4: 고급 기능
11. ✅ 차트 (matplotlib 통합)
12. ✅ 시스템 트레이
13. ✅ 자동 시작 (Windows 시작 프로그램 등록)

### Phase 5: 패키징
14. ✅ PyInstaller로 실행 파일 생성
15. ✅ 설치 프로그램 (선택)

---

## 📝 핵심 설계 결정

### 1. 태그 ID 기반 참조
- 태그 이름 변경 시 activities 테이블 영향 없음
- `UPDATE tags SET name='연구' WHERE id=1` → 모든 기록 자동 반영

### 2. 룰 우선순위
- 화면 잠금 > URL > Chrome 프로필 > 프로세스 > 창 제목
- 우선순위 숫자로 사용자 커스터마이징 가능

### 3. 와일드카드 패턴
- `*youtube.com*` - YouTube 관련 모든 URL
- `*github.com/user/work-repo*` - 특정 레포지토리만

### 4. 실시간 룰 갱신
- 설정에서 룰 변경 → `rule_engine.reload_rules()` 호출
- 다음 활동부터 즉시 적용

### 5. 활동 구간 저장
- `start_time` ~ `end_time` 구간
- 통계 계산 시 `SUM(julianday(end_time) - julianday(start_time))`

---

## 📦 빌드 및 배포

### .gitignore 설정
```gitignore
# 데이터베이스
activity_tracker.db
activity_tracker.db-journal
*.db
*.db-journal

# 설정 파일
config.json

# 로그
logs/
*.log

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# PyInstaller
*.spec

# IDE
.vscode/
.idea/
*.swp
*.swo
```

### PyInstaller 빌드
```bash
# PyInstaller 설치
pip install pyinstaller

# 실행 파일 생성 (터미널 없이)
pyinstaller --windowed --onefile --name="ActivityTracker" --icon=icon.ico main.py

# 결과: dist/ActivityTracker.exe
```

**빌드 옵션:**
- `--windowed` (또는 `-w`) - 터미널 창 숨김
- `--onefile` - 단일 .exe 파일 생성
- `--name` - 실행 파일 이름
- `--icon` - 아이콘 파일 지정

**빌드 후 동작:**
- `sys.frozen = True` → AppConfig가 자동으로 AppData 경로 사용
- 개발 중 DB는 프로젝트 폴더, 빌드 후 DB는 AppData에 분리

### Windows 시작 프로그램 등록
```python
# UI 설정 탭에서 체크박스로 제공
import winreg
import sys

def add_to_startup():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "ActivityTracker", 0, winreg.REG_SZ, sys.executable)
    winreg.CloseKey(key)
```

---

## 🔐 보안/프라이버시
- 모든 데이터 로컬 저장 (SQLite)
- 네트워크 통신은 localhost WebSocket만 (Chrome Extension)
- 배포 안함, 개인 사용

---

## 📝 AI 검토 반영 사항

### 1. RuleEngine 로직 단순화 ✅
**문제:** `is_locked`, `is_idle` 상태를 코드에서 하드코딩 + DB 룰로 중복 처리

**해결:**
- `MonitorEngine.collect_activity_info()`에서 상태를 먼저 판단
- 화면 잠금 → `process_name = '__LOCKED__'`
- Idle 상태 → `process_name = '__IDLE__'`
- `RuleEngine.match()`는 모든 상태를 동일한 방식으로 처리 (priority 기반)

**장점:**
- 하드코딩 제거, 모든 로직이 `rules` 테이블로 위임
- 사용자가 UI에서 자유롭게 idle 임계값 변경 가능 (룰 우선순위 조정)

### 2. activities 테이블 스키마 단순화 ✅
**문제:** `is_locked`, `is_idle` 컬럼이 `tag_id`와 중복

**해결:**
- `is_locked`, `is_idle`, `idle_seconds` 컬럼 제거
- 상태는 `process_name`과 `tag_id`로 충분히 판별 가능
- 필요 시 '화면잠금', '유휴상태' 태그를 별도로 생성

**장점:**
- 데이터 중복 제거
- 스키마 단순화

### 3. WebSocket 서버 스레드 관리 ✅
**문제:** `ChromeURLReceiver`의 asyncio 이벤트 루프가 메인/QThread 차단 가능성

**해결:**
- `threading.Thread(daemon=True)`로 별도 스레드에서 WebSocket 서버 실행
- `threading.Lock`으로 스레드 안전성 확보
- `MonitorEngine` (QThread)과 독립적으로 동작

**장점:**
- UI/모니터링 스레드 차단 방지
- Chrome Extension 연결 끊어져도 프로그램 정상 동작

---

## 🚀 다음 단계
Phase 1부터 구현 시작!
