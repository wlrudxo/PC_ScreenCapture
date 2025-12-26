# Activity Tracker V2 - Architecture (WebUI)

## Overview

Windows 데스크톱 활동 추적 애플리케이션. 활성 창, Chrome URL, 화면 잠금/idle 상태를 일정 간격으로 감지해 룰 기반으로 태그를 분류하고, 웹 UI에서 통계/타임라인/설정을 제공한다.

**Core Features:**
- 실시간 모니터링 (threading 기반 MonitorEngine)
- Chrome URL 추적 (WebSocket + Extension)
- 우선순위 기반 자동 태그 분류
- 토스트 알림 (사운드/이미지 지원)
- 집중 모드 (태그 + 시간대 기반 창 최소화)
- 활동 로그 자동 생성 (LLM 분석용)
- FastAPI + Svelte Web UI (PyWebView 내장)
- 시스템 트레이 백그라운드 실행

---

## System Architecture

```
+------------------------------------------------------------------+
|                          PyWebView Shell                          |
|  - main_webview.pyw                                                |
|  - EdgeChromium backend                                            |
|  - pystray system tray                                             |
+-------------------------------+----------------------------------+
                                | loads
+-------------------------------v----------------------------------+
|                         Web UI (Svelte SPA)                       |
|  Routes: Dashboard / Timeline / Analysis / Tags / Alerts / Focus  |
|  - REST: /api/*                                                     |
|  - WS:  /ws/activity                                                |
+-------------------------------+----------------------------------+
                                | HTTP + WebSocket
+-------------------------------v----------------------------------+
|                          FastAPI API Server                        |
|  - api_server.py                                                   |
|  - static: webui/dist                                               |
|  - REST + WebSocket                                                 |
+-------------------------------+----------------------------------+
                                | runtime engines
+-------------------------------v----------------------------------+
|                         Backend Core (Threading)                   |
|  MonitorEngineThread                                              |
|   + WindowTracker (ctypes + psutil)                               |
|   + ScreenDetector (lock/idle)                                     |
|   + ChromeURLReceiver (WebSocket server :8766)                     |
|   + NotificationManager (windows-toasts + winsound)                |
|   + FocusBlocker (window minimize)                                 |
|  RuleEngine (priority-based matching)                              |
|  DatabaseManager (thread-local SQLite WAL)                         |
|  ActivityLogGenerator (daily/recent/monthly logs)                  |
|  ImportExportManager (DB/rule backup/restore)                      |
+-------------------------------+----------------------------------+
                                |
+-------------------------------v----------------------------------+
|                     SQLite Database (WAL)                          |
|  tags, activities, rules, settings,                                |
|  alert_sounds, alert_images                                        |
+------------------------------------------------------------------+

+-----------------------------------------------------------+
|              Chrome Extension (Manifest V3)                |
|  WebSocket client (ws://localhost:8766)                    |
|  Active tab URL/profile push + auto-reconnect              |
+-----------------------------------------------------------+
```

---

## Directory Structure

```
PC_ScreenCapture/
+-- main_webview.pyw             # Entry point (PyWebView)
+-- backend/
|   +-- api_server.py            # FastAPI REST + WS
|   +-- monitor_engine_thread.py # Monitor loop (threading)
|   +-- window_tracker.py        # Active window detection
|   +-- screen_detector.py       # Lock/idle detection
|   +-- chrome_receiver.py       # WebSocket server (Chrome)
|   +-- rule_engine.py           # Rule matching engine
|   +-- database.py              # SQLite manager (WAL)
|   +-- notification_manager.py  # Toast + sound/image
|   +-- focus_blocker.py         # Focus mode window minimize
|   +-- log_generator.py         # Activity log generation
|   +-- import_export.py         # DB/rule import/export
|   +-- auto_start.py            # Windows auto-start registry
|   +-- config.py                # Path/settings (dev vs build)
|
+-- webui/                       # Svelte SPA (latest UI)
|   +-- src/                     # UI source
|   +-- dist/                    # Production build (served by FastAPI)
|
+-- chrome_extension/            # Manifest V3 extension
+
+-- legacy_pyqt/                 # Legacy PyQt implementation
+-- ui/                          # Legacy PyQt UI modules
+-- activity_logs/               # Dev-mode log output (created at runtime)
```

