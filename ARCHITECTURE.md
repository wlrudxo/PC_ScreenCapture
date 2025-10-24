# ScreenCapture - 프로젝트 구조 문서

## 📁 프로젝트 디렉토리 구조

```
ScreenCapture/
├── run.py                    # 통합 실행 진입점
├── capture.py                # 화면 캡처 모듈
├── viewer.py                 # Flask 웹 서버 + API
├── database.py               # SQLite 데이터베이스 관리
├── config.json               # 설정 파일
├── requirements.txt          # Python 패키지 의존성
├── README.md                 # 프로젝트 설명 문서
├── ARCHITECTURE.md           # 이 문서
│
├── data/                     # 데이터 저장소
│   ├── activity.db           # SQLite 데이터베이스
│   └── screenshots/          # 캡처된 이미지
│       └── 2025-10-23/       # 날짜별 폴더
│           ├── 11-25-21_m1.jpg
│           ├── 11-25-21_m2.jpg
│           └── ...
│
├── static/                   # 정적 파일
│   ├── style.css             # CSS 스타일시트
│   └── app.js                # JavaScript 로직
│
└── templates/                # HTML 템플릿
    ├── timeline.html         # 타임라인 페이지
    ├── stats.html            # 통계 페이지
    └── settings.html         # 설정 페이지
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

**캡처 프로세스**:
```
1. 현재 시간 획득
2. 날짜별 폴더 생성 (data/screenshots/YYYY-MM-DD/)
3. 각 모니터 순회:
   - mss로 스크린샷 캡처
   - PIL로 JPEG 변환 (품질 85%)
   - 파일명: HH-MM-SS_m{N}.jpg
   - 파일 저장
   - DB에 레코드 추가
4. 설정된 간격(분) 대기
5. 예약 종료 시간 체크
6. 반복
```

**설정 파라미터**:
- `interval_minutes`: 캡처 간격 (기본 3분)
- `image_quality`: JPEG 품질 (기본 85%)
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
- `GET /api/captures/<date>` - 특정 날짜의 캡처 목록
- `GET /screenshots/<path>` - 이미지 파일 제공

**태그 관련**:
- `GET /api/tags/<date>` - 특정 날짜의 태그 목록
- `POST /api/tags` - 새 태그 추가
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

#### 테이블 스키마

**captures** - 캡처된 스크린샷 로그
```sql
CREATE TABLE captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    monitor_num INTEGER NOT NULL,
    filepath TEXT NOT NULL
);
CREATE INDEX idx_captures_timestamp ON captures(timestamp);
```

**tags** - 활동 태그 로그
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,  -- 시작 시간
    category TEXT NOT NULL,        -- 카테고리 (연구, 행정, 개인, 기타)
    activity TEXT NOT NULL,        -- 활동 (코딩, 메일 등)
    duration_min INTEGER NOT NULL  -- 지속 시간 (분)
);
CREATE INDEX idx_tags_timestamp ON tags(timestamp);
```

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
- `get_captures_by_date(date)`: 날짜별 캡처 조회
- `get_captures_by_time_range(start, end)`: 시간 범위별 캡처 조회
- `delete_captures_by_time_range(start, end)`: 시간 범위별 삭제

**Tags**:
- `add_tag(timestamp, category, activity, duration_min)`: 태그 추가
- `get_tags_by_date(date)`: 날짜별 태그 조회
- `get_tags_by_date_range(start_date, end_date)`: 기간별 태그 조회
- `get_category_stats(start_date, end_date)`: 카테고리별 통계
- `get_activity_stats(start_date, end_date)`: 활동별 통계

**Categories**:
- `init_categories(categories)`: 카테고리 초기화 (config.json에서)
- `get_categories()`: 모든 카테고리 조회

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
       └─ capture-grid (세로 리스트)
            └─ capture-item (각 캡처)
                 ├─ capture-time (시간)
                 ├─ monitor-images (모니터 1, 2 가로 배치)
                 └─ capture-tagging (드롭다운)
                      ├─ category-select
                      └─ activity-select
```

**인라인 태깅 플로우**:
```
1. 카테고리 선택
   → onCategoryChange(index)
   → 활동 드롭다운 활성화

2. 활동 선택
   → onActivityChange(index)
   → 자동 시간 범위 계산 (캡처 시간 + 간격)
   → API POST /api/tags
   → 성공 시 초록색 하이라이트
   → 1초 후 목록 새로고침 (태그 유지)
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

.charts-column {
    /* 좌측 열: 차트 2개 세로 배치 */
}

.stats-table {
    /* 우측 열: 테이블 전체 높이 */
}
```

**차트 렌더링**:
- Chart.js 사용
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

### static/app.js - JavaScript 로직

**페이지별 초기화**:
```javascript
DOMContentLoaded
  ├─ timeline → initTimeline()
  ├─ stats → initStats()
  └─ settings → initSettings()
