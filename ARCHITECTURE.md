# 활동 추적 시스템 V2 - 아키텍처

## 개요
PC 활동(활성 창, Chrome URL, 화면 잠금 등)을 실시간 추적하여 태그별로 자동 분류하고 통계를 시각화하는 데스크톱 애플리케이션

**핵심 기능:**
- 2초 간격 실시간 활동 모니터링
- Chrome URL 추적 (WebSocket 기반 확장 프로그램)
- 우선순위 기반 자동 태그 분류
- 태그별 데스크톱 알림 (커스텀 사운드 지원)
- 대시보드/타임라인 UI
- 시스템 트레이 백그라운드 실행
- 데이터 Import/Export

---

## 전체 구조

```
┌─────────────────────────────────────────────────────┐
│              PyQt6 Frontend                          │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │Dashboard │Timeline  │Tag Mgmt  │  Settings    │  │
│  │   Tab    │   Tab    │   Tab    │    Tab       │  │
│  └──────────┴──────────┴──────────┴──────────────┘  │
│                    + SystemTrayIcon                  │
└─────────────────────┬────────────────────────────────┘
                      │ (Qt Signals)
┌─────────────────────▼────────────────────────────────┐
│              Backend Core                             │
│  ┌─────────────────────────────────────────────────┐ │
│  │  MonitorEngine (QThread)                        │ │
│  │  ├─ WindowTracker (ctypes + psutil)             │ │
│  │  ├─ ScreenDetector (lock/idle 감지)             │ │
│  │  ├─ ChromeURLReceiver (WebSocket 서버)          │ │
│  │  └─ NotificationManager (데스크톱 알림)          │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  RuleEngine (우선순위 기반 룰 매칭)              │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  DatabaseManager (Thread-safe SQLite)           │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  ImportExportManager (백업/복원, 룰 Import)     │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│              SQLite Database (WAL)                    │
│  - tags, activities, rules, settings, alert_sounds   │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│      Chrome Extension (Manifest V3)                   │
│  - WebSocket 클라이언트 (ws://localhost:8766)         │
│  - 활성 탭 URL/프로필 전송 + 자동 재연결              │
└──────────────────────────────────────────────────────┘
```

---

## 데이터베이스 스키마

