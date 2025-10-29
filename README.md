# Activity Tracker V2

> PC 활동을 실시간 추적하여 태그별로 자동 분류하고 통계를 시각화하는 개인용 데스크톱 애플리케이션

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-WAL-orange.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## 📋 개요

**Activity Tracker V2**는 Windows PC에서 사용자의 활동을 자동으로 추적하고 분류하는 데스크톱 애플리케이션입니다.
활성 창, Chrome URL, 화면 잠금 상태를 실시간으로 모니터링하여 태그 기반으로 분류하고, 시각적 대시보드로 통계를 제공합니다.

### 핵심 기능

- ⏱️ **실시간 활동 모니터링** (2초 간격)
  - Windows 활성 창 자동 감지
  - Chrome URL 추적 (WebSocket 기반 확장 프로그램)
  - 화면 잠금/Idle 상태 감지

- 🏷️ **우선순위 기반 자동 태그 분류**
  - 프로세스명, 창 제목, URL 패턴 매칭
  - 와일드카드 패턴 지원 (`*youtube.com*`, `*.pdf`)
  - Chrome 프로필별 분류 가능

- 📊 **통계 및 시각화**
  - 태그별 사용 시간 대시보드
  - 파이 차트, 프로세스 TOP 5
  - 시간대별 타임라인 뷰

- ⚙️ **유연한 설정**
  - 태그 CRUD (색상 커스터마이징)
  - 룰 관리 (우선순위, 다중 패턴)
  - Windows 자동 시작

- 🖥️ **백그라운드 실행**
  - 시스템 트레이 상주
  - 최소화 시 트레이로 숨김
  - 가벼운 리소스 사용

---

## 🚀 빠른 시작

### 1. 요구사항

- **Windows 10/11** (64bit)
- **Python 3.8+** (개발 모드)
- **Google Chrome** (URL 추적용)

### 2. 설치

#### 개발 모드 (Python 환경)

```bash
# 저장소 클론
git clone https://github.com/yourusername/PC_ScreenCapture_V2.git
cd PC_ScreenCapture_V2

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

#### 빌드 모드 (단일 EXE)

```bash
# PyInstaller로 빌드
pyinstaller --onefile --windowed --name ActivityTracker main.py

# dist/ActivityTracker.exe 실행
```

### 3. Chrome 확장 프로그램 설치 (선택사항)

Chrome URL을 추적하려면 확장 프로그램을 설치해야 합니다:

1. Chrome 주소창에 `chrome://extensions/` 입력
2. 우측 상단 **개발자 모드** 활성화
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. `chrome_extension` 폴더 선택
5. 확장 프로그램 아이콘 클릭 → 프로필명 입력 (선택)

> **참고:** 확장 프로그램이 없어도 활성 창 추적은 정상 작동합니다.
> Chrome URL만 추적되지 않습니다.

---

## 📖 사용 방법

### 기본 사용 흐름

1. **프로그램 실행**
   - `main.py` 실행 또는 `.exe` 실행
   - 시스템 트레이에 아이콘 표시

2. **자동 추적 시작**
   - 프로그램이 백그라운드에서 자동으로 활동 추적 시작
   - 2초마다 활성 창 감지 및 DB 저장

3. **대시보드 확인**
   - 메인 창 → **📊 대시보드** 탭
   - 날짜 선택 → 태그별 통계/차트 확인

4. **타임라인 확인**
   - **⏱️ 타임라인** 탭
   - 실시간 활동 기록 확인
   - 태그별 필터링 가능

5. **태그/룰 설정**
   - **⚙️ 설정** 탭
   - 태그 추가/수정 (색상 커스터마이징)
   - 룰 추가 (패턴 매칭 조건 설정)

### 룰 설정 예시

**예: YouTube를 "딴짓" 태그로 분류**

