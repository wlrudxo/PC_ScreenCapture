# Activity Tracker V2

> PC 활동을 실시간 추적하여 태그별로 자동 분류하고 통계를 시각화하는 개인용 데스크톱 애플리케이션

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Svelte](https://img.shields.io/badge/Svelte-Frontend-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-WAL-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## 개요

**Activity Tracker V2**는 Windows PC에서 사용자의 활동을 자동으로 추적하고 분류하는 데스크톱 애플리케이션입니다.
활성 창, Chrome URL, 화면 잠금 상태를 실시간으로 모니터링하여 태그 기반으로 분류하고, 웹 기반 대시보드로 통계를 제공합니다.

### 핵심 기능

- **실시간 활동 모니터링** (2초 간격)
  - Windows 활성 창 자동 감지
  - Chrome URL 추적 (WebSocket 기반 확장 프로그램)
  - 화면 잠금/Idle 상태 감지

- **우선순위 기반 자동 태그 분류**
  - 프로세스명, 창 제목, URL 패턴 매칭
  - 와일드카드 패턴 지원 (`*youtube.com*`, `*.pdf`)
  - Chrome 프로필별 분류 가능

- **통계 및 시각화**
  - 태그별 사용 시간 대시보드 (파이/바 차트)
  - 시간대별 타임라인 바 시각화
  - 기간별 분석 및 목표 대비 달성률

- **알림 시스템**
  - 태그별 토스트 알림
  - 커스텀 사운드 (다중, 랜덤)
  - 히어로 이미지 지원 (다중, 랜덤)

- **집중 모드**
  - 태그별 창 최소화 (방해 차단)
  - 시간대 설정 (예: 09:00~18:00)
  - 변경 방지 (차단 시간 중 설정 잠금)

- **활동 로그 자동 생성**
  - daily/monthly 로그 파일
  - recent.log (LLM 분석용)

- **백그라운드 실행**
  - 시스템 트레이 상주 (pystray)
  - 닫기 시 트레이로 숨김

---

## 빠른 시작

### 요구사항

- **Windows 10/11** (64bit)
- **Python 3.11+**
- **Node.js 18+** (웹 UI 빌드용)
- **Google Chrome** (URL 추적용, 선택)

### 설치

```bash
# 저장소 클론
git clone https://github.com/wlrudxo/PC_ScreenCapture.git
cd PC_ScreenCapture

# Python 가상환경 생성
py -3.13 -m venv venv313
venv313\Scripts\activate

# Python 의존성 설치
pip install -r requirements.txt

# Web UI 빌드
cd webui
npm install
npm run build
cd ..

# 실행 (더블클릭 또는)
python main_webview.pyw
```

### Chrome 확장 프로그램 설치 (선택)

Chrome URL을 추적하려면 확장 프로그램을 설치해야 합니다:

1. Chrome 주소창에 `chrome://extensions/` 입력
2. 우측 상단 **개발자 모드** 활성화
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. `chrome_extension` 폴더 선택
5. 확장 프로그램 아이콘 클릭 → 프로필명 입력 (선택)

> 확장 프로그램이 없어도 활성 창 추적은 정상 작동합니다.

---

## 프로젝트 구조

```
PC_ScreenCapture_V2/
├── main_webview.pyw             # 앱 진입점 (PyWebView + pystray, 콘솔 없음)
├── requirements.txt             # Python 의존성
├── ARCHITECTURE.md              # 상세 아키텍처 문서
├── CLAUDE.md                    # 프로젝트 컨텍스트
│
├── backend/                     # Python 백엔드
│   ├── api_server.py            # FastAPI REST/WebSocket 서버
│   ├── monitor_engine_thread.py # 모니터링 스레드 (threading)
│   ├── database.py              # SQLite 매니저 (WAL, thread-safe)
│   ├── rule_engine.py           # 룰 매칭 엔진
│   ├── window_tracker.py        # 활성 창 감지 (ctypes)
│   ├── screen_detector.py       # 잠금/idle 감지
│   ├── chrome_receiver.py       # WebSocket 서버 (Chrome)
│   ├── notification_manager.py  # 토스트/사운드/이미지 알림
│   ├── focus_blocker.py         # 집중 모드 (창 최소화)
│   ├── log_generator.py         # 활동 로그 생성
│   └── config.py                # 경로/설정 관리
│
├── webui/                       # Svelte 웹 UI
│   ├── src/
│   │   ├── pages/               # 페이지 컴포넌트
│   │   │   ├── Dashboard.svelte
│   │   │   ├── Timeline.svelte
│   │   │   ├── Analysis.svelte
│   │   │   ├── TagManagement.svelte
│   │   │   ├── Notification.svelte
│   │   │   ├── Focus.svelte
│   │   │   └── Settings.svelte
│   │   ├── lib/
│   │   │   ├── api/client.js    # API 클라이언트
│   │   │   └── stores/          # Svelte stores
│   │   └── App.svelte
│   └── dist/                    # 빌드 결과물
│
├── chrome_extension/            # Chrome 확장 (Manifest V3)
│
└── legacy_pyqt/                 # PyQt6 레거시 (아카이브)
```

상세 아키텍처는 [`ARCHITECTURE.md`](ARCHITECTURE.md) 참고

---

## 기술 스택

**Backend**
- Python 3.13
- FastAPI + Uvicorn (REST API, WebSocket)
- SQLite3 (WAL 모드)
- threading (모니터링 스레드)
- ctypes (Windows API)
- psutil (프로세스 정보)
- windows-toasts (토스트 알림)

**Frontend**
- Svelte + Vite
- TailwindCSS
- Chart.js (차트)

**Desktop**
- PyWebView (네이티브 윈도우)
- pystray (시스템 트레이)

**Chrome Extension**
- Manifest V3
- WebSocket 클라이언트

---

## 보안 및 프라이버시

- 모든 데이터 로컬 저장 (외부 전송 없음)
- WebSocket은 localhost만 허용
- Chrome Extension도 로컬 연결만 사용
- 오픈소스 (코드 검증 가능)

---

## 라이선스

이 프로젝트는 개인 학습 및 사용 목적으로 제작되었습니다.

---

**Made with ❤️ for personal productivity tracking**
