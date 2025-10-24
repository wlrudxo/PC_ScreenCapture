# ScreenCapture - 프로젝트 구조 문서

## 📁 프로젝트 디렉토리 구조

```
ScreenCapture/
├── CORE APPLICATION FILES
│   ├── run.py                    # 통합 실행 진입점 (5KB)
│   ├── capture.py                # 화면 캡처 모듈 (8.6KB)
│   ├── viewer.py                 # Flask 웹 서버 + API (20KB)
│   ├── database.py               # SQLite 데이터베이스 관리 (13KB)
│   └── config.json               # 설정 파일 (1KB)
│
├── DOCUMENTATION
│   ├── ARCHITECTURE.md           # 이 문서 (시스템 구조)
│   ├── REFACTORING.md            # 리팩토링 계획 및 체크리스트 (31KB)
│   ├── README.md                 # 프로젝트 개요 (8KB)
│   └── CLAUDE.md                 # AI 어시스턴트 가이드 (6KB)
│
├── MIGRATION SCRIPTS
│   ├── migration.py              # 데이터베이스 마이그레이션 도구 (5KB)
│   ├── migration.sql             # SQL 스키마 변경 스크립트 (3KB)
│   ├── migrate_with_matching.py  # 고급 마이그레이션 (5KB)
│   └── test_migration.py         # 마이그레이션 테스트 (3KB)
│
├── TEMPLATES/ (HTML)
│   ├── timeline.html             # 타임라인 페이지 + 이미지 모달 (4.8KB)
│   ├── stats.html                # 통계 대시보드 (2.6KB)
│   └── settings.html             # 설정 페이지 (5.2KB)
│
├── STATIC/ (Frontend Assets)
│   ├── app.js                    # JavaScript 로직 (45KB, 1,330 lines)
│   └── style.css                 # CSS 스타일 (19KB)
│
├── DATA/ (Runtime)
│   ├── activity.db               # SQLite 데이터베이스
│   └── screenshots/              # 캡처된 이미지
│       └── 2025-10-23/           # 날짜별 폴더
│           ├── 11-25-21_m1.jpg   # 모니터 1
│           ├── 11-25-21_m2.jpg   # 모니터 2
│           └── ...
│
├── .git/                         # Git 저장소
├── .gitignore
├── __pycache__/                  # Python 캐시
└── requirements.txt              # 패키지 의존성
```

---

## 🔧 핵심 모듈 설명

### 1. run.py - 통합 실행 스크립트

**역할**: 모든 구성 요소를 통합 실행하는 메인 진입점

**주요 기능**:
- 캡처 인스턴스 생성 및 초기화
- 캡처 스레드 실행 (백그라운드)
- Flask 웹 서버 스레드 실행 (백그라운드)
- 예약 종료 체크 스레드 실행
- 시스템 트레이 아이콘 생성 및 관리
- 자동 브라우저 열기 (2초 후)

**실행 방법**:
```bash
python run.py
```

**스레드 구조**:
```
main thread (시스템 트레이)
  ├── capture_thread (백그라운드 캡처)
  ├── flask_thread (웹 서버)
  ├── scheduled_thread (예약 종료 체크)
  └── browser_thread (브라우저 자동 열기)
```

---

### 2. capture.py - 화면 캡처 모듈

**역할**: 멀티모니터 화면을 주기적으로 캡처

**클래스**: `ScreenCapture`

**주요 메서드**:
- `__init__(config_path)`: 설정 로드 및 초기화
- `capture_all_monitors()`: 모든 모니터 캡처 (mss 사용)
- `start_capture_loop()`: 주기적 캡처 루프 (블로킹)
- `stop_capture()`: 캡처 중지
- `pause_capture()`: 캡처 일시정지
- `resume_capture()`: 캡처 재개
- `is_screen_locked()`: Windows 화면 잠금 감지
- `is_black_screen()`: 검은 화면 감지 (잠금 화면 방지)

