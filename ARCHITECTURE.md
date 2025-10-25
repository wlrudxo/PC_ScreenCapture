# ScreenCapture - 프로젝트 구조 문서

## 📁 프로젝트 디렉토리 구조

```
ScreenCapture/
├── CORE APPLICATION FILES
│   ├── run.py                    # 통합 실행 진입점
│   ├── capture.py                # 화면 캡처 모듈
│   ├── viewer.py                 # Flask 웹 서버 + API
│   ├── database.py               # SQLite 데이터베이스 관리
│   └── config.json               # 설정 파일
│
├── DOCUMENTATION
│   ├── ARCHITECTURE.md           # 이 문서 (시스템 구조)
│   ├── README.md                 # 프로젝트 개요
│   └── CLAUDE.md                 # AI 어시스턴트 가이드
│
├── TEMPLATES/ (HTML)
│   ├── timeline.html             # 타임라인 페이지 + 이미지 모달
│   ├── stats.html                # 통계 대시보드
│   └── settings.html             # 설정 페이지 + 카테고리 관리
│
├── STATIC/ (Frontend Assets)
│   ├── app.js                    # JavaScript 로직
│   └── style.css                 # CSS 스타일
│
├── DATA/ (Runtime)
│   ├── activity.db               # SQLite 데이터베이스
│   └── screenshots/              # 캡처된 이미지
│       └── YYYY-MM-DD/           # 날짜별 폴더
│           ├── HH-MM-SS_m1.jpg   # 모니터 1
│           ├── HH-MM-SS_m2.jpg   # 모니터 2
│           └── ...
│
├── .git/                         # Git 저장소
├── .gitignore
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
- `capture_all_monitors()`: 모든 모니터 캡처 (mss 사용)
- `start_capture_loop()`: 주기적 캡처 루프 (블로킹)
- `stop_capture()`: 캡처 중지
- `pause_capture()` / `resume_capture()`: 일시정지/재개
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
- `image_quality`: JPEG 품질 50-100 (기본 50)
- `screenshots_dir`: 저장 경로

---

### 3. viewer.py - Flask 웹 서버 및 API

**역할**: 웹 UI 제공 및 REST API 엔드포인트

#### 웹 페이지 라우트

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | timeline.html | 타임라인 (메인 페이지) |
| `/stats` | stats.html | 통계 대시보드 |
| `/settings` | settings.html | 설정 페이지 + 카테고리 관리 |

#### API 엔드포인트

**캡처 관련**:
- `GET /api/dates` - 캡처된 날짜 목록
- `GET /api/captures/<date>` - 특정 날짜의 캡처 목록 (capture_id 포함)
- `GET /screenshots/<path>` - 이미지 파일 제공
- `POST /api/captures/delete` - ID 기반 일괄 삭제 (hard delete)

**태그 관련**:
- `GET /api/tags/<date>` - 특정 날짜의 태그 목록 (카테고리/활동 상세 정보 포함)
- `POST /api/tags` - 새 태그 추가 (capture_id + category_id + activity_id)

**카테고리/활동 관리 (v3.0)**:
- `GET /api/categories` - 카테고리 목록 (활동 포함)
- `POST /api/categories` - 카테고리 추가
- `PUT /api/categories/<id>` - 카테고리 수정
- `DELETE /api/categories/<id>` - 카테고리 삭제
- `POST /api/categories/<id>/activities` - 활동 추가
- `PUT /api/activities/<id>` - 활동 수정
- `DELETE /api/activities/<id>` - 활동 삭제

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

#### 주요 API 응답 형식

**GET /api/captures/<date>**:
```json
{
  "success": true,
  "captures": [
    {
      "timestamp": "2025-10-25 12:45:13",
      "capture_id": 1,
      "monitors": {
        "m1": {
          "id": 1,
          "filepath": "data/screenshots/2025-10-25/12-45-13_m1.jpg",
          "monitor_num": 1,
          "deleted_at": null
        },
        "m2": {
          "id": 2,
          "filepath": "data/screenshots/2025-10-25/12-45-13_m2.jpg",
          "monitor_num": 2,
          "deleted_at": null
        }
      }
    }
  ]
}
```

**POST /api/tags**:
```json
// Request
{
  "capture_id": 1,
  "category_id": 1,
  "activity_id": 2
}

