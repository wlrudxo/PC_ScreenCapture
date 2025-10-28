# 개발 계획

## Phase 1: 백엔드 코어 구축 ✅

### 1.1 프로젝트 기초 설정
- [x] 폴더 구조 생성 (`backend/`, `ui/`, `chrome_extension/`)
- [x] 필요 라이브러리 설치 (`PyQt6`, `pywin32`, `websockets`)
- [x] `.gitignore` 설정

### 1.2 설정 및 경로 관리
- [x] `backend/config.py` 구현
  - `AppConfig.get_app_dir()` - 개발/빌드 모드 자동 구분
  - `AppConfig.get_db_path()` - DB 경로 반환
  - `AppConfig.get_log_path()` - 로그 경로 반환

### 1.3 데이터베이스
- [x] `backend/database.py` 구현
  - `tags` 테이블 스키마 + 기본 데이터
  - `activities` 테이블 스키마 + 인덱스
  - `rules` 테이블 스키마 + 기본 룰
- [x] DatabaseManager 메서드 구현
  - 태그 CRUD
  - 활동 기록 생성/종료/조회
  - 통계 쿼리 (태그별, 프로세스별)
  - 룰 CRUD
  - **스레드 안전성 확보** (threading.local)
  - **update_tag 버그 수정**

### 1.4 모니터링 엔진
- [x] `backend/window_tracker.py` - 활성 창 감지 (pywin32)
- [x] `backend/screen_detector.py` - 화면 잠금/idle 감지
- [x] `backend/chrome_receiver.py` - WebSocket 서버 (포트 8766)
  - 별도 스레드에서 asyncio 실행
  - `threading.Lock`으로 스레드 안전성 확보
  - **stop() 메서드 추가**
- [x] `backend/monitor_engine.py` - QThread로 통합
  - 2초마다 활동 수집
  - 활동 변경 감지 → DB 저장
  - 화면 잠금/idle을 `__LOCKED__`/`__IDLE__`로 처리
  - **스레드 종료 보장 (wait 추가)**

### 1.5 룰 엔진
- [x] `backend/rule_engine.py` 구현
  - `match()` - priority 기반 룰 매칭
  - `is_matched()` - 와일드카드 패턴 매칭 (fnmatch)
  - `reload_rules()` - DB에서 룰 리로드
  - **'미분류' 태그 자동 생성**

---

## Phase 2: 프론트엔드 기본 ✅

### 2.1 메인 윈도우
- [x] `ui/main_window.py` 구현
  - QMainWindow 생성
  - QTabWidget으로 탭 구조
  - MonitorEngine 시작
  - 시그널 연결 (`activity_detected`)
- [x] `main.py` 진입점 구현

### 2.2 대시보드 탭
- [x] `ui/dashboard_tab.py` 구현
  - 날짜 선택 위젯
  - 태그별 통계 카드 (사용 시간 + 진행률 바)
  - 프로세스별 TOP 5 테이블
  - 10초마다 자동 갱신 (QTimer)
  - **QTimer 리소스 정리 (__del__ 메서드)**
  - **DB 예외 처리 추가**

### 2.3 타임라인 탭
- [x] `ui/timeline_tab.py` 구현
  - 날짜/태그 필터
  - QTableWidget으로 활동 목록 표시
  - 컬럼: 시작/종료 시간, 프로세스, 제목/URL, 태그, 시간
  - **실시간 업데이트 (monitor_engine 연결)**
  - **태그 색상 배경 적용**
  - **DB 예외 처리 추가**
  - 수동 태그 변경 기능 (Phase 3로 이연)

---

## Phase 3: 설정 기능 ✅

### 3.1 설정 탭 - 태그 관리
- [x] `ui/settings_tab.py` - 태그 관리 섹션
  - QListWidget으로 태그 목록
  - 태그 추가 다이얼로그 (이름 + 색상 피커)
  - 태그 수정/삭제
  - DB 반영 후 UI 갱신
  - **입력 검증 추가** (이름 필수, 50자 제한)
  - **CASCADE 삭제 경고** (룰 종속성 확인)