**캡처 프로세스**:
```
1. 화면 잠금 체크 (is_screen_locked + is_black_screen)
   → 잠금 상태면 캡처 건너뜀
2. 현재 시간 획득
3. 날짜별 폴더 생성 (data/screenshots/YYYY-MM-DD/)
4. 각 모니터 순회:
   - mss로 스크린샷 캡처
   - PIL로 JPEG 변환 (config에서 품질 설정)
   - 파일명: HH-MM-SS_m{N}.jpg
   - 파일 저장
   - DB에 레코드 추가 (capture_id 자동 생성)
5. 설정된 간격(분) 대기
6. 예약 종료 시간 체크
7. 반복
```

**설정 파라미터**:
- `interval_minutes`: 캡처 간격 (기본 3분)
- `image_quality`: JPEG 품질 50-100 (현재: 50)
- `screenshots_dir`: 저장 경로

---

### 3. viewer.py - Flask 웹 서버 및 API

**역할**: 웹 UI 제공 및 REST API 엔드포인트

#### 웹 페이지 라우트

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | timeline.html | 타임라인 (메인 페이지) |
| `/stats` | stats.html | 통계 대시보드 |
| `/settings` | settings.html | 설정 페이지 |

#### API 엔드포인트

**캡처 관련**:
- `GET /api/dates` - 캡처된 날짜 목록
- `GET /api/captures/<date>` - 특정 날짜의 캡처 목록 (**capture_id 포함**)
- `GET /screenshots/<path>` - 이미지 파일 제공
- `POST /api/captures/delete` - **ID 기반 일괄 삭제 (NEW)**

**태그 관련**:
- `GET /api/tags/<date>` - 특정 날짜의 태그 목록 (**capture_id 포함**)
- `POST /api/tags` - 새 태그 추가 (**capture_id 기반**)
- `GET /api/categories` - 카테고리 목록

**통계 관련**:
- `GET /api/stats/category?start_date=&end_date=` - 카테고리별 통계 (미분류 포함)
- `GET /api/stats/activity?start_date=&end_date=` - 활동별 통계 (미분류 포함)

**설정 관련**:
- `GET /api/status` - 현재 캡처 상태
- `POST /api/control/pause` - 캡처 일시정지
- `POST /api/control/resume` - 캡처 재개
- `POST /api/control/capture` - 수동 캡처
- `GET /api/config` - 현재 설정 조회
- `POST /api/config` - 설정 업데이트
- `POST /api/scheduled-stop` - 예약 종료 설정
- `DELETE /api/scheduled-stop` - 예약 종료 취소
- `GET /api/storage` - 저장 공간 정보
- `POST /api/storage/delete-all` - 모든 이미지 삭제

#### 주요 API 변경사항 (v2.0)

**GET /api/captures/<date>** (Lines 67-107):
```json
{
  "success": true,
  "captures": [
    {
      "timestamp": "2025-10-24 15:01:08",
      "capture_id": 123,              // NEW: 대표 ID (첫 모니터)
      "monitors": {
        "m1": {
          "id": 123,
          "filepath": "/path/to/image.jpg",  // null if deleted
          "monitor_num": 1,
          "deleted_at": null                 // NEW: 삭제 시간
        },
        "m2": {
          "id": 124,
          "filepath": null,                  // 삭제됨
          "monitor_num": 2,
          "deleted_at": "2025-10-24 15:30:00"
        }
      }
    }
  ]
}
```

**POST /api/tags** (Lines 122-181):
```json
// Request
{
  "capture_id": 123,        // ID 기반 (타임스탬프 제거)
  "category": "연구",
  "activity": "코딩"
  // duration_min은 서버에서 자동 계산
}
```

**POST /api/captures/delete** (Lines 307-359):
```json
// Request
{
  "capture_ids": [123, 124, 125]  // ID 배열 (타임스탬프 제거)
}
```

**미분류 시간 계산 로직**:
```python
# 전체 캡처 시간 = 캡처 수 × 간격
total_minutes = total_captures × interval_minutes

# 태그된 시간 합계
tagged_minutes = sum(all_tags.duration)

# 미분류 시간
untagged_minutes = total_minutes - tagged_minutes
```

---

### 4. database.py - 데이터베이스 관리

**역할**: SQLite 데이터베이스 추상화 계층

**클래스**: `Database`

#### 테이블 스키마 (v2.0 - 리팩토링됨)