1. 설정 탭 → 룰 관리 → **추가** 버튼
2. 룰 정보 입력:
   - 이름: `YouTube 차단`
   - 우선순위: `50`
   - URL 패턴: `*youtube.com*,*youtu.be*`
   - 태그: `딴짓`
3. 저장 → 즉시 적용

**예: 특정 Chrome 프로필을 "업무" 태그로 분류**

1. URL 패턴: `*github.com*,*stackoverflow.com*`
2. Chrome 프로필: `Profile 1`
3. 태그: `업무`

> **Tip:** 쉼표(`,`)로 여러 패턴을 한 번에 지정 가능
> **Tip:** 우선순위가 높을수록 먼저 매칭됨 (100 > 50 > 10)

---

## 🏗️ 프로젝트 구조

```
PC_ScreenCapture_V2/
├── main.py                      # 애플리케이션 진입점
├── requirements.txt             # Python 의존성
├── ARCHITECTURE.md              # 상세 아키텍처 문서
├── CLAUDE.md                    # 프로젝트 컨텍스트
│
├── backend/                     # 백엔드 모듈
│   ├── config.py                # 경로/설정 관리
│   ├── database.py              # SQLite 매니저 (thread-safe)
│   ├── monitor_engine.py        # 모니터링 루프 (QThread)
│   ├── window_tracker.py        # 활성 창 감지 (ctypes)
│   ├── screen_detector.py       # 잠금/idle 감지
│   ├── chrome_receiver.py       # WebSocket 서버
│   ├── rule_engine.py           # 룰 매칭 엔진
│   └── auto_start.py            # Windows 자동 시작
│
├── ui/                          # PyQt6 UI
│   ├── main_window.py           # 메인 윈도우
│   ├── dashboard_tab.py         # 통계 대시보드
│   ├── timeline_tab.py          # 활동 타임라인
│   ├── settings_tab.py          # 설정 (태그/룰)
│   ├── tray_icon.py             # 시스템 트레이
│   └── styles.py                # 다크 테마 QSS
│
├── chrome_extension/            # Chrome 확장 (Manifest V3)
│   ├── manifest.json
│   ├── background.js            # Service Worker
│   ├── popup.html/js            # 설정 팝업
│   └── 설치방법.txt
│
└── reference/                   # 테스트/참고 파일
    ├── test_active_window.py
    ├── test_screen_lock.py
    ├── test_chrome_websocket.py
    └── demo_pyqt6_ui.py
```

상세한 아키텍처는 [`ARCHITECTURE.md`](ARCHITECTURE.md) 참고

---

## 🛠️ 기술 스택

**Backend**
- Python 3.x
- SQLite3 (WAL 모드) - 로컬 데이터 저장
- threading (멀티스레딩)
- asyncio + websockets (WebSocket 서버)
- ctypes (Windows API 호출)
- psutil (프로세스 정보)

**Frontend**
- PyQt6 - GUI 프레임워크
- matplotlib - 차트 시각화
- QSS - 다크 테마 스타일

**Chrome Extension**
- Manifest V3
- Service Worker (background.js)
- chrome.tabs/webNavigation API
- WebSocket 클라이언트

**배포**
- PyInstaller (단일 EXE 빌드)
- Windows Registry (자동 시작)

---

## 🗄️ 데이터베이스 스키마

### 주요 테이블

- **tags** - 태그 정의 (id, name, color)
- **activities** - 활동 기록 (start_time, end_time, process_name, chrome_url, tag_id)
- **rules** - 자동 분류 룰 (priority, process_pattern, url_pattern, tag_id)

### 특수 활동 상태

- `__LOCKED__` - 화면 잠금
- `__IDLE__` - 5분 이상 입력 없음