// Response
{
  "success": true
}
```

**GET /api/categories**:
```json
{
  "success": true,
  "categories": [
    {
      "id": 1,
      "name": "연구",
      "color": "#4CAF50",
      "order_index": 0,
      "activities": [
        {"id": 1, "name": "코딩", "order_index": 0},
        {"id": 2, "name": "자료 조사", "order_index": 1}
      ]
    }
  ]
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

#### 테이블 스키마 (v3.0)

**captures** - 캡처된 스크린샷 로그
```sql
CREATE TABLE captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    monitor_num INTEGER NOT NULL,
    filepath TEXT,                     -- NULL 허용 (삭제 시)
    deleted_at DATETIME                -- Soft delete 시간
);

CREATE INDEX idx_captures_timestamp ON captures(timestamp);
CREATE INDEX idx_captures_deleted_at ON captures(deleted_at);
```

**categories** - 카테고리 정의 (v3.0: 별도 테이블)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**activities** - 활동 정의 (v3.0: 별도 테이블)
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

CREATE INDEX idx_activities_category_id ON activities(category_id);
```

**tags** - 활동 태그 로그 (v3.0: ID 기반 참조)
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    category_id INTEGER NOT NULL,      -- FK to categories.id
    activity_id INTEGER NOT NULL,      -- FK to activities.id
    duration_min INTEGER NOT NULL,
    capture_id INTEGER,                -- FK to captures.id
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE RESTRICT,
    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE SET NULL
);

CREATE INDEX idx_tags_timestamp ON tags(timestamp);
CREATE INDEX idx_tags_capture_id ON tags(capture_id);
CREATE INDEX idx_tags_category_id ON tags(category_id);
CREATE INDEX idx_tags_activity_id ON tags(activity_id);
```

#### 주요 메서드

**Captures**:
- `add_capture(timestamp, monitor_num, filepath)`: 캡처 추가
- `get_captures_by_date(date)`: 날짜별 캡처 조회
- `get_capture_by_id(capture_id)`: ID로 직접 조회
- `mark_capture_deleted(capture_id)`: Soft delete (filepath=NULL, deleted_at=NOW)

**Tags**:
- `add_tag(timestamp, category_id, activity_id, duration_min, capture_id)`: 태그 추가
- `get_tags_by_date(date)`: 날짜별 태그 조회
- `get_tags_by_date_with_details(date)`: 태그 조회 (카테고리/활동 JOIN)
- `get_category_stats(start_date, end_date)`: 카테고리별 통계
- `get_activity_stats(start_date, end_date)`: 활동별 통계

**Categories (v3.0)**:
- `init_categories(categories)`: 카테고리 초기화 (config.json에서, DB 비어있을 때만)
- `get_categories_with_activities()`: 모든 카테고리 + 활동 조회
- `add_category(name, color, order_index)`: 카테고리 추가
- `update_category(category_id, name, color, order_index)`: 카테고리 수정
- `delete_category(category_id)`: 카테고리 삭제 (ON DELETE RESTRICT)

**Activities (v3.0)**:
- `add_activity(category_id, name, order_index)`: 활동 추가
- `update_activity(activity_id, name, order_index)`: 활동 수정
- `delete_activity(activity_id)`: 활동 삭제 (ON DELETE RESTRICT)

---

## 🎨 프론트엔드 구조

### templates/timeline.html - 타임라인 페이지

**구조**:
```html
navbar
  └─ 타임라인 / 통계 / 설정

container
  ├─ sidebar (날짜 목록)
  └─ main-content
       ├─ header (선택된 날짜)
       ├─ filter-buttons (전체/태그됨/미태그)
       ├─ bulk-controls (일괄 작업)
       └─ capture-grid
            └─ capture-item
                 ├─ checkbox (선택)
                 ├─ capture-time (시간)
                 ├─ monitor-images (클릭 시 모달)
                 └─ capture-tagging (카테고리/활동 버튼)

modal (이미지 뷰어 - v3.0 사이드바 레이아웃)
  ├─ modal-image-area (왼쪽: 이미지 영역)
  └─ modal-sidebar (오른쪽: 200px)
       ├─ modal-time (날짜 + 시간)
       ├─ modal-tagging (카테고리/활동 선택)
       └─ modal-hint (단축키 도움말)
```

**주요 기능**:
1. **이미지 모달 뷰어**: 이미지 클릭 시 전체화면 모달, 키보드 단축키 (←, →, ESC)
2. **필터링**: 전체/태그됨/미태그 필터
3. **페이지네이션**: 20개씩 표시
4. **일괄 작업**: 체크박스로 다중 선택 → 태깅/삭제

**태깅 플로우**:
```
1. 카테고리 버튼 클릭
   → selectCategory(captureId, categoryId)
   → 활동 버튼 표시

2. 활동 버튼 클릭
   → selectActivity(captureId, categoryId, activityId)
   → POST /api/tags { capture_id, category_id, activity_id }
   → 성공 시 초록색 하이라이트
```

**모달 태깅 플로우**:
```
1. 이미지 클릭 → openCaptureModal(captureId)
2. 카테고리/활동 선택 → selectModalActivity(categoryId, activityId)
3. 태깅 성공 시 자동으로 다음 캡처로 이동
4. 키보드: ← → (네비게이션), ESC (닫기)
```

---

### templates/stats.html - 통계 페이지

**레이아웃** (2열 그리드):
```
┌─────────────────────────────────────┐
│  활동 통계 헤더 (날짜 선택)           │
├──────────────────┬──────────────────┤
│ 카테고리별       │                  │
│ 시간 분포        │   상세 내역      │
│ (Pie Chart)      │   (Table)        │
├──────────────────┤                  │
│ 활동별           │                  │
│ 시간 사용량      │                  │
│ (Bar Chart)      │                  │
└──────────────────┴──────────────────┘
```

**차트 렌더링** (Chart.js):
- 카테고리별 색상 자동 매핑 (config.json의 color 값 사용)
- 미분류: `#E0E0E0` (연회색)

---

### templates/settings.html - 설정 페이지

**섹션 구성**:
1. **캡처 상태** - 실시간 상태 표시, 일시정지/재개, 즉시 캡처
2. **캡처 설정** - 간격, 품질, 자동 삭제 옵션
3. **카테고리 관리 (v3.0)** - 카테고리/활동 추가/수정/삭제, 순서 변경
4. **예약 종료** - 특정 시간에 자동 종료
5. **저장 공간** - 총 캡처 수, 용량 표시
6. **위험 구역** - 모든 이미지 삭제

**카테고리 관리 기능 (v3.0)**:
- 카테고리 색상 변경 (color picker)
- 카테고리명 수정 (inline editing)
- 활동 추가/수정/삭제
- Drag & Drop으로 순서 변경
- ON DELETE RESTRICT: 태그가 연결된 항목은 삭제 불가 (에러 메시지 표시)

---

### static/app.js - JavaScript 로직

**페이지별 초기화**:
```javascript
DOMContentLoaded
  ├─ timeline → initTimeline()
  ├─ stats → initStats()
  └─ settings → initSettings()
```

**주요 함수**:

| 기능 | 함수 | 설명 |
|------|------|------|
| **Timeline** | loadCaptures | 캡처 목록 로드 (capture_id 사용) |
| | renderCaptures | 캡처 렌더링 (ID 기반) |
| **Modal Viewer** | openCaptureModal | 모달 열기 |
| | showModal | 모달 표시 + 이미지 로드 |
| | navigateModal | 이전/다음 (키보드: ← →) |
| | selectModalActivity | 모달 내 태깅 |
| **Tagging** | selectCategory | 카테고리 선택 (ID 기반) |
| | selectActivity | 활동 선택 + 태그 저장 (ID 기반) |
| **Bulk** | bulkSaveTags | 일괄 태깅 (ID 배열) |
| | bulkDeleteCaptures | 일괄 삭제 (ID 배열, hard delete) |
| **Settings** | loadCategoriesForSettings | 카테고리 관리 UI 로드 |
| | updateCategoryColor/Name | 카테고리 수정 |
| | deleteCategory/Activity | 삭제 (ON DELETE RESTRICT 처리) |

**v3.0 주요 변경사항**:
- 모든 태깅 함수에서 `category_id`, `activity_id` (INT) 사용
- 카테고리/활동 정보를 `categories` 전역 배열에서 조회
- 일괄삭제는 hard delete (DB에서 완전 삭제)
- 태깅 후 auto-delete는 soft delete (filepath=NULL)

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
    flex-direction: column;
}

