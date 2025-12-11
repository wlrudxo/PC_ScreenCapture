# 코드 리뷰: Activity Tracker V2

**리뷰 일시:** 2025-12-09
**리뷰 기준:** 1인 개발/1인 사용 프로그램 관점에서 개발 효율성 저하 요소 분석

---

## 요약

| 카테고리 | 심각도 | 발견 수 |
|----------|--------|---------|
| 고아 코드 | 낮음 | 4건 |
| 중복 구현 | 중간 | 3건 |
| 과도한 책임 | 중간 | 3건 |
| 과도한 추상화 | 없음 | 0건 |
| 기타 효율성 저하 | 낮음 | 3건 |

**전반적 평가:** 1인 개발 프로젝트로서 **양호한 수준**. 모듈 분리가 적절하고 스레드 안전성이 잘 고려되어 있음. 일부 중복과 사용되지 않는 코드 정리 시 유지보수 효율성 향상 가능.

---

## 1. 고아 코드 (Orphan Code)

### 1.1 미사용 AppConfig 메서드 (낮음)

**위치:** `backend/config.py:56-70`

```python
@staticmethod
def get_config_path():
    """설정 파일 경로 (JSON)"""
    return AppConfig.get_app_dir() / "config.json"

@staticmethod
def get_log_dir():
    """로그 디렉토리"""
    ...

@staticmethod
def get_log_path():
    """로그 파일 경로"""
    ...
```

**문제:** 정의되어 있지만 프로젝트 어디에서도 사용되지 않음.

**권장 조치:**
- 향후 로깅/설정 기능 구현 예정이면 유지
- 아니라면 삭제하여 코드 복잡도 감소

---

### 1.2 WindowTracker._detect_chrome_profile 중복 (낮음)

**위치:** `backend/window_tracker.py:59-94`

**문제:** Chrome 프로필을 프로세스 cmdline에서 추출하지만, 이 정보는 `ChromeURLReceiver`에서 WebSocket으로 더 정확하게 받아옴. `MonitorEngine`에서는 `ChromeURLReceiver`의 데이터를 우선 사용.

```python
# window_tracker.py - 사용되는 곳 없음
def _detect_chrome_profile(self, process: psutil.Process) -> Optional[str]:
    ...

# monitor_engine.py:144-157 - 실제로는 ChromeURLReceiver 데이터 사용
chrome_data = self.chrome_receiver.get_latest_url()
if chrome_data:
    return {
        ...
        'chrome_profile': chrome_data.get('profile') if chrome_data else None,
    }
```

**권장 조치:** `_detect_chrome_profile` 메서드 삭제 또는 fallback으로만 활용

---

### 1.3 reference 폴더 테스트 파일 (정보)

**위치:** `reference/test_*.py`, `reference/demo_*.py`

**문제:** 개발 초기 테스트용 파일들이 남아있음. 현재 애플리케이션에서 사용되지 않음.

**권장 조치:**
- 참고용으로 유지하거나
- `.gitignore`에 추가하여 버전 관리에서 제외

---

### 1.4 루트의 테스트 스크립트 (정보)

**위치:**
- `test_import_export.py`
- `check_db_stats.py`

**문제:** 유틸리티/테스트 스크립트가 프로젝트 루트에 위치

**권장 조치:** `scripts/` 또는 `tools/` 폴더로 이동

---

## 2. 중복 구현

### 2.1 시간 포맷팅 함수 중복 (중간)

**발생 위치:**
- `dashboard_tab.py:235-240` (DailyStatsWidget)
- `dashboard_tab.py:320-321` (DailyStatsWidget)
- `dashboard_tab.py:641-642` (PeriodStatsWidget)
- `timeline_tab.py:265-267`

```python
# 거의 동일한 코드가 4곳 이상에서 반복
hours = int(seconds // 3600)
minutes = int((seconds % 3600) // 60)
time_str = f"{hours}시간 {minutes}분"
```