**captures** - 캡처된 스크린샷 로그
```sql
CREATE TABLE captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    monitor_num INTEGER NOT NULL,
    filepath TEXT,                     -- NULL 허용 (v2.0 변경)
    deleted_at DATETIME                -- NEW: Soft delete 시간
);

CREATE INDEX idx_captures_timestamp ON captures(timestamp);
CREATE INDEX idx_captures_deleted_at ON captures(deleted_at);  -- NEW
CREATE UNIQUE INDEX idx_captures_unique ON captures(timestamp, monitor_num);  -- NEW
```

**주요 변경사항**:
- `filepath`: `NOT NULL` → `NULL` 허용 (삭제 시 NULL)
- `deleted_at`: Soft delete 타임스탬프 추가
- Unique 인덱스: 중복 캡처 방지

**tags** - 활동 태그 로그
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,       -- 시작 시간
    category TEXT NOT NULL,            -- 카테고리 (연구, 행정, 개인, 기타)
    activity TEXT NOT NULL,            -- 활동 (코딩, 메일 등)
    duration_min INTEGER NOT NULL,     -- 지속 시간 (분)
    capture_id INTEGER                 -- NEW: FK to captures.id
);

CREATE INDEX idx_tags_timestamp ON tags(timestamp);
CREATE INDEX idx_tags_capture_id ON tags(capture_id);  -- NEW
```

**주요 변경사항**:
- `capture_id`: 외래키 추가 (captures.id 참조)
- 인덱스: capture_id 기반 조회 최적화

**categories** - 카테고리 정의
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    activities TEXT NOT NULL  -- JSON array
);
```

#### 주요 메서드

**Captures**:
- `add_capture(timestamp, monitor_num, filepath)`: 캡처 추가
- `get_captures_by_date(date)`: 날짜별 캡처 조회 (deleted_at 포함)
- `get_captures_by_time_range(start, end)`: 시간 범위별 캡처 조회
- `delete_captures_by_time_range(start, end)`: 시간 범위별 삭제 (레거시)
- **`get_capture_by_id(capture_id)` (NEW)**: ID로 직접 조회
- **`mark_capture_deleted(capture_id)` (NEW)**: Soft delete (filepath=NULL, deleted_at=NOW)

**Tags**:
- `add_tag(timestamp, category, activity, duration_min, capture_id)`: 태그 추가 (**capture_id 파라미터 추가**)
- `get_tags_by_date(date)`: 날짜별 태그 조회
- `get_tags_by_date_range(start_date, end_date)`: 기간별 태그 조회
- `get_category_stats(start_date, end_date)`: 카테고리별 통계
- `get_activity_stats(start_date, end_date)`: 활동별 통계

**Categories**:
- `init_categories(categories)`: 카테고리 초기화 (config.json에서)
- `get_categories()`: 모든 카테고리 조회

**성능 개선**:
| 작업 | v1.0 (타임스탬프) | v2.0 (ID 기반) | 개선율 |
|------|------------------|----------------|--------|
| 태그 추가 | String 비교 | Integer 인덱스 | 10-100배 |
| 삭제 처리 | 루프 + 파싱 | 단일 쿼리 | 50배 |
| FK 조회 | 불가능 | O(log n) | - |

---

## 🎨 프론트엔드 구조

### templates/timeline.html - 타임라인 페이지

**구조**:
```html
navbar
  └─ 타임라인 / 통계 / 설정

container
  ├─ sidebar (날짜 목록)
  │    └─ date-list (클릭 시 selectDate)
  └─ main-content
       ├─ header (선택된 날짜)
       ├─ filter-buttons (전체/태그됨/미태그)  -- NEW
       ├─ bulk-controls (일괄 작업)            -- NEW
       └─ capture-grid (세로 리스트)
            └─ capture-item (각 캡처)
                 ├─ checkbox (선택)             -- NEW
                 ├─ capture-time (시간)
                 ├─ monitor-images (클릭 시 모달)  -- UPDATED
                 └─ capture-tagging (카테고리/활동)

modal (이미지 세부 확인)  -- NEW
  ├─ modal-header (날짜 + 시간)
  ├─ modal-images (큰 이미지)
  ├─ modal-navigation (이전/다음)
  └─ modal-tagging (카테고리/활동 선택)
```

