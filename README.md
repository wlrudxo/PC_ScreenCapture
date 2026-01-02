# Activity Tracker

> PC 활동을 실시간 추적해 태그별로 자동 분류하고, 통계/알림/집중 모드를 제공하는 Windows 데스크톱 앱

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![Svelte](https://img.shields.io/badge/Svelte-Frontend-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-WAL-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

---

## 개요

**Activity Tracker**는 활성 창, Chrome URL, 잠금/유휴 상태를 감지해 활동을 자동 분류하고 통계를 제공하는 PyWebView 기반 앱입니다.
웹 UI(Svelte)를 내장해 대시보드/타임라인/분석/설정을 제공합니다.

![대시보드](docs/images/dashboard.png)

### 핵심 기능

- **실시간 활동 모니터링**
  - Windows 활성 창 감지
  - Chrome URL/프로필 추적 (선택)
  - 화면 잠금/Idle 감지

- **자동 태그 분류**
  - 프로세스/URL/창 제목/경로 패턴 매칭
  - 우선순위 기반 룰 적용
  - Chrome 프로필 매칭 지원

- **통계 및 분석**
  - 일간 대시보드 + 시간대별 차트
  - 기간 분석 + 목표 달성 지표
  - 프로세스/웹사이트 TOP

- **알림 시스템**
  - 태그별 토스트 알림
  - 커스텀 사운드/이미지 (단일/랜덤)
  - 태그별 쿨다운

- **집중 모드**
  - 태그 기반 창 자동 최소화
  - 시간대 설정 + 활성 시간 동안 변경 잠금

- **데이터 관리**
  - DB 백업/복원
  - 룰 내보내기/가져오기(병합/교체)
  - 미분류 재분류/삭제

- **활동 로그 자동 생성**
  - daily/monthly 로그
  - recent.log (LLM 분석용)

  ---

## 다운로드

[📥 최신 릴리즈 다운로드](https://github.com/wlrudxo/PC_ActivityTracker/releases/latest)

1. `ActivityTracker.zip` 다운로드
2. 원하는 위치에 압축 해제
3. `ActivityTracker.exe` 실행

### Chrome 확장 프로그램 설치

Chrome URL을 추적하려면 확장 프로그램을 설치하세요:

1. `chrome://extensions/` 접속
2. **개발자 모드** 활성화 (우측 상단)
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. `chrome_extension` 폴더 선택

> 확장 프로그램이 없어도 활성 창 추적은 정상 작동합니다.

---

## 빠른 시작

### 요구사항

- **Windows 10/11** (64bit)
- **Python 3.11+**
- **Node.js 18+** (웹 UI 빌드용)
- **Google Chrome** (URL 추적용, 선택)

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/wlrudxo/PC_ActivityTracker.git
cd PC_ActivityTracker

# 2. Python 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate        # Windows CMD
# 또는
venv/Scripts/Activate.ps1    # Windows PowerShell

# 3. Python 의존성 설치
pip install -r requirements.txt

# 4. Web UI 빌드
cd webui
npm install
npm run build
cd ..

# 5. 실행
python main_webview.pyw
```

### 개발 모드 실행 (선택)

프론트엔드 수정 시 Hot Reload를 사용하려면:

```bash
# 터미널 1: Vite 개발 서버 실행
cd webui
npm run dev

# 터미널 2: 백엔드 실행 (--dev 플래그)
cd ..
python main_webview.pyw --dev
```

개발 모드에서는 `http://localhost:5173`의 Vite 서버를 사용합니다.

---

## 데이터 저장 위치

- **개발 모드**: 프로젝트 폴더에 DB/로그 저장
- **빌드 모드**: `%APPDATA%\ActivityTracker`에 저장

로그:
- `activity_logs/daily/*.log`
- `activity_logs/monthly/*.log`
- `activity_logs/recent.log`

---

## 트러블슈팅

**Q: `npm install` 실패**
```bash
node --version
npm cache clean --force
cd webui && npm install
```

**Q: `python main_webview.pyw` 실행 시 모듈 에러**
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

**Q: 빈 화면만 보임**
```bash
dir webui\dist
cd webui && npm run build
```

**Q: 토스트 알림이 안 뜸**

Windows 알림 설정을 확인하세요:

1. 설정 → 시스템 → 알림 → Activity Tracker(또는 Python) 알림 켜기
2. 방해 금지(집중 지원) 확인
3. 전체 화면 앱 실행 시 알림이 표시되지 않을 수 있음

---

## 프로젝트 구조

```
PC_ActivityTracker/
├── main_webview.pyw             # 앱 진입점 (PyWebView + pystray)
├── requirements.txt             # Python 의존성
├── ARCHITECTURE.md              # 아키텍처 문서
├── backend/                     # Python 백엔드
│   ├── api_server.py            # FastAPI REST/WS
│   ├── monitor_engine_thread.py # 모니터링 스레드
│   ├── database.py              # SQLite 매니저 (WAL)
│   ├── rule_engine.py           # 룰 매칭 엔진
│   ├── window_tracker.py        # 활성 창 감지
│   ├── screen_detector.py       # 잠금/idle 감지
│   ├── chrome_receiver.py       # Chrome WebSocket 수신
│   ├── notification_manager.py  # 토스트/사운드/이미지
│   ├── focus_blocker.py         # 집중 모드 (창 최소화)
│   ├── log_generator.py         # 활동 로그 생성
│   ├── import_export.py         # DB/룰 백업/복원
│   ├── auto_start.py            # 자동 시작 레지스트리
│   └── config.py                # 경로/설정 관리
├── webui/                       # Svelte 웹 UI
│   ├── src/
│   │   ├── pages/               # 페이지 컴포넌트
│   │   ├── lib/                 # API/stores/components/utils
│   │   └── App.svelte
│   └── dist/                    # 빌드 결과물
├── chrome_extension/            # Chrome 확장 (Manifest V3)
```

상세 아키텍처는 `ARCHITECTURE.md` 참고.

---

## 기술 스택

**Backend**
- Python 3.x
- FastAPI + Uvicorn
- SQLite (WAL)
- threading / asyncio
- ctypes / psutil
- windows-toasts / winsound

**Frontend**
- Svelte + Vite
- TailwindCSS
- Chart.js

**Desktop**
- PyWebView (EdgeChromium)
- pystray

**Chrome Extension**
- Manifest V3
- WebSocket client

---

## License

This project is licensed under the [MIT License](LICENSE).