**권장 조치:** 유틸리티 함수로 추출

```python
# utils.py 또는 각 파일 상단에
def format_duration(seconds: float) -> str:
    """초를 '시간 분' 형식으로 변환"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}시간 {minutes}분"
```

---

### 2.2 총 활동 시간 계산 (자리비움 제외) 중복 (중간)

**발생 위치:**
- `dashboard_tab.py:178`
- `dashboard_tab.py:197`
- `timeline_tab.py:264`

```python
# 동일한 로직 반복
total_seconds = sum(s['total_seconds'] or 0 for s in tag_stats if s['tag_name'] != '자리비움')
```

**권장 조치:** DatabaseManager에 전용 메서드 추가

```python
def get_active_time(self, start_date, end_date) -> float:
    """자리비움 제외 총 활동 시간(초) 반환"""
    stats = self.get_stats_by_tag(start_date, end_date)
    return sum(s['total_seconds'] or 0 for s in stats if s['tag_name'] != '자리비움')
```

---

### 2.3 태그 색상 조회 로직 중복 (낮음)

**발생 위치:**
- `dashboard_tab.py:567-575` (PeriodStatsWidget)

```python
# 매 날짜마다 DB 쿼리 반복
for date in date_range:
    tag_stats = self.db_manager.get_stats_by_tag(start, end)
    for stat in tag_stats:
        if stat['tag_name'] not in tag_colors:
            tag_colors[stat['tag_name']] = stat['tag_color']
```

**문제:** N일 * 태그 수 만큼 중복 조회. 태그는 변경 빈도가 낮으므로 한 번만 조회해도 충분.

**권장 조치:** 미리 태그 목록을 한 번만 조회

---

## 3. 과도한 책임 (Large Files)

### 3.1 dashboard_tab.py - 708줄 (중간)

**문제:** 두 개의 독립적인 위젯(`DailyStatsWidget`, `PeriodStatsWidget`)이 한 파일에 존재

**구조:**
```
dashboard_tab.py (708줄)
├── DashboardTab (wrapper, 20줄)
├── DailyStatsWidget (340줄)
└── PeriodStatsWidget (340줄)
```

**권장 조치:**
- 분리할 경우: `daily_stats_widget.py`, `period_stats_widget.py`
- 현재 상태도 충분히 관리 가능한 수준

---

### 3.2 settings_tab.py - 689줄 (중간)

**문제:** 여러 설정 그룹이 한 파일에 밀집

**구조:**
```
settings_tab.py (689줄)
├── SettingsTab (본체, 450줄)
│   ├── create_general_settings
│   ├── create_sound_settings (150줄+)
│   ├── create_data_management
│   └── 각 on_* 핸들러들
└── RulesImportDialog (70줄)
```

**권장 조치:**
- 알림음 설정을 별도 위젯으로 분리 고려
- 현재 상태로도 기능별 메서드가 잘 분리되어 있어 큰 문제는 아님

---

### 3.3 database.py - 564줄 (낮음)

**문제:** 모든 CRUD, 통계, 설정이 하나의 클래스에

**현재 구조:**
```
DatabaseManager
├── init/connection (50줄)
├── 태그 CRUD (70줄)
├── 활동 CRUD (100줄)
├── 룰 CRUD (80줄)
├── 통계 (50줄)
├── 설정 (30줄)
└── 알림음 (30줄)
```

**평가:** 1인 개발 프로젝트로서 분리 불필요. 메서드가 논리적으로 잘 그룹화되어 있음.

---

## 4. 과도한 추상화

**결론: 없음**

오히려 **적절한 추상화 수준**을 유지하고 있음:
- `DateNavigationWidget`: 재사용 가능한 위젯으로 잘 분리됨
- 각 Backend 모듈이 단일 책임 원칙을 잘 따름
- 불필요한 인터페이스/추상 클래스 없음

---

## 5. 기타 개발 효율성 저하 요소