**새로운 기능 (v2.0)**:
1. **이미지 모달 뷰어** (Lines 71-102):
   - 이미지 클릭 시 전체화면 모달
   - 이전/다음 네비게이션 버튼
   - 키보드 단축키 (화살표, ESC)
   - 모달 내에서 직접 태깅 가능
   - 태깅 후 자동으로 다음 캡처로 이동

2. **필터링**: 전체/태그됨/미태그 필터
3. **페이지네이션**: 20개씩 표시
4. **일괄 작업**: 체크박스로 다중 선택 → 태깅/삭제

**인라인 태깅 플로우**:
```
1. 카테고리 선택
   → selectCategory(captureId, category)  // ID 기반
   → 활동 버튼 활성화

2. 활동 선택
   → selectActivity(captureId, category, activity)
   → API POST /api/tags { capture_id: 123, ... }
   → 성공 시 초록색 하이라이트
   → allTags 배열 업데이트
```

**모달 태깅 플로우** (NEW):
```
1. 이미지 클릭
   → openCaptureModal(captureId)
   → 모달 오픈 + 해당 캡처 표시

2. 카테고리/활동 선택
   → selectModalActivity(category, activity)
   → API 호출
   → 자동으로 다음 캡처로 이동 (또는 마지막이면 닫기)

3. 키보드 네비게이션
   → Arrow Left: 이전 캡처
   → Arrow Right: 다음 캡처
   → ESC: 모달 닫기
```

---

### templates/stats.html - 통계 페이지

**레이아웃** (2열):
```
┌─────────────────────────────────────┐
│  활동 통계 헤더 (날짜 선택)           │
├──────────────────┬──────────────────┤
│ 카테고리별       │                  │
│ 시간 분포        │                  │
│ (Pie Chart)      │   상세 내역      │
├──────────────────┤   (Table)        │
│ 활동별           │                  │
│ 시간 사용량      │                  │
│ (Bar Chart)      │                  │
└──────────────────┴──────────────────┘
```

**CSS 그리드 구조**:
```css
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;  /* 좌우 2열 */
}
```

**차트 렌더링** (Chart.js):
- 카테고리별 색상 매핑:
  - 연구: `#4CAF50` (초록)
  - 행정: `#2196F3` (파랑)
  - 개인: `#FF9800` (주황)
  - 기타: `#9E9E9E` (회색)
  - 미분류: `#E0E0E0` (연회색)

---

### templates/settings.html - 설정 페이지

**섹션 구성**:
1. **캡처 상태** - 실시간 상태 표시, 일시정지/재개, 즉시 캡처
2. **캡처 설정** - 간격, 품질, 자동 삭제 옵션
3. **예약 종료** - 특정 시간에 자동 종료
4. **저장 공간** - 총 캡처 수, 용량 표시
5. **위험 구역** - 모든 이미지 삭제

**실시간 업데이트**:
- 3초마다 `GET /api/status` 호출
- 캡처 상태 업데이트
- 예약 종료 정보 표시

---

### static/app.js - JavaScript 로직 (1,330 lines)

**페이지별 초기화**:
```javascript
DOMContentLoaded
  ├─ timeline → initTimeline()
  ├─ stats → initStats()
  └─ settings → initSettings()
```

**주요 함수 매핑**:

| 섹션 | Lines | 기능 | v2.0 변경사항 |
|------|-------|------|--------------|
| **Global State** | 1-8 | 전역 변수 | - |
| **Timeline** | 31-323 | 타임라인 렌더링 | `data-capture-id` 사용 |
| renderCaptures | 246-323 | 캡처 렌더링 | ID 기반, null 체크 |
| **Modal Viewer** | **325-553** | **이미지 상세 모달** | **NEW** |
| openCaptureModal | 330-356 | 모달 열기 | NEW |
| showModal | 358-425 | 모달 표시 | NEW |
| navigateModal | 433-447 | 이전/다음 | NEW |
| selectModalActivity | 472-539 | 모달 태깅 | NEW |
| handleModalKeyboard | 541-553 | 키보드 제어 | NEW |
| **Inline Tagging** | 555-654 | 인라인 태깅 | capture_id 사용 |
| selectCategory | 557-597 | 카테고리 선택 | ID 파라미터 |
| selectActivity | 599-654 | 활동 선택 저장 | capture_id POST |
| **Bulk Operations** | 680-881 | 일괄 작업 | capture_ids 배열 |
| bulkSaveTags | 761-833 | 일괄 태깅 | ID 기반 |
| bulkDeleteCaptures | 835-881 | 일괄 삭제 | capture_ids POST |
| **Statistics** | 883-1071 | 통계 차트 | - |
| **Settings** | 1073-1331 | 설정 관리 | - |