---

## Database Schema

### `tags`
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    category TEXT DEFAULT 'other',
    alert_enabled BOOLEAN DEFAULT 0,
    alert_message TEXT,
    alert_cooldown INTEGER DEFAULT 30,
    block_enabled BOOLEAN DEFAULT 0,
    block_start_time TEXT,
    block_end_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
Default tags: 업무(#4CAF50), 딴짓(#FF5722), 자리비움(#9E9E9E), 미분류(#607D8B)

### `activities`
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    process_name TEXT,
    window_title TEXT,
    chrome_profile TEXT,
    chrome_url TEXT,
    tag_id INTEGER,
    rule_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL,
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE SET NULL
);
-- Indexes: idx_activities_time, idx_activities_tag, idx_activities_process
```

### `rules`
```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT 1,
    process_pattern TEXT,
    url_pattern TEXT,
    window_title_pattern TEXT,
    chrome_profile TEXT,
    process_path_pattern TEXT,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```
- Priority-based sequential matching
- Multiple patterns with comma separator
- Wildcard support (`*`, `?`) via fnmatch

### `settings`
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```
Key settings: `alert_toast_enabled`, `alert_sound_enabled`, `alert_sound_mode`, `alert_sound_selected`, `alert_image_enabled`, `alert_image_mode`, `alert_image_selected`, `polling_interval`, `idle_threshold`, `log_retention_days`, `target_distraction_ratio`

### `alert_sounds`
```sql
CREATE TABLE alert_sounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `alert_images`
```sql
CREATE TABLE alert_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Backend Modules

### `monitor_engine_thread.py` - MonitorEngineThread

Threading 기반 모니터링 루프. 폴링 간격 및 idle 임계값은 settings에서 동적으로 로드.

```python
class MonitorEngineThread(threading.Thread):
    DEFAULT_POLLING_INTERVAL = 2
    DEFAULT_IDLE_THRESHOLD = 300

    def run(self):
        while not self._stop_event.is_set():
            activity_info = self.collect_activity_info()
            if self._is_activity_changed(activity_info):
                self.end_current_activity()
                self.start_new_activity(activity_info)
            else:
                self._check_tag_alert(self.current_tag_id)
                self.focus_blocker.check_and_block(self.current_tag_id, hwnd)
            self._stop_event.wait(timeout=polling_interval)
```

**Activity collection priority:**
1. `is_locked()` -> `__LOCKED__`
2. `get_idle_duration() > idle_threshold` -> `__IDLE__`
3. Normal activity -> WindowTracker + ChromeURLReceiver

### `focus_blocker.py` - FocusBlocker

Tag + 시간대 기반 창 최소화. 시간대가 설정된 태그만 차단 대상.

```python
class FocusBlocker:
    def is_blocked(self, tag_id: int) -> bool:
        # block_enabled + time range 체크

    def check_and_block(self, tag_id: int, hwnd: int) -> bool:
        if self.is_blocked(tag_id):
            windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
            return True
        return False
```

### `notification_manager.py` - NotificationManager

Windows 토스트 + 사운드/이미지 알림.

```python
class NotificationManager:
    # windows-toasts 사용 (AUMID: ActivityTracker)
    def show(self, tag_id, title, message, cooldown=None):
        if self._can_notify(tag_id, cooldown):
            self._show_toast(message)           # Hero image 지원
            self._play_custom_sound()           # 별도 스레드
```

### `log_generator.py` - ActivityLogGenerator

