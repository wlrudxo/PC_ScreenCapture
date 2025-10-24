# ScreenCapture - 개인 활동 기록 및 분석 도구

## 프로젝트 개요

하루 종일 컴퓨터로 무엇을 했는지 되돌아보기 위한 자동 화면 캡처 및 활동 분석 도구입니다.

### 핵심 기능

- 설정된 간격으로 자동 화면 캡처 (멀티모니터 지원)
- 캡처된 화면을 타임라인으로 확인
- 시간대별 활동 태깅 및 분류
- 카테고리별 시간 사용 통계
- 태깅 완료 후 이미지 삭제 가능

### 사용 목적

개인의 시간 사용 패턴을 파악하고, 생산성을 개선하기 위한 **자기 회고용 도구**입니다.

---

## 기술 스택

### 백엔드
- **Python 3.8+**
- **mss** - 빠른 멀티모니터 스크린샷
- **Pillow** - 이미지 처리 및 JPEG 압축
- **Flask** - 웹 서버 및 API
- **SQLite** - 로컬 데이터베이스
- **pystray** - 시스템 트레이 통합
- **schedule** - 주기적 작업 실행

### 프론트엔드
- **HTML/CSS/JavaScript**
- **Chart.js** (통계 시각화)

---

## 프로젝트 구조

```
ScreenCapture/
├── run.py               # 통합 실행 진입점 (캡처 + 뷰어)
├── capture.py           # 백그라운드 캡처 모듈
├── viewer.py            # Flask 웹 뷰어 + API
├── database.py          # DB 관리 모듈
├── config.json          # 설정 파일
├── requirements.txt     # Python 패키지 목록
│
├── data/
│   ├── screenshots/     # 캡처된 이미지 (날짜별 폴더)
│   │   └── 2025-10-23/
│   │       ├── 14-30-00_m1.jpg  # 모니터 1
│   │       ├── 14-30-00_m2.jpg  # 모니터 2
│   │       └── ...
│   └── activity.db      # SQLite 데이터베이스
│
├── static/              # 정적 파일
│   ├── style.css
│   └── app.js
│
└── templates/           # HTML 템플릿
    ├── timeline.html    # 메인 타임라인 뷰
    └── stats.html       # 통계 대시보드
```

---

## 캡처 설정

### 캡처 간격 옵션
- **3분** (권장): 하루 약 32~80MB, 세밀한 기록
- **5분**: 하루 약 19~48MB, 큰 흐름 파악

### 멀티모니터 처리
- **방식**: 각 모니터를 별도 파일로 저장
- **파일명 형식**: `HH-MM-SS_m1.jpg`, `HH-MM-SS_m2.jpg`
- **뷰어**: 같은 시간대의 모니터 1, 2를 나란히 표시

---

## 활동 카테고리

### 연구 활동
- 코딩
- 논문 읽기
- 논문 작성
- PPT 제작

### 행정 업무
- 메일 처리
- 서류 작성
- 영수증 처리

### 개인 활동
- 언어 공부
- 앱 개발
- 인터넷 서핑
- 유튜브

### 기타
- 자리 비움

---

## 데이터베이스 스키마

### captures 테이블
```sql
CREATE TABLE captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    monitor_num INTEGER NOT NULL,
    filepath TEXT NOT NULL
);
```

### tags 테이블
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    category TEXT NOT NULL,
    activity TEXT NOT NULL,
    duration_min INTEGER NOT NULL
);
```

### categories 테이블
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    activities TEXT NOT NULL  -- JSON array
);
```

---

## 주요 기능 상세

### 1. 자동 캡처 (capture.py)
- 설정된 간격으로 모든 모니터 캡처
- JPEG 압축으로 용량 최적화 (품질 85%)
- 날짜별 폴더에 자동 정리
- 백그라운드 실행 (시스템 트레이)

### 2. 타임라인 뷰어 (viewer.py)
- 날짜 선택 → 해당 날짜의 모든 캡처 표시
- 시간순 정렬, 썸네일 뷰
- 클릭 시 원본 크기로 확대
- 각 시간대별 태깅 UI