/* 이미지 모달 (v3.0 사이드바 레이아웃) */
.modal-body {
    display: flex;  /* 이미지 영역 + 사이드바 */
}

.modal-image-area {
    flex: 1;
    padding: 0.5rem;  /* 최소 패딩 */
}

.modal-sidebar {
    width: 200px;  /* 컴팩트 사이드바 */
}

.modal-images.dual-monitor {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
}

/* 통계 페이지 */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
}
```

**모달 특징 (v3.0)**:
- 좌우 네비게이션 버튼 제거 (키보드 전용)
- 이미지 영역 최대화 (패딩 최소화)
- 사이드바: 시간, 태깅, 도움말을 우측에 배치
- 듀얼 모니터 이미지 세로 중앙 정렬

---

## ⚙️ 설정 파일 (config.json)

```json
{
  "capture": {
    "interval_minutes": 3,
    "image_quality": 50,
    "format": "JPEG"
  },
  "storage": {
    "screenshots_dir": "./data/screenshots",
    "database_path": "./data/activity.db",
    "auto_delete_after_tagging": true
  },
  "viewer": {
    "port": 5000,
    "thumbnail_size": [320, 180]
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

**중요**: `categories`는 초기 시드 데이터입니다. 프로그램 첫 실행 시 DB로 로드되며, 이후에는 DB가 단일 진실 공급원(Single Source of Truth)이 됩니다. Settings 페이지에서 관리하세요.

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

### 태깅 플로우
```
사용자 (카테고리/활동 버튼 클릭)
  ↓
app.js: selectActivity(captureId, categoryId, activityId)
  ↓
POST /api/tags { capture_id, category_id, activity_id }
  ↓
viewer.py: add_tag()
  ├─ get_capture_by_id(capture_id) → timestamp 조회
  ├─ duration = config['interval_minutes']
  └─ database.add_tag(timestamp, category_id, activity_id, duration, capture_id)
  ↓
SQLite (tags 테이블) - FK 저장
  ↓
[자동 삭제 옵션 ON]
  ↓
database.mark_capture_deleted(capture_id)
  ├─ UPDATE captures SET filepath=NULL, deleted_at=NOW
  └─ 파일 시스템에서 이미지 삭제 (os.remove)
```

### 일괄 삭제 플로우 (v3.0: hard delete)
```
사용자 (체크박스 선택 + 삭제 버튼)
  ↓
app.js: bulkDeleteCaptures()
  ├─ capture_ids = [1, 2, 3]
  └─ POST /api/captures/delete { capture_ids }
  ↓
viewer.py: delete_captures()
  └─ for capture_id:
       ├─ 파일 시스템에서 이미지 삭제
       └─ DELETE FROM captures (hard delete)
  ↓
tags 테이블의 capture_id는 ON DELETE SET NULL로 안전하게 처리
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
| 프론트 | HTML/CSS/JS | 웹 UI |
| 차트 | Chart.js | 통계 시각화 |

---

## 📊 데이터 크기 추정

**1080p 듀얼 모니터 기준** (JPEG 품질 50):
- 캡처 간격: 3분
- 하루 캡처 수: 480개 (8시간 × 20회/시간)
- 이미지당 크기: ~100KB
- 하루 용량: ~48MB
- 일주일: ~336MB
- 한 달: ~1.4GB

---

## 🔐 보안 및 프라이버시

**로컬 전용**:
- 모든 데이터는 로컬에만 저장
- 외부 서버 전송 없음
- Flask는 0.0.0.0:5000으로 바인드 (로컬 네트워크 접근 가능)

**화면 잠금 감지**:
- Windows API로 잠금 화면 감지
- 검은 화면 감지로 이중 체크
- 잠금 시 캡처 건너뜀 (프라이버시 보호)

**데이터 관리**:
- 이미지는 태깅 후 자동 삭제 가능 (`auto_delete_after_tagging`)
- 일괄삭제: DB에서 완전 삭제 (hard delete)
- 태깅 후 자동삭제: Soft delete (filepath=NULL, 태그 정보 유지)

---

## 🔗 관련 문서

- **README.md**: 프로젝트 개요 및 시작 가이드
- **CLAUDE.md**: AI 어시스턴트 작업 가이드
- **config.json**: 설정 파일

---

**버전**: 3.0.0
**최종 업데이트**: 2025-10-25