### 5.1 매직 넘버/스트링 하드코딩 (낮음)

**발생 위치:**
```python
# monitor_engine.py:27
IDLE_THRESHOLD = 300  # OK - 클래스 상수로 정의됨

# chrome_receiver.py:45
self.server = await websockets.serve(self._handler, "localhost", self.port)
# port는 생성자에서 받음 - OK

# notification_manager.py:21
DEFAULT_COOLDOWN = 30  # OK - 클래스 상수로 정의됨
```

**평가:** 대부분 클래스 상수로 적절히 정의되어 있음. **문제 없음.**

---

### 5.2 광범위한 Exception 처리 (낮음)

**패턴:**
```python
try:
    ...
except Exception as e:
    print(f"[Module] 오류: {e}")
```

**발생 위치:** 대부분의 모듈

**평가:**
- 1인 사용 데스크톱 앱에서는 크래시 방지가 중요
- 로깅이 없어 디버깅 시 print 출력에 의존
- **현재 수준에서 충분함**

---

### 5.3 DB 마이그레이션 방식 (정보)

**위치:** `database.py:120-143`

```python
# 기존 테이블에 컬럼 추가 (마이그레이션)
try:
    cursor.execute("ALTER TABLE rules ADD COLUMN process_path_pattern TEXT")
except Exception:
    pass  # 이미 컬럼이 존재하면 무시
```

**평가:**
- 단순하고 효과적인 방식
- 1인 사용에서는 버전 관리형 마이그레이션이 오버엔지니어링
- **현재 방식 유지 권장**

---

## 6. 잘된 점 (Keep Doing)

### 6.1 모듈 분리
```
backend/
├── config.py          # 설정/경로
├── database.py        # 데이터 접근
├── monitor_engine.py  # 핵심 모니터링
├── window_tracker.py  # Windows API
├── screen_detector.py # 화면 상태
├── chrome_receiver.py # WebSocket
├── rule_engine.py     # 룰 매칭
├── notification_manager.py  # 알림
└── import_export.py   # 백업/복원
```
**각 모듈이 단일 책임을 가지며 잘 분리됨**

### 6.2 스레드 안전성
- `DatabaseManager`: `threading.local()`로 스레드별 커넥션
- `ChromeURLReceiver`: `threading.Lock()`으로 데이터 보호
- `NotificationManager`: 별도 스레드에서 알림 표시

### 6.3 의존성 주입
```python
# 좋은 패턴: 객체를 외부에서 주입
class MonitorEngine(QThread):
    def __init__(self, db_manager, rule_engine):
        self.db_manager = db_manager
        self.rule_engine = rule_engine
```

### 6.4 Signal/Slot 패턴
Qt의 Signal/Slot을 적절히 활용하여 UI 업데이트 처리

---

## 7. 권장 조치 우선순위

| 우선순위 | 항목 | 예상 효과 |
|----------|------|-----------|
| 선택적 | 시간 포맷팅 함수 통합 | 코드 중복 20줄 감소 |
| 선택적 | 미사용 AppConfig 메서드 정리 | 고아 코드 15줄 제거 |
| 낮음 | 테스트 스크립트 폴더 정리 | 프로젝트 구조 개선 |
| 낮음 | WindowTracker Chrome 프로필 정리 | 혼란 방지 |

---

## 8. 결론

**Activity Tracker V2**는 1인 개발/1인 사용 프로젝트로서 **잘 설계된 코드베이스**입니다.

**강점:**
- 백엔드/프론트엔드 분리
- 스레드 안전한 설계
- 적절한 모듈 크기
- 과도한 추상화 없음

**개선 여지:**
- 일부 코드 중복 정리 가능
- 미사용 코드 정리 시 약 50줄 감소 가능

**총평:** 현재 상태로 유지보수에 큰 문제 없음. 위 권장 조치는 "있으면 좋음" 수준이며 필수는 아님.