### 3. 활동 태깅
- 캡처 시간대 선택 (예: 14:00 ~ 15:00)
- 카테고리 → 활동 선택 (드롭다운)
- 시작/종료 시간 자동 계산
- 태깅 완료 후 해당 시간대 이미지 삭제 옵션

**삭제 로직:**
- 사용자가 14:00~15:00을 "코딩"으로 태깅하면
- `tags` 테이블에 `(14:00:00, "연구", "코딩", 60)` 레코드 생성
- 자동 삭제 옵션이 켜져 있으면:
  - `captures` 테이블에서 해당 시간 범위의 모든 레코드 조회
  - 조회된 `filepath`의 실제 이미지 파일 삭제 (`os.remove()`)
  - `captures` 테이블의 해당 레코드도 삭제

### 4. 통계 대시보드
- **일간 통계**: 오늘 하루 활동 분석
- **주간 통계**: 이번 주 패턴 분석
- **월간 통계**: 한 달 트렌드
- **시각화**:
  - 원그래프: 카테고리별 시간 비율
  - 바차트: 활동별 세부 시간
  - 타임라인: 시간대별 활동 분포

### 5. 이미지 관리
- 태깅 완료 후 자동 삭제 옵션
- 날짜별 일괄 삭제
- 용량 확인 기능

---

## 설정 파일 (config.json)

```json
{
  "capture": {
    "interval_minutes": 3,
    "image_quality": 85,
    "format": "JPEG"
  },
  "storage": {
    "screenshots_dir": "./data/screenshots",
    "database_path": "./data/activity.db",
    "auto_delete_after_tagging": false
  },
  "viewer": {
    "port": 5000,
    "thumbnail_size": [320, 180]
  },
  "categories": [
    {
      "name": "연구",
      "color": "#4CAF50",
      "activities": ["코딩", "논문 읽기", "논문 작성", "PPT 제작"]
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

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 통합 실행 (권장)
```bash
python run.py
```

**run.py가 하는 일:**
- Flask 웹 서버를 메인 프로세스로 실행
- 캡처 로직을 백그라운드 스레드로 함께 실행
- 시스템 트레이 아이콘 생성 (뷰어 열기/일시정지/종료 메뉴)

브라우저에서 `http://localhost:5000` 접속

### 3. 개별 실행 (개발/디버깅용)
```bash
# 터미널 1
python capture.py

# 터미널 2
python viewer.py
```

---

## 개발 로드맵

- [ ] 화면 캡처 모듈 구현 (멀티모니터 지원)
- [ ] 데이터베이스 스키마 설계 및 구현
- [ ] 통합 실행 스크립트 (run.py) 구현
- [ ] 웹 뷰어 구현 - 타임라인 표시
- [ ] 태깅 UI 구현 (카테고리별 분류)
- [ ] 통계 기능 구현 (시간 사용량 분석)
- [ ] 이미지 삭제 기능 구현 (시간 범위 기반)
- [ ] 설정 파일 및 백그라운드 실행 설정
- [ ] 시스템 트레이 통합 (pystray 사용)
  - 뷰어 열기 메뉴
  - 캡처 일시정지/재개 메뉴
  - 종료 메뉴
- [ ] 자동 시작 설정 (Windows 시작 프로그램)

---

## 라이선스

개인 사용 목적의 프로젝트입니다.

---

## 참고사항

### 프라이버시
- 모든 데이터는 로컬에만 저장됩니다
- 외부 서버로 전송되지 않습니다
- 이미지는 태깅 후 삭제 가능합니다

### 용량 관리
- JPEG 압축으로 용량 최적화 (품질 85%)
- **1080p 듀얼 모니터 기준 예상 용량:**
  - 3분 간격: 하루 약 32~80MB
  - 5분 간격: 하루 약 19~48MB
- **주의:** 4K 듀얼 모니터 같은 고해상도 환경에서는 용량이 4배 이상 증가할 수 있습니다
- 주기적인 이미지 삭제 권장 (태깅 후 자동 삭제 기능 활용)

### 시스템 요구사항
- Windows 10/11
- Python 3.8+
- 최소 1GB 여유 공간 (일주일 데이터 기준)
