# PyWebView 전환 계획 (Frontend 리뉴얼 중심)

작성 목적: 기존 Python 백엔드는 유지하고, UI 품질/정렬/레이아웃 개선을 위해 PyWebView 기반 웹 UI로 전환한다.

## 1) 현재 상태 요약 (UI 기준)

- UI 구성은 전부 PyQt6 위젯 기반 (`ui/` 폴더)
- 주요 화면: 대시보드(차트/테이블), 타임라인(테이블+커스텀 바), 태그/룰 관리(폼+테이블), 알림/집중/설정(폼)
- 테마는 QSS 다크 테마 (`ui/styles.py`)
- 실시간 갱신: QTimer + Qt Signals
- 차트: matplotlib (PyQt 백엔드)
- 커스텀 렌더링: 타임라인 바/이미지 크롭 다이얼로그

## 2) 전환 목표

- UI 정렬/일관성 개선, 현대적 레이아웃/타이포 적용
- 백엔드 로직 변경 최소화 (DB/모니터링/룰/알림 기능 유지)
- 상시 실행 앱에 맞게 가볍고 빠른 UI

## 3) 전환 범위

### 3-1. 웹 UI로 전환할 화면 (우선순위)
1. **대시보드**: 차트/카드/통계 테이블
2. **타임라인**: 테이블 + 시각화 (세로 타임라인 바)

### 3-2. UI 혼용에 대한 선택지 (중요)

PyQt + PyWebView 혼용은 UX 일관성이 깨질 수 있음. 따라서 아래 중 하나를 선택하는 것을 권장한다.

- **Option A: 전체 웹 UI로 전환**
  - 대시보드/타임라인/태그/알림/집중/설정 전부 웹 UI로 구현
  - UX 가장 깔끔, 공수 큼
- **Option B: 폼 화면도 웹으로 간단히 전환**
  - 태그/알림/설정 등도 Tailwind 폼으로 비교적 빠르게 전환
  - UX 깔끔 + 공수 중간
- **Option C: 과도기 분리**
  - 대시보드/타임라인만 웹 UI, 나머지는 별도 PyQt 창 유지
  - 과도기 용도, 최종 UX는 다소 어색

## 4) 구조 제안 (PyWebView 기반)

### 4-1. 앱 구조

PyQt UI 대신 다음과 같이 구성:

- **Python Backend (기존 유지)**
  - 모니터링/DB/룰 엔진/알림/포커스 유지
  - API 제공 (로컬 HTTP + WebSocket)
- **PyWebView Frontend**
  - HTML/CSS/JS (Svelte/React 또는 Vanilla)
  - API 통해 데이터 수신/명령 전송

### 4-2. 통신 방식

#### A안: HTTP + WebSocket (권장)
- HTTP: 통계/조회/설정 등 요청-응답
- WebSocket: 실시간 활동 갱신 push

#### B안: pywebview JS API
- `pywebview.api`로 Python 함수 직접 호출
- 간단하지만 API 확장/버전 관리/테스트가 불편

## 5) 화면별 매핑 설계

### 대시보드
- 현재: `ui/dashboard_tab.py`
- 전환: 웹 대시보드 (카드 + 차트 + 테이블)
- 데이터:
  - `get_stats_by_tag(start, end)`
  - `get_stats_by_process(start, end, limit=5)`
  - 기간별 통계 API 추가 (기간/태그/요일)

### 타임라인
- 현재: `ui/timeline_tab.py` (테이블 + `TimelineBarWidget`)
- 전환: 웹 테이블 + 타임라인 시각화
- 데이터:
  - `get_activities(start, end, tag_id)`
  - 실시간 update 이벤트 (WebSocket)

### 태그/룰 관리
- Option B/A 선택 시 웹 Form + CRUD API로 전환
- Option C 선택 시 PyQt 유지 (별도 창)

## 6) API 스펙 (초안)

### HTTP (REST)
- `GET /api/dashboard/daily?date=YYYY-MM-DD`
- `GET /api/dashboard/period?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/timeline?date=YYYY-MM-DD&tag_id=...`
- `GET /api/tags`

### WebSocket
- `activity_update`: 활동 변경 시 push
- `stats_update`: 필요 시 통계 갱신 알림

## 7) UI 기술 스택 확정

### 확정
- Vite + **Svelte** + Tailwind
  - 번들 작고 상태 관리 내장
  - 이 프로젝트 규모에 적합

### 차트 라이브러리
- **Chart.js** (확정)

## 8) 파일/폴더 구조 제안

```
webui/
  src/
  public/
  dist/            # 빌드 산출물

backend/
  api_server.py    # FastAPI (REST + WebSocket)

main.py            # PyWebView 앱 엔트리
```

## 9) 빌드/배포 (로컬 사용 기준)

- PyWebView 앱 실행 시 `webui/dist` 로드
- API 서버는 동일 프로세스 또는 백그라운드 스레드로 구동
- PyInstaller 사용 시 `webui/dist` 포함

## 10) 단계별 마이그레이션 플랜

### Phase 1: PoC
- PyWebView + 기본 HTML UI
- Python API 연결 최소화 (더미 데이터)

### Phase 2: 대시보드 전환
- 대시보드 API 구현 + 차트 적용
- 실제 DB 연동

### Phase 3: 타임라인 전환
- 테이블 + 시각화
- WebSocket 실시간 갱신 연결

### Phase 4: 선택적 전환
- Option A/B 기준으로 나머지 화면 전환

## 11) API 서버 통합 고려사항

- 기존 `chrome_receiver.py`에 WebSocket 서버가 이미 있음 (포트 8766)
- 가능한 선택지:
  1) **FastAPI에 통합**: REST + WebSocket(`/ws/activity`) 제공
  2) **분리 유지**: Chrome 전용 WebSocket은 그대로, UI용 WebSocket은 별도
- 확정: **분리 유지** (Chrome 확장 수정 리스크 최소화)

## 12) System Tray 대체

- PyQt `QSystemTrayIcon` 대신 **pystray 사용 확정**
- 기본 기능: 열기/종료 메뉴
- 아이콘 리소스는 기존 앱 아이콘 재사용 권장

## 13) 리스크 및 대응

- WebView2 런타임 이슈: 개발 환경에서 고정 사용 → 리스크 낮음
- IPC 설계 복잡도: REST + WS로 명확히 분리
- UI 상태 동기화: React/Svelte state 관리 규칙 명확화

## 14) 결정 사항

- **UI 전환 범위: Option B** (폼 화면도 웹으로 전환)
- **기술 스택: Svelte + Tailwind**
- **통신 방식: HTTP + WebSocket**
- **차트: Chart.js**
- **API 서버: FastAPI**
- **Chrome WS: 분리 유지**
- **System Tray: pystray**
- **Python: 3.13**

## 15) 다음 액션

1. ~~UI 전환 범위 결정~~ → **Option B 확정**
2. API 스펙 확정 (FastAPI + HTTP/WS)
3. ~~웹 UI 기술 스택 선택~~ → **Svelte 확정**
4. webui 스캐폴딩 생성 (Svelte + Tailwind + Chart.js)
5. 대시보드 화면부터 실제 데이터 연동

## 16) 확정된 선택지 요약

| 항목 | 결정 |
|------|------|
| UI 전환 범위 | Option B (전체 웹 UI 전환, 백엔드 유지) |
| 프론트 프레임워크 | Svelte |
| 통신 방식 | HTTP + WebSocket |
| 차트 라이브러리 | Chart.js |
| API 서버 프레임워크 | FastAPI |
| Chrome WS 통합 | 분리 유지 |
| System Tray | pystray |
| Python 버전 | 3.13 |