활동 로그 생성 (일별/최근/월별). 보관 일수는 settings `log_retention_days` 사용.

```python
class ActivityLogGenerator:
    def generate_daily_log(self, date) -> str:
        # 압축 포맷: 요약/태그/프로세스/웹사이트/시간대
    def generate_recent_log(self):
        # 최근 N일 통합
    def generate_monthly_log(self, year, month):
        # 월별 아카이브
```

### `api_server.py` - FastAPI

REST + WebSocket API, Web UI 정적 파일 서빙.

- REST: dashboard/timeline/analysis/tags/rules/settings/alerts/focus/import-export
- WS: `/ws/activity` (실시간 활동 이벤트)
- Static: `/` and `/assets` from `webui/dist`

---

## Frontend (Web UI)

Svelte + Vite 기반 SPA (`webui/`). `svelte-spa-router`로 라우팅.

Routes:
- `/` Dashboard
- `/timeline` Timeline
- `/analysis` Analysis
- `/tags` Tag Management
- `/notification` Alert Settings
- `/focus` Focus Mode
- `/settings` General Settings

Web UI는 FastAPI REST를 통해 데이터 조회/갱신, `/ws/activity`로 실시간 활동 업데이트 수신.

---

## Data Flow

### 1. Activity Tracking Loop

```
MonitorEngineThread.run() [polling_interval]
  -> collect_activity_info()
       +-- is_locked() -> __LOCKED__?
       +-- get_idle_duration() > idle_threshold -> __IDLE__?
       +-- get_active_window() + get_latest_url()
  -> _is_activity_changed()?
       YES: end_current_activity() + start_new_activity()
            -> rule_engine.match() -> tag_id, rule_id
            -> db_manager.create_activity()
            -> callback: WebSocket broadcast
            -> notification + focus block
       NO:  -> _check_tag_alert() + focus_blocker.check_and_block()
```

### 2. Chrome URL Tracking

```
Chrome Extension
  -> tabs.onActivated / onUpdated / windows.onFocusChanged
  -> WebSocket.send(JSON)
     -> ChromeURLReceiver._handler()
        -> latest_data update (thread lock)
```

### 3. Web UI Updates

```
Web UI (Svelte)
  -> REST /api/* for CRUD + stats
  -> WS /ws/activity for live activity updates
```

### 4. Alerts + Focus Mode

```
MonitorEngineThread
  -> NotificationManager.show() [cooldown 적용]
  -> FocusBlocker.check_and_block() [시간대 내 최소화]
```

### 5. Logs & Import/Export

```
ActivityLogGenerator
  -> daily/*.log + recent.log (+ monthly on demand)
ImportExportManager
  -> DB backup/restore, rule JSON import/export
```

---

## Technical Notes

### Thread Safety
- DatabaseManager: thread-local SQLite connections, WAL mode
- ChromeURLReceiver: lock으로 latest_data 보호
- MonitorEngineThread: 독립 스레드 루프
- NotificationManager: 사운드는 별도 스레드

### Toast Requirements
- Library: `windows-toasts` (AUMID: `ActivityTracker`)
- Hero image: 2:1 비율로 리사이즈 (364x182)

### App Paths
- Dev: 프로젝트 폴더에 DB/로그 저장
- Build: `%APPDATA%/ActivityTracker` 저장

### Web UI Serving
- Dev mode: Vite dev server (`--dev` → http://localhost:5173)
- Prod: FastAPI에서 `webui/dist` 정적 서빙

---

## Tech Stack

**Backend:**
- Python 3.x, SQLite3 (WAL)
- FastAPI, Uvicorn, websockets
- threading, asyncio
- ctypes (Windows API), psutil
- windows-toasts, winsound, pystray
- pywebview (EdgeChromium)

**Frontend:**
- Svelte + Vite, svelte-spa-router
- Chart.js

**Chrome Extension:**
- Manifest V3, WebSocket

**Build:**
- PyInstaller