### 1. `tags` - 태그 정의
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    alert_enabled BOOLEAN DEFAULT 0,  -- 알림 활성화
    alert_message TEXT,               -- 커스텀 알림 메시지
    alert_cooldown INTEGER DEFAULT 30, -- 알림 쿨다운(초)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**기본 태그:** 업무(#4CAF50), 딴짓(#FF5722), 자리비움(#9E9E9E), 미분류(#607D8B)

### 2. `activities` - 활동 기록
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,           -- NULL = 진행 중
    process_name TEXT,            -- "chrome.exe", "__LOCKED__", "__IDLE__"
    window_title TEXT,
    chrome_url TEXT,
    chrome_profile TEXT,
    tag_id INTEGER,               -- FK: tags(id)
    rule_id INTEGER,              -- FK: rules(id)
    created_at TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL,
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE SET NULL
);
```
- `start_time ~ end_time` 구간 저장으로 정확한 시간 계산
- 특수 상태: `__LOCKED__` (화면 잠금), `__IDLE__` (5분 이상 미사용)

### 3. `rules` - 자동 분류 룰
```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority INTEGER DEFAULT 0,      -- 높을수록 우선 적용
    enabled BOOLEAN DEFAULT 1,
    process_pattern TEXT,            -- "chrome.exe,firefox.exe"
    url_pattern TEXT,                -- "*youtube.com*,*netflix.com*"
    window_title_pattern TEXT,
    chrome_profile TEXT,
    process_path_pattern TEXT,       -- 프로세스 경로 패턴
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```
- 우선순위 기반 순차 매칭, 조건 간 OR 관계
- 와일드카드(`*`, `?`) + 쉼표 구분 다중 패턴 지원

### 4. `settings` - 전역 설정
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### 5. `alert_sounds` - 알림음 목록
```sql
CREATE TABLE alert_sounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP
);
```

---

## 디렉토리 구조

```
PC_ScreenCapture_V2/
├── main.py                      # 애플리케이션 진입점
├── requirements.txt
│
├── backend/                     # 백엔드 모듈
│   ├── config.py                # 경로/설정 관리 (dev vs build)
│   ├── database.py              # SQLite 매니저 (thread-safe)
│   ├── monitor_engine.py        # 모니터링 루프 (QThread)
│   ├── window_tracker.py        # 활성 창 감지 (ctypes)
│   ├── screen_detector.py       # 잠금/idle 감지
│   ├── chrome_receiver.py       # WebSocket 서버 (asyncio)
│   ├── rule_engine.py           # 룰 매칭 엔진
│   ├── notification_manager.py  # 데스크톱 알림 (winotify)
│   ├── import_export.py         # DB/룰 Import/Export
│   └── auto_start.py            # Windows 자동 시작 관리
│
├── ui/                          # PyQt6 UI
│   ├── main_window.py           # 메인 윈도우 + 탭 구조
│   ├── dashboard_tab.py         # 통계 대시보드
│   ├── timeline_tab.py          # 활동 타임라인
│   ├── tag_management_tab.py    # 태그/룰 관리
│   ├── settings_tab.py          # 일반 설정 + 데이터 관리
│   ├── date_navigation_widget.py # 날짜 선택 위젯 (재사용)
│   ├── tray_icon.py             # 시스템 트레이
│   └── styles.py                # 다크 테마 QSS
│
├── chrome_extension/            # Chrome 확장 (Manifest V3)
│   ├── manifest.json
│   ├── background.js            # Service Worker
│   ├── popup.html/js            # 프로필 설정 팝업
│   └── 설치방법.txt
│
└── reference/                   # 테스트/참고 파일
```

---

## 백엔드 모듈

### `backend/config.py` - 설정 및 경로 관리
- 개발 모드 (`sys.frozen` 체크): 프로젝트 폴더에 DB/설정 저장
- 빌드 모드: `%APPDATA%/ActivityTracker`에 저장
- `get_db_path()`, `get_sounds_dir()` 등 경로 유틸리티

### `backend/database.py` - DatabaseManager
```python
class DatabaseManager:
    def __init__(self, db_path=None):
        self._local = threading.local()  # 스레드별 connection
        self.init_database()

    @property
    def conn(self):
        # 스레드별 독립 연결 반환 (WAL 모드)
```

**주요 메서드:**
- **태그**: `get_all_tags()`, `create_tag()`, `update_tag()`, `delete_tag()`
- **활동**: `create_activity()`, `end_activity()`, `get_activities()`, `get_timeline()`
- **룰**: `get_all_rules()`, `create_rule()`, `update_rule()`, `delete_rule()`
- **통계**: `get_stats_by_tag()`, `get_stats_by_process()`
- **설정**: `get_setting()`, `set_setting()`
- **알림음**: `get_all_alert_sounds()`, `add_alert_sound()`, `delete_alert_sound()`
- **유틸**: `cleanup_unfinished_activities()`, `get_unclassified_activities()`

### `backend/monitor_engine.py` - MonitorEngine (QThread)
```python
class MonitorEngine(QThread):
    activity_detected = pyqtSignal(dict)
    IDLE_THRESHOLD = 300  # 5분

    def run(self):
        while self.running:
            activity_info = self.collect_activity_info()
            if self._is_activity_changed(activity_info):
                self.end_current_activity()
                self.start_new_activity(activity_info)
            time.sleep(2)
```

**활동 수집 우선순위:**
1. `is_locked()` → `__LOCKED__`
2. `get_idle_duration() > 300` → `__IDLE__`
3. 일반 활동 → WindowTracker + ChromeURLReceiver

**알림 처리:**
- 새 활동 시작 시 `_check_tag_alert(tag_id)` 호출
- 태그에 `alert_enabled` 설정되어 있으면 NotificationManager로 알림 표시

### `backend/window_tracker.py` - WindowTracker
```python
def get_active_window(self):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    # GetWindowTextW → window_title
    # GetWindowThreadProcessId → pid → psutil.Process → process_name, process_path