### 3.2 설정 탭 - 룰 관리
- [x] `ui/settings_tab.py` - 룰 관리 섹션
  - QTableWidget으로 룰 목록 (우선순위, 이름, 조건, 태그, 활성화)
  - 룰 추가/수정 다이얼로그
    - 우선순위 입력
    - 조건 입력 (프로세스/URL/제목/프로필)
    - 태그 선택
  - 룰 삭제
  - 변경 시 `rule_engine.reload_rules()` 호출
  - **입력 검증 추가** (이름 필수, 최소 1개 조건, 태그 선택)

---

## Phase 4: 고급 기능 ✅

### 4.1 차트
- [x] matplotlib 통합
  - 파이 차트 (태그별 비율)
  - QWidget에 matplotlib 임베딩
  - 대시보드 탭에 추가
  - **한글 폰트 설정** (맑은 고딕)

### 4.2 시스템 트레이
- [x] `ui/tray_icon.py` 구현
  - QSystemTrayIcon 생성
  - 컨텍스트 메뉴 (열기/종료)
  - 창 닫기 → 트레이로 최소화
  - 트레이 아이콘 클릭 → 창 복원
  - **트레이 알림 메시지**

### 4.3 자동 시작
- [x] Windows 시작 프로그램 등록 기능
  - 설정 탭에 체크박스
  - winreg로 레지스트리 수정
  - 체크 해제 시 레지스트리 삭제
  - **backend/auto_start.py 모듈**

### 4.4 스타일링
- [x] `ui/styles.py` - QSS 다크 테마
  - GitHub 스타일
  - 통일된 색상/폰트
  - 모든 위젯에 적용
  - **다크 배경 (#1e1e1e), 액센트 컬러 (#007acc)**

---

## Phase 5: Chrome Extension

### 5.1 확장 프로그램
- [ ] `chrome_extension/manifest.json` 작성
  - permissions: `tabs`, `activeTab`
- [ ] `chrome_extension/background.js` 구현
  - WebSocket 연결 (`ws://localhost:8766`)
  - 활성 탭 변경 감지
  - URL + 프로필명 전송
- [ ] `chrome_extension/popup.html` - 간단한 상태 표시
- [ ] Chrome에 로드 및 테스트

---

## Phase 6: 패키징

### 6.1 빌드 준비
- [ ] 로그 시스템 추가 (logging 모듈)
- [ ] 예외 처리 강화
- [ ] 아이콘 파일 준비 (`icon.ico`)

### 6.2 실행 파일 생성
- [ ] PyInstaller 설치
- [ ] 빌드 명령어 실행
  ```bash
  pyinstaller --windowed --onefile --name="ActivityTracker" --icon=icon.ico main.py
  ```
- [ ] `dist/ActivityTracker.exe` 테스트
  - AppData 경로 동작 확인
  - DB 생성 확인
  - 모니터링 동작 확인

### 6.3 배포 (선택)
- [ ] Inno Setup으로 설치 프로그램 제작
- [ ] 설치 시 Chrome Extension 안내 추가

---

## 체크포인트

### ✅ Phase 1 완료 조건
- DB 테이블 생성 확인
- 백그라운드 모니터링 동작 (콘솔 로그)
- 활동 변경 시 DB에 저장 확인

### ✅ Phase 2 완료 조건
- 메인 윈도우 실행
- 대시보드에 오늘 통계 표시
- 타임라인에 활동 목록 표시

### ✅ Phase 3 완료 조건
- 태그 추가/수정/삭제 동작
- 룰 추가/수정/삭제 동작
- 룰 변경 후 다음 활동부터 적용 확인
- **입력 검증 동작** (빈 값, 길이 제한)
- **CASCADE 삭제 경고** (종속성 확인)

### ✅ Phase 4 완료 조건
- 차트 표시
- 트레이 아이콘 동작 (최소화/복원)
- Windows 시작 프로그램 등록/해제

### ✅ Phase 5 완료 조건
- Chrome Extension 설치
- WebSocket 연결 확인
- Chrome URL이 DB에 저장 확인

### ✅ Phase 6 완료 조건
- `.exe` 파일 정상 실행
- AppData에 DB/로그 생성 확인
- 재부팅 후 자동 시작 확인

---

## 추가 개선 사항 (선택)

- [ ] SQLite → 클라우드 백업 (선택)
- [ ] 주간/월간 리포트 자동 생성
- [ ] 목표 시간 설정 + 알림
- [ ] 스크린샷 자동 캡처 (프라이버시 옵션)
- [ ] 다국어 지원 (한국어/영어)