**주요 변경사항 (v1.0 → v2.0)**:

| 항목 | v1.0 | v2.0 |
|------|------|------|
| 식별자 | `data-index="${index}"` | `data-capture-id="${captureId}"` |
| 태그맵 키 | `tagMap[timestamp]` | `tagMap[capture_id]` |
| API 요청 | `{ start_time, end_time }` | `{ capture_id }` |
| 삭제 체크 | `filepath === 'DELETED'` | `filepath === null` |
| 선택자 | `querySelector('[data-index]')` | `querySelector('[data-capture-id]')` |

**모달 뷰어 특징** (NEW):
- **전체화면 이미지**: 더 큰 해상도로 확인
- **빠른 네비게이션**: 버튼 + 키보드
- **인라인 태깅**: 모달 닫지 않고 태깅
- **자동 진행**: 태깅 후 다음 미태그 캡처로 자동 이동
- **반응형**: 단일/듀얼 모니터 모두 지원

---

### static/style.css - 스타일시트

**주요 레이아웃**:
```css
/* 타임라인 페이지 */
.container {
    display: flex;  /* 사이드바 + 메인 */
}

.capture-grid {
    display: flex;
    flex-direction: column;  /* 세로 리스트 */
}

.capture-item {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    /* 체크박스 | 시간 | 모니터1 모니터2 | 드롭다운 */
}

/* 이미지 모달 (NEW) */
.capture-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    z-index: 9999;
}

.modal-images img {
    max-height: 70vh;
    cursor: pointer;
}

/* 통계 페이지 */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;  /* 2열 */
}

/* 설정 페이지 */
.settings-page {
    padding: 2rem;
    max-width: 800px;
    margin: 0 auto;
}
```

**반응형**:
- 모니터 이미지: `max-height: 200px` (인라인), `70vh` (모달)
- 차트: `max-height: 300px`
- 전체 페이지: `max-width: 1000px` (통계/설정)

---

## ⚙️ 설정 파일 (config.json)

```json
{
  "capture": {
    "interval_minutes": 3,           // 캡처 간격 (분)
    "image_quality": 50,             // JPEG 품질 (50-100, 현재 50)
    "format": "JPEG"                 // 이미지 포맷
  },
  "storage": {
    "screenshots_dir": "./data/screenshots",
    "database_path": "./data/activity.db",
    "auto_delete_after_tagging": true  // 태깅 후 자동 삭제 (현재 활성화)
  },
  "viewer": {
    "port": 5000,                    // Flask 서버 포트
    "thumbnail_size": [320, 180]     // 썸네일 크기
  },
  "categories": [
    {
      "name": "연구",
      "color": "#4CAF50",
      "activities": ["코딩", "자료 조사", "논문 작성", "PPT 제작", "공부"]
    },
    {
      "name": "행정",
      "color": "#2196F3",
      "activities": ["메일", "서류 작성", "영수증 처리"]
    },
    {
      "name": "개인",
      "color": "#FF9800",
      "activities": ["언어 공부", "앱 개발", "인터넷", "유튜브"]
    },
    {
      "name": "기타",
      "color": "#9E9E9E",
      "activities": ["자리 비움"]
    }
  ]
}
```

---

## 🔄 데이터 플로우

### 캡처 플로우
```
capture.py (캡처 스레드)
  ↓
화면 잠금 체크 (is_screen_locked + is_black_screen)
  ↓
mss.grab() → PIL.Image → JPEG 저장
  ↓
database.add_capture(timestamp, monitor_num, filepath)
  ↓
SQLite (captures 테이블) - capture_id 자동 생성
```