```

### `backend/screen_detector.py` - ScreenDetector
- `is_locked()`: `OpenInputDesktop()` → 0이면 잠금 상태
- `get_idle_duration()`: `GetLastInputInfo()` → 마지막 입력 후 경과 시간(초)

### `backend/rule_engine.py` - RuleEngine
```python
class RuleEngine:
    def match(self, activity_info) -> Tuple[tag_id, rule_id]:
        for rule in self.rules_cache:  # priority DESC 정렬
            if self._is_matched(rule, activity_info):
                return rule['tag_id'], rule['id']
        return unclassified_tag_id, None

    def _is_matched(self, rule, info) -> bool:
        # OR 관계: process_pattern, url_pattern, window_title_pattern,
        #          chrome_profile, process_path_pattern 중 하나 매치 시 True
        # fnmatch로 와일드카드 처리, 쉼표로 다중 패턴 지원
```

### `backend/chrome_receiver.py` - ChromeURLReceiver
- 별도 데몬 스레드에서 asyncio WebSocket 서버 실행 (port=8766)
- Chrome Extension에서 `url_change` 메시지 수신 → `latest_data` 저장
- `threading.Lock`으로 데이터 경합 방지

### `backend/notification_manager.py` - NotificationManager
```python
class NotificationManager:
    DEFAULT_COOLDOWN = 30

    def show(self, tag_id, title, message, cooldown=None):
        if self._can_notify(tag_id, cooldown):  # 쿨다운 체크
            # winotify로 토스트 알림 (별도 스레드)
            # 커스텀 사운드 재생 (winsound)
```

**사운드 재생 모드:**
- `single`: 선택된 사운드만 재생
- `random`: 등록된 사운드 중 랜덤 선택

### `backend/import_export.py` - ImportExportManager
```python
class ImportExportManager:
    def export_database(backup_path)  # SQLite 파일 복사
    def import_database(backup_path)  # 앱 재시작 필요
    def export_rules(json_path)       # 태그+룰 JSON 저장
    def import_rules(json_path, merge_mode)  # merge=True: 기존 유지+추가
```

---

## 프론트엔드 (PyQt6)

### `ui/main_window.py` - MainWindow
```python
class MainWindow(QMainWindow):
    def create_tabs(self):
        self.tabs.addTab(DashboardTab(self.db_manager), "📊 대시보드")
        self.tabs.addTab(TimelineTab(self.db_manager, self.monitor_engine), "⏱️ 타임라인")
        self.tabs.addTab(TagManagementTab(self.db_manager, self.rule_engine), "🏷️ 태그 관리")
        self.tabs.addTab(SettingsTab(self.db_manager, self.rule_engine), "⚙️ 설정")

    def closeEvent(self, event):
        # Shift+닫기 = 종료, 일반 닫기 = 트레이 최소화
```

### `ui/dashboard_tab.py` - DashboardTab
- 날짜 선택 (DateNavigationWidget)
- 태그별 통계 카드 (진행률 바 + 사용 시간)
- matplotlib 파이 차트
- 프로세스 TOP 5 테이블
- 10초 자동 갱신

### `ui/timeline_tab.py` - TimelineTab
- 날짜/태그 필터링
- QTableWidget 기반 테이블 뷰
- 태그 셀 배경색 표시
- 우클릭 → 태그 수동 변경
- MonitorEngine 시그널 연결 → 실시간 업데이트

### `ui/tag_management_tab.py` - TagManagementTab
**태그 관리:**
- 추가/수정/삭제 (QColorDialog)
- 알림 설정: 활성화, 메시지, 쿨다운

**룰 관리:**
- 추가/수정/삭제
- 우선순위, 조건 패턴, 태그 선택
- 변경 시 `rule_engine.reload_rules()` 호출

### `ui/settings_tab.py` - SettingsTab
**일반 설정:**
- Windows 자동 시작
- 미분류 재분류 버튼

**알림음 설정:**
- 알림음 사용 체크박스
- 랜덤/단일 재생 모드
- 사운드 목록 관리 (추가/삭제/테스트)
- MP3 → WAV 자동 변환 (imageio-ffmpeg)

**데이터 관리:**
- DB 전체 백업/복원
- 룰 Import/Export (JSON)

### `ui/date_navigation_widget.py` - DateNavigationWidget
- 재사용 가능한 날짜 선택 위젯
- QDateEdit + 오늘/이전/다음 버튼
- `date_changed` 시그널

---

## Chrome Extension (Manifest V3)

### `manifest.json`
```json
{
  "manifest_version": 3,
  "permissions": ["tabs", "webNavigation", "storage"],
  "background": { "service_worker": "background.js" },
  "action": { "default_popup": "popup.html" }
}
```

### `background.js` - Service Worker
```javascript
// WebSocket 연결 관리 (ws://localhost:8766)
function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8766');
  ws.onclose = () => setTimeout(connectWebSocket, 5000);  // 자동 재연결
}