상세 스키마는 [`ARCHITECTURE.md`](ARCHITECTURE.md#-데이터베이스-스키마) 참고

---

## 🔧 개발 가이드

### 의존성 설치

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
PyQt6
matplotlib
psutil
websockets
```

### 테스트 스크립트

```bash
# 활성 창 감지 테스트
python reference/test_active_window.py

# 화면 잠금 감지 테스트
python reference/test_screen_lock.py

# Chrome WebSocket 연결 테스트
python reference/test_chrome_websocket.py

# PyQt6 UI 데모
python reference/demo_pyqt6_ui.py
```

### 빌드

```bash
# 단일 EXE 빌드
pyinstaller --onefile --windowed --name ActivityTracker main.py

# 아이콘 추가 (선택)
pyinstaller --onefile --windowed --icon=icon.ico --name ActivityTracker main.py
```

빌드 후 데이터는 `%APPDATA%/ActivityTracker`에 저장됩니다.

---

## 🔐 보안 및 프라이버시

- ✅ **모든 데이터 로컬 저장** (외부 전송 없음)
- ✅ **WebSocket은 localhost만 허용** (`ws://127.0.0.1:8766`)
- ✅ **Chrome Extension도 로컬 연결만 사용**
- ✅ **개인 사용 목적** (배포/상업화 없음)
- ✅ **오픈소스** (코드 검증 가능)

> **주의:** 이 프로그램은 활성 창과 URL을 추적합니다.
> 민감한 정보(비밀번호 등)는 직접 수집하지 않지만, 접속한 사이트 주소는 기록됩니다.

---

## 📝 라이선스

이 프로젝트는 개인 학습 및 사용 목적으로 제작되었습니다.
자유롭게 수정 및 사용 가능하나, 상업적 배포는 금지합니다.

---

## 🤝 기여

버그 제보나 기능 제안은 GitHub Issues로 남겨주세요.

**주요 개선 아이디어:**
- [ ] macOS/Linux 지원
- [ ] Firefox/Edge 확장 프로그램
- [ ] 일/주/월별 리포트 생성
- [ ] 목표 설정 및 알림 기능
- [ ] 데이터 내보내기 (CSV/JSON)

---

## 📚 관련 문서

- [ARCHITECTURE.md](ARCHITECTURE.md) - 상세 시스템 아키텍처 및 데이터 흐름
- [CLAUDE.md](CLAUDE.md) - 프로젝트 컨텍스트 및 개발 가이드
- [chrome_extension/설치방법.txt](chrome_extension/설치방법.txt) - 확장 프로그램 설치 가이드

---

## 💡 FAQ

**Q: Chrome URL이 추적되지 않아요**
A: Chrome 확장 프로그램이 설치되어 있는지 확인하세요. 확장 프로그램 없이도 활성 창은 추적됩니다.

**Q: 프로그램을 종료하려면?**
A: 트레이 아이콘 우클릭 → "종료" 또는 메인 창에서 Shift+닫기

**Q: 데이터가 어디에 저장되나요?**
A: 개발 모드는 프로젝트 폴더, 빌드 모드는 `%APPDATA%/ActivityTracker`

**Q: 특정 사이트를 추적하지 않으려면?**
A: 룰에서 해당 URL 패턴을 "자리비움" 또는 "미분류" 태그로 설정하거나, 확장 프로그램을 비활성화하세요.

**Q: 리소스 사용량이 궁금해요**
A: 약 50~80MB RAM, CPU 0~1% (2초 간격 체크 시)

---

## 🎯 로드맵

### v1.0 (현재)
- ✅ 기본 활동 추적
- ✅ 태그/룰 시스템
- ✅ 대시보드/타임라인 UI
- ✅ Chrome 확장 프로그램

### v1.1 (계획)
- [ ] 주간/월간 리포트
- [ ] 목표 시간 설정 및 알림
- [ ] 데이터 백업/복원
- [ ] 룰 Import/Export

### v2.0 (장기)
- [ ] 크로스 플랫폼 지원 (macOS, Linux)
- [ ] 클라우드 동기화 (선택적)
- [ ] 팀 협업 기능

---

**Made with ❤️ for personal productivity tracking**