### 태깅 플로우 (v2.0)
```
사용자 (카테고리/활동 선택)
  ↓
app.js: selectActivity(captureId, category, activity)
  ↓
POST /api/tags { capture_id: 123, category, activity }
  ↓
viewer.py: add_tag()
  ├─ get_capture_by_id(capture_id) → timestamp 조회
  ├─ duration = config['interval_minutes']
  └─ database.add_tag(timestamp, category, activity, duration, capture_id)
  ↓
SQLite (tags 테이블) - capture_id FK 저장
  ↓
[자동 삭제 옵션 ON]
  ↓
database.mark_capture_deleted(capture_id)
  ├─ UPDATE captures SET filepath=NULL, deleted_at=NOW
  └─ WHERE timestamp = (SELECT timestamp FROM captures WHERE id=capture_id)
  ↓
파일 시스템에서 이미지 삭제 (os.remove)
```

### 삭제 플로우 (v2.0)
```
사용자 (체크박스 선택 + 삭제 버튼)
  ↓
app.js: bulkDeleteCaptures()
  ├─ capture_ids = [123, 124, 125]
  └─ POST /api/captures/delete { capture_ids }
  ↓
viewer.py: delete_captures()
  └─ for capture_id in capture_ids:
       ├─ get_capture_by_id(capture_id)
       ├─ os.remove(filepath) for all monitors
       └─ mark_capture_deleted(capture_id)
  ↓
SQLite (filepath=NULL, deleted_at=NOW)
```

### 통계 조회 플로우
```
사용자 (기간 선택 + 조회)
  ↓
app.js: loadStats()
  ↓
GET /api/stats/category?start_date=2025-10-01&end_date=2025-10-31
GET /api/stats/activity?start_date=2025-10-01&end_date=2025-10-31
  ↓
viewer.py: get_category_stats()
  ├─ database.get_category_stats() (태그된 시간)
  ├─ database.get_captures_by_date() (전체 캡처)
  └─ 미분류 계산: (전체 캡처 수 × 간격) - 태그됨
  ↓
JSON 응답
  ↓
app.js: renderCategoryChart() (Pie chart)
         renderActivityChart() (Bar chart)
         renderStatsTable() (HTML table)
  ↓
Chart.js 렌더링
```

---

## 🚀 실행 흐름

### 프로그램 시작
```
1. python run.py 실행
2. main() 함수 진입
3. ScreenCapture 인스턴스 생성
   - config.json 로드
   - Database 초기화 (테이블 생성/카테고리 초기화)
   - 스크린샷 디렉토리 생성
4. 스레드 시작:
   - capture_thread: capture_instance.start_capture_loop()
   - flask_thread: app.run(host='0.0.0.0', port=5000)
   - scheduled_thread: check_scheduled_stop() (1분마다)
   - browser_thread: 2초 후 브라우저 열기
5. 시스템 트레이 아이콘 생성
   - 메뉴: 열기 / 종료
6. pystray.run() 블로킹 (메인 스레드)
```

### 캡처 루프
```
while is_running:
    1. 예약 종료 시간 체크
    2. is_paused 확인
    3. 화면 잠금 체크 (is_screen_locked + is_black_screen)
       → 잠금 상태면 다음 반복으로
    4. capture_all_monitors() 실행
       - 각 모니터 캡처
       - 파일 저장
       - DB 레코드 추가 (capture_id 자동 생성)
    5. interval_minutes × 60초 대기
       (1초 단위로 is_running 체크)
    6. 반복
```

### 웹 요청 처리
```
사용자 → 브라우저 → Flask (포트 5000)
  ├─ GET / → timeline.html
  ├─ GET /api/dates → JSON
  ├─ GET /api/captures/2025-10-24 → JSON (capture_id 포함)
  ├─ POST /api/tags → database.add_tag() (capture_id 사용)
  ├─ POST /api/captures/delete → mark_capture_deleted()
  └─ GET /screenshots/2025-10-24/11-25-21_m1.jpg → send_from_directory()
```

---

## 🛠️ 주요 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| 백엔드 | Python 3.8+ | 메인 언어 |
| 캡처 | mss | 멀티모니터 스크린샷 |
| 이미지 | Pillow | JPEG 변환/압축 |
| 웹 | Flask | 웹 서버 + REST API |
| DB | SQLite | 로컬 데이터베이스 |
| 트레이 | pystray | 시스템 트레이 아이콘 |
| 스케줄 | threading | 멀티스레드 실행 |
| 프론트 | HTML/CSS/JS | 웹 UI (1,330 lines JS) |
| 차트 | Chart.js | 통계 시각화 |
| 타임존 | pytz | 시간대 처리 |