```

**주요 함수**:

**타임라인**:
- `loadDates()`: 날짜 목록 로드
- `selectDate(date)`: 날짜 선택 시 캡처 로드
- `loadCaptures(date)`: 캡처 + 태그 동시 로드
- `renderCaptures(captures, tags)`: 캡처 렌더링 (태그 유지)
- `onCategoryChange(index)`: 카테고리 선택 → 활동 활성화
- `onActivityChange(index)`: 활동 선택 → 자동 저장

**통계**:
- `loadStats()`: 기간별 통계 로드
- `renderCategoryChart(stats)`: 원 그래프 렌더링
- `renderActivityChart(stats)`: 막대 그래프 렌더링
- `renderStatsTable(stats)`: 테이블 렌더링

**설정**:
- `loadCurrentSettings()`: 현재 설정 로드
- `updateStatus()`: 상태 업데이트 (3초마다)
- `togglePauseResume()`: 일시정지/재개 토글
- `manualCapture()`: 수동 캡처
- `saveSettings()`: 설정 저장
- `setScheduledStop()`: 예약 종료 설정

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
    /* 시간 | 모니터1 모니터2 | 드롭다운 */
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
- 모니터 이미지: `max-height: 200px`, 비율 유지
- 차트: `max-height: 300px`
- 전체 페이지: `max-width: 1000px` (통계/설정)

---

## ⚙️ 설정 파일 (config.json)

```json
{
  "capture": {
    "interval_minutes": 3,      // 캡처 간격 (분)
    "image_quality": 85,         // JPEG 품질 (50-100)
    "format": "JPEG"             // 이미지 포맷
  },
  "storage": {
    "screenshots_dir": "./data/screenshots",
    "database_path": "./data/activity.db",
    "auto_delete_after_tagging": false  // 태깅 후 자동 삭제
  },
  "viewer": {
    "port": 5000,                // Flask 서버 포트
    "thumbnail_size": [320, 180] // 썸네일 크기
  },
  "categories": [
    {
      "name": "연구",
      "color": "#4CAF50",
      "activities": ["코딩", "논문 읽기", "논문 작성", "PPT 제작"]
    },
    // ... 기타 카테고리
  ]
}
```

---

## 🔄 데이터 플로우

### 캡처 플로우
```
capture.py (캡처 스레드)
  ↓
mss.grab() → PIL.Image → JPEG 저장
  ↓
database.add_capture()
  ↓
SQLite (captures 테이블)
```

### 태깅 플로우
```
사용자 (드롭다운 선택)
  ↓
app.js: onActivityChange()
  ↓
POST /api/tags
  ↓
viewer.py: add_tag()
  ↓
database.add_tag()
  ↓
SQLite (tags 테이블)
  ↓
[자동 삭제 옵션 ON]
  ↓
database.get_captures_by_time_range()
  ↓
파일 삭제 (os.remove)
  ↓
database.delete_captures_by_time_range()
```

### 통계 조회 플로우
```
사용자 (기간 선택 + 조회)
  ↓
app.js: loadStats()
  ↓
GET /api/stats/category
GET /api/stats/activity
  ↓
viewer.py: get_category_stats()
  ├─ database.get_category_stats() (태그된 시간)
  ├─ database.get_captures_by_date() (전체 캡처)
  └─ 미분류 계산: 전체 - 태그됨
  ↓
JSON 응답
  ↓
app.js: renderCategoryChart()
         renderActivityChart()
         renderStatsTable()
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
   - Database 초기화
   - 스크린샷 디렉토리 생성
4. 스레드 시작:
   - capture_thread: capture_instance.start_capture_loop()
   - flask_thread: app.run(port=5000)
   - scheduled_thread: check_scheduled_stop()
   - browser_thread: 2초 후 브라우저 열기
5. 시스템 트레이 아이콘 생성
6. pystray.run() 블로킹 (메인 스레드)
```

### 캡처 루프
```
while is_running:
    1. 예약 종료 시간 체크
    2. is_paused 확인
    3. capture_all_monitors() 실행
    4. interval_minutes × 60초 대기
       (1초 단위로 is_running 체크)
```

### 웹 요청 처리
```
사용자 → 브라우저 → Flask (포트 5000)
  ├─ GET / → timeline.html
  ├─ GET /api/dates → JSON
  ├─ POST /api/tags → database.add_tag()
  └─ GET /screenshots/<path> → send_from_directory()
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

**1080p 듀얼 모니터 기준**:
- 캡처 간격: 3분
- 하루 캡처 수: 480개 (8시간 × 20회/시간)
- 이미지당 크기: ~200KB (JPEG 85%)
- 하루 용량: ~96MB
- 일주일: ~672MB
- 한 달: ~2.8GB

**4K 듀얼 모니터**:
- 이미지당 크기: ~800KB
- 하루 용량: ~384MB
- 일주일: ~2.6GB
- 한 달: ~11GB

---

## 🔐 보안 및 프라이버시

**로컬 전용**:
- 모든 데이터는 로컬에만 저장
- 외부 서버 전송 없음
- Flask는 0.0.0.0:5000으로 바인드 (로컬 네트워크만)

**데이터 관리**:
- 이미지는 태깅 후 자동 삭제 가능
- 날짜별 폴더로 구조화
- 태그 정보는 유지 (이미지만 삭제)

---

## 🐛 디버깅 및 로깅

**콘솔 출력**:
```
[ScreenCapture] 초기화 완료
[Capture] Monitor 1: data\screenshots\2025-10-23\11-25-21_m1.jpg
[Thread] 캡처 스레드 시작
[Thread] Flask 스레드 시작
[Tray] 브라우저 열기: http://localhost:5000
```

**에러 핸들링**:
- try-except로 API 에러 캡처
- JSON 응답: `{"success": false, "error": "..."}`
- 클라이언트: `alert()` 또는 `console.error()`

---

## 📝 향후 개선 사항

- [ ] PyInstaller로 단일 실행 파일 생성
- [ ] Windows 시작 프로그램 자동 등록
- [ ] 다국어 지원 (한/영)
- [ ] 태그 수정/삭제 기능
- [ ] CSV/Excel 내보내기
- [ ] 주간/월간 리포트 자동 생성
- [ ] 활동 패턴 분석 (시간대별)
- [ ] 알림 기능 (일정 시간 미분류 경고)
- [ ] 클라우드 백업 옵션

---

**작성일**: 2025-10-23
**버전**: 1.0.0