// 탭 이벤트 감지 (활성 탭만)
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.title) {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (activeTab && activeTab.id === tabId)
      sendUrlToServer(tabId, tab.url, tab.title);
  }
});

chrome.tabs.onActivated.addListener(/* ... */);
chrome.windows.onFocusChanged.addListener(/* ... */);

function sendUrlToServer(tabId, url, title) {
  ws.send(JSON.stringify({
    type: 'url_change',
    profileName: profileName,
    tabId, url, title, timestamp: Date.now()
  }));
}
```

### `popup.html/js` - 프로필 설정
- 프로필명 입력 및 저장 (`chrome.storage.local`)
- background.js에 `profile_updated` 메시지 전송

---

## 데이터 흐름

### 1. 활동 추적 루프 (2초마다)
```
MonitorEngine.run()
  → collect_activity_info()
    ├─ is_locked() → __LOCKED__?
    ├─ get_idle_duration() > 300 → __IDLE__?
    └─ get_active_window() + get_latest_url()
  → is_activity_changed() 체크
    → YES: end_current_activity() + start_new_activity()
      → rule_engine.match() → tag_id, rule_id
      → db_manager.create_activity()
      → _check_tag_alert() → 알림 표시
      → emit activity_detected signal → UI 업데이트
```

### 2. Chrome URL 전송
```
Chrome Extension
  → tabs.onActivated / onUpdated / windows.onFocusChanged
  → sendUrlToServer(tabId, url, title)
    → WebSocket.send(JSON)
      → ChromeURLReceiver._handler()
        → latest_data 업데이트 (Lock 보호)
          → MonitorEngine.collect_activity_info()에서 참조
```

### 3. 룰 변경
```
TagManagementTab
  → 룰 추가/수정/삭제 → db_manager.create/update/delete_rule()
  → rule_engine.reload_rules()
    → rules_cache 갱신 → 다음 활동부터 새 룰 적용
```

---

## 핵심 설계 원칙

### 스레드 안전성
- **DatabaseManager**: `threading.local`로 스레드별 연결 분리
- **ChromeURLReceiver**: `threading.Lock`으로 데이터 보호
- **MonitorEngine**: QThread로 메인 UI와 격리
- **NotificationManager**: 별도 스레드에서 알림 표시

### 느슨한 결합
- Backend 모듈은 UI 의존성 없음 (헤드리스 실행 가능)
- Qt Signal/Slot으로 UI 업데이트 전달
- RuleEngine은 DB만 참조, 다른 모듈과 독립

### 확장 가능성
- 태그/룰 시스템으로 무한한 분류 가능
- 우선순위 기반 룰 매칭으로 복잡한 조건 표현
- 쉼표 구분 패턴으로 한 룰에 여러 조건 통합
- 프로세스 경로 패턴으로 동일 이름 프로세스 구분

---

## 기술 스택

**Backend:**
- Python 3.x, SQLite3 (WAL), threading, asyncio + websockets
- ctypes (Windows API), psutil, winotify, winsound

**Frontend:**
- PyQt6, matplotlib, QSS

**Chrome Extension:**
- Manifest V3, Service Worker, chrome.tabs/storage API, WebSocket

**빌드:**
- PyInstaller, Windows Registry (자동 시작)
- imageio-ffmpeg (MP3 → WAV 변환)