---

## 📊 데이터 크기 추정

**1080p 듀얼 모니터 기준** (JPEG 품질 50):
- 캡처 간격: 3분
- 하루 캡처 수: 480개 (8시간 × 20회/시간)
- 이미지당 크기: ~100KB (JPEG 50%)
- 하루 용량: ~48MB
- 일주일: ~336MB
- 한 달: ~1.4GB

**1080p 듀얼 모니터 기준** (JPEG 품질 85):
- 이미지당 크기: ~200KB
- 하루 용량: ~96MB
- 일주일: ~672MB
- 한 달: ~2.8GB

**4K 듀얼 모니터** (JPEG 품질 50):
- 이미지당 크기: ~400KB
- 하루 용량: ~192MB
- 일주일: ~1.3GB
- 한 달: ~5.6GB

---

## 🔐 보안 및 프라이버시

**로컬 전용**:
- 모든 데이터는 로컬에만 저장
- 외부 서버 전송 없음
- Flask는 0.0.0.0:5000으로 바인드 (로컬 네트워크 접근 가능)

**화면 잠금 감지**:
- Windows API로 잠금 화면 감지 (`is_screen_locked`)
- 검은 화면 감지로 이중 체크 (`is_black_screen`)
- 잠금 시 캡처 건너뜀 (프라이버시 보호)

**데이터 관리**:
- 이미지는 태깅 후 자동 삭제 가능 (`auto_delete_after_tagging`)
- 날짜별 폴더로 구조화
- Soft delete: 태그 정보는 유지 (이미지만 삭제)

---

## 🔄 리팩토링 개선사항 (v2.0)

### 1. Primary Key 기반 아키텍처

**v1.0 문제점**:
- 배열 index 기반 식별 → 페이지네이션/필터링 시 불안정
- 타임스탬프 문자열 매칭 → UTC/로컬 변환 복잡성
- 외래키 없음 → 데이터 무결성 문제

**v2.0 해결책**:
- `capture_id` (INTEGER PK) 기반 식별
- `tags.capture_id` 외래키 추가
- 모든 API가 ID 기반으로 통신

**성능 개선**:
- 타임스탬프 문자열 비교 → ID 인덱스 조회: **10-100배 빠름**
- UTF-8 인코딩/디코딩 제거
- SQL `datetime()` 함수 호출 제거

### 2. Soft Delete 시스템

**v1.0 문제점**:
- `filepath NOT NULL` 제약
- 'DELETED' 센티널 문자열 저장
- 모든 코드에서 `=== 'DELETED'` 체크 필요

**v2.0 해결책**:
- `filepath TEXT` (NULL 허용)
- `deleted_at DATETIME` 컬럼 추가
- NULL 체크만으로 삭제 여부 확인

**장점**:
- 삭제 시간 추적 가능
- 데이터 복구 용이
- 더 깔끔한 코드 (`!filepath` vs `filepath !== 'DELETED'`)

### 3. 프론트엔드 안정성

**v1.0 문제점**:
```javascript
// 페이지 1: data-index="0" → capture.id=100
// 페이지 2: data-index="0" → capture.id=200 (다른 레코드!)
```

**v2.0 해결책**:
```javascript
// 모든 페이지: data-capture-id="123" → 항상 동일 레코드
```

**코드 비교**:
| 항목 | v1.0 | v2.0 |
|------|------|------|
| HTML 속성 | `data-index="${index}"` | `data-capture-id="${captureId}"` |
| 선택자 | `querySelector('[data-index]')` | `querySelector('[data-capture-id]')` |
| API 요청 | `{ start_time, end_time }` | `{ capture_id }` |
| 태그맵 키 | `tagMap[timestamp]` | `tagMap[capture_id]` |

### 4. 새로운 기능

**이미지 모달 뷰어** (app.js:325-553):
- 전체화면 이미지 확인
- 키보드 네비게이션 (Arrow, ESC)
- 모달 내 태깅
- 태깅 후 자동 진행
- 듀얼 모니터 지원

