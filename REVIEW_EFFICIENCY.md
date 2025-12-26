# Backend + WebUI 효율성 검토 보고서

검토 범위: `backend/`, `webui/src/` (Svelte UI 및 API 클라이언트 포함)

## 요약
- 전반적으로 구조는 명확하고 유지보수 가능한 형태이며, 기능별 모듈 분리가 잘 되어 있습니다.
- 다만 통계 집계/차트 업데이트 로직에서 불필요한 반복/정렬이 존재하여 데이터가 많아질수록 느려질 여지가 있습니다.
- 개선은 대부분 “작은 최적화” 수준이며, 대규모 리팩터 없이도 효율 개선이 가능합니다.

## 효율적으로 잘 작성된 부분
- `backend/database.py`: SQLite WAL 모드 적용과 인덱스 구성으로 읽기/쓰기 병행 성능 고려됨. (`backend/database.py`)
- `backend/import_export.py`: SQLite backup API 사용으로 일관성 있는 백업 처리. (`backend/import_export.py`)
- `backend/monitor_engine_thread.py`: 폴링 간격/유휴 임계값을 설정으로 외부화하고, 스레드 안전성(이벤트/락) 고려. (`backend/monitor_engine_thread.py`)
- `webui/src/lib/api/client.js`: API 베이스 URL 자동 분기 및 공통 request/업로드 래퍼로 중복 최소화. (`webui/src/lib/api/client.js`)

## 개선 여지가 있는 부분 (효율/성능 관점)
1) 시간대 통계 계산이 활동 수 * 24 반복으로 고정됨  
   - `get_dashboard_hourly`에서 모든 활동을 24시간 모두와 비교합니다. (`backend/api_server.py`)
   - 활동의 시작/끝 시간에서 겹치는 시간대 범위를 계산해 해당 구간만 반복하면 반복 횟수를 크게 줄일 수 있습니다.

2) 대시보드 일간 통계에서 정렬을 2회 수행  
   - `get_dashboard_daily`에서 `activities`를 두 번 정렬합니다. (`backend/api_server.py`)
   - 정렬 결과를 한 번만 만들고 재사용하면 불필요한 O(n log n) 비용 제거 가능.

3) 기간 통계 계산에서 활동 전체를 2회 순회  
   - `get_dashboard_period`에서 `activities`를 기준으로 dailyTrend와 websiteStats를 별도 루프로 계산합니다. (`backend/api_server.py`)
   - 한 번의 루프로 합산하면 메모리 접근과 파싱 비용을 줄일 수 있습니다.

4) 시간대 차트 업데이트에서 O(n^2) 접근  
   - `updateCharts`에서 `hourlyStats.indexOf(hourData)`를 내부 루프에서 반복 호출합니다. (`webui/src/pages/Dashboard.svelte`)
   - `forEach((hourData, idx) => ...)` 방식으로 인덱스를 한 번만 계산하면 효율 개선.

5) `get_activities` 기반 API가 대용량 데이터에 취약  
   - 대시보드/기간 통계에서 전체 활동을 가져온 후 Python에서 집계. (`backend/api_server.py`, `backend/database.py`)
   - 데이터가 커질수록 응답 지연 가능. SQL 집계로 일부 계산을 이동하면 DB가 더 효율적.

## 제안되는 개선 방향 (우선순위 낮음)
- `get_dashboard_hourly`는 시간대 범위를 계산해 루프를 최소화 (활동당 최대 2~3시간대만 순회). (`backend/api_server.py`)
- `get_dashboard_daily`의 정렬/통계 계산을 단일 정렬 결과로 처리. (`backend/api_server.py`)
- `get_dashboard_period`에서 `activities` 1회 순회로 dailyTrend + websiteStats를 동시에 계산. (`backend/api_server.py`)
- `Dashboard.svelte`의 시간대 차트 업데이트 로직에서 인덱스 캐싱으로 O(n^2) 제거. (`webui/src/pages/Dashboard.svelte`)

## 전체 결론
- 현재 구조는 안정적이며 기능 분리가 좋아 성능 이슈를 국소적으로 개선하기 좋습니다.
- 통계/집계 루틴의 반복 계산만 정리해도 응답 속도와 UI 반응성이 개선될 가능성이 큽니다.