**필터 및 페이지네이션**:
- 전체/태그됨/미태그 필터
- 20개씩 페이징
- 이전/다음 버튼

**일괄 작업**:
- 체크박스로 다중 선택
- 일괄 태깅
- 일괄 삭제

### 5. 마이그레이션 지원

**제공 스크립트**:
- `migration.sql`: 스키마 변경 SQL
- `migration.py`: 자동 마이그레이션 + 백업
- `test_migration.py`: 마이그레이션 검증

**주요 변환**:
```sql
-- 'DELETED' 센티널 → NULL
UPDATE captures SET
  filepath = CASE WHEN filepath='DELETED' THEN NULL ELSE filepath END,
  deleted_at = CASE WHEN filepath='DELETED' THEN CURRENT_TIMESTAMP ELSE NULL END;

-- capture_id 매칭 (타임스탬프 기반)
UPDATE tags SET capture_id = (
  SELECT id FROM captures
  WHERE datetime(timestamp) = datetime(tags.timestamp)
  AND monitor_num = 1
);
```

---

## 🐛 디버깅 및 로깅

**콘솔 출력**:
```
[ScreenCapture] 초기화 완료
[Capture] Monitor 1: data\screenshots\2025-10-24\11-25-21_m1.jpg (capture_id: 123)
[Capture] Monitor 2: data\screenshots\2025-10-24\11-25-21_m2.jpg (capture_id: 124)
[Thread] 캡처 스레드 시작
[Thread] Flask 스레드 시작
[Tray] 브라우저 열기: http://localhost:5000
[AutoDelete] 파일 삭제: data\screenshots\2025-10-24\11-25-21_m1.jpg
```

**에러 핸들링**:
- try-except로 API 에러 캡처
- JSON 응답: `{"success": false, "error": "..."}`
- 클라이언트: `alert()` 또는 `console.error()`

**성능 모니터링**:
```python
# database.py에서 쿼리 실행 시간 추적
import time
start = time.time()
cursor.execute(query)
print(f"Query took {time.time() - start:.3f}s")
```

---

## 📊 코드베이스 통계

| 항목 | 값 |
|------|------|
| Python 파일 | 4개 (run, capture, viewer, database) |
| 총 Python 라인 | ~1,200 lines |
| JavaScript 라인 | 1,330 lines |
| HTML 라인 | ~500 lines |
| CSS 라인 | ~650 lines |
| 데이터베이스 테이블 | 3개 (captures, tags, categories) |
| 인덱스 | 7개 |
| API 엔드포인트 | 20+ |
| 프론트엔드 페이지 | 3개 (timeline, stats, settings) |

---

## 📝 향후 개선 사항

**고려 중**:
- [ ] PyInstaller로 단일 실행 파일 생성
- [ ] Windows 시작 프로그램 자동 등록
- [ ] 다국어 지원 (한/영)
- [ ] 태그 수정/삭제 기능
- [ ] CSV/Excel 내보내기
- [ ] 주간/월간 리포트 자동 생성
- [ ] 활동 패턴 분석 (시간대별)
- [ ] 알림 기능 (일정 시간 미분류 경고)
- [ ] 클라우드 백업 옵션 (암호화)
- [ ] 다중 사용자 지원

**구현 완료**:
- [x] Primary key 기반 아키텍처
- [x] Soft delete 시스템
- [x] 이미지 모달 뷰어
- [x] 키보드 네비게이션
- [x] 필터 및 페이지네이션
- [x] 일괄 작업
- [x] 화면 잠금 감지

---

## 🔗 관련 문서

- **REFACTORING.md**: 리팩토링 상세 계획 및 체크리스트 (31KB)
- **README.md**: 프로젝트 개요 및 시작 가이드 (8KB)
- **CLAUDE.md**: AI 어시스턴트 작업 가이드 (6KB)
- **migration.sql**: 데이터베이스 마이그레이션 스크립트 (3KB)
- **config.json**: 설정 파일 (1KB)

---

**작성일**: 2025-10-24
**버전**: 2.0.0 (리팩토링 완료)
**마지막 업데이트**: 2025-10-24
