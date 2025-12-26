# WebUI 코드 리뷰

**리뷰 날짜**: 2025-12-27
**평가 기준**: 1인 개발 효율성, 목적에 맞는 구현 방법

---

## 요약

| 항목 | 평가 |
|------|------|
| 기술 스택 | 적절함 (Svelte + Vite + TailwindCSS) |
| 코드 일관성 | 양호 |
| 유지보수성 | 개선 필요 |
| 중복 코드 | 다소 많음 |
| 컴포넌트 구조 | 개선 여지 있음 |

---

## 잘된 점

### 1. 기술 스택 선택 (A)

```json
// package.json
"svelte": "^5.43.8",
"tailwindcss": "^4.1.18",
"vite": "^7.2.4",
"chart.js": "^4.5.1",
"svelte-spa-router": "^4.0.1"
```

- **Svelte 5 + Vite**: 빌드 속도와 DX 모두 최신 스택
- **svelte-spa-router**: SPA에 충분한 가벼운 라우터 선택 (react-router 같은 과잉 솔루션 회피)
- **TailwindCSS v4**: 1인 개발에 최적화된 스타일링 방식
- **Chart.js**: D3.js 같은 복잡한 것 대신 목적에 맞는 선택

### 2. API 클라이언트 분리 (A)

`lib/api/client.js`에서 모든 API 호출을 중앙화:

```javascript
export const api = {
  getDashboardDaily: (date) => request(`/dashboard/daily?date=${date}`),
  getTags: () => request('/tags'),
  // ...
};
```

- API 엔드포인트 변경 시 한 곳만 수정
- 에러 핸들링 로직 통일

### 3. Toast/ConfirmModal 재사용 (A)

```javascript
// toast store - 잘 설계된 커스텀 스토어
function createToastStore() {
  const { subscribe, update } = writable([]);
  return {
    subscribe,
    success: (msg, duration) => show(msg, 'success', duration),
    error: (msg, duration) => show(msg, 'error', duration ?? 5000),
    // ...
  };
}
```

- 브라우저 alert/confirm 대신 커스텀 모달 사용
- ConfirmModal이 confirm/alert/prompt 3가지 모드 지원

### 4. WebSocket 상태 관리 (B+)

```javascript
// websocket.js
export const wsConnected = writable(false);
export const latestActivity = writable(null);
export const activityUpdated = writable(0);
```

- 연결 상태를 전역 store로 관리
- 자동 재연결 로직 포함
- ping/pong으로 연결 유지

### 5. CSS 변수 활용 (A)

```css
@theme {
  --color-bg-primary: #0f0f0f;
  --color-accent: #6366f1;
  /* ... */
}
```

- 다크 테마용 CSS 변수 체계적 정의
- TailwindCSS와 잘 통합됨

---

## 개선 필요 사항

### 1. ~~미사용 코드~~ (심각도: 중) - **해결됨**

#### ~~Counter.svelte~~ - **삭제 완료**
```javascript
// lib/Counter.svelte - Svelte 5 runes 보일러플레이트
let count = $state(0)  // 어디서도 사용되지 않음
```

#### ~~client.js의 createWebSocket~~ - **삭제 완료**
```javascript
// client.js (사용되지 않음)
export function createWebSocket(onMessage) { ... }

// websocket.js (실제 사용)
export function connectWebSocket() { ... }
```

#### ~~app.js의 일부 stores~~ - **정리 완료**
```javascript
// 삭제됨:
// currentActivity, tags, isLoading, error, dashboardStats, timelineData, settings, getTagColor
```

### 2. 중복 코드 (심각도: 중)

#### 날짜 변경 로직 - 3곳 중복

```javascript
// Dashboard.svelte:211
function changeDate(delta) {
  const current = new Date($selectedDate);
  current.setDate(current.getDate() + delta);
  $selectedDate = current.toISOString().split('T')[0];
}

// Timeline.svelte:124
function changeDate(delta) { /* 동일 */ }

// Analysis.svelte에서는 다른 방식 (startDate/endDate 직접 조작)
```

**해결 방안**: `app.js`에 `changeDate` 함수 추가 또는 DatePicker 컴포넌트화

#### 날짜 선택 UI - 3곳 거의 동일

```svelte
<!-- Dashboard.svelte:238-266, Timeline.svelte:159-188 -->
<div class="flex items-center gap-2">
  <button on:click={() => $selectedDate = new Date().toISOString()...}>오늘</button>
  <button on:click={() => changeDate(-1)}>←</button>
  <input type="date" bind:value={$selectedDate} />
  <button on:click={() => changeDate(1)}>→</button>
</div>
```

**해결 방안**: `<DatePicker bind:value={$selectedDate} />` 컴포넌트 분리

#### 에러 배너 - 모든 페이지에서 반복

```svelte
<!-- 거의 모든 페이지에 존재 -->
{#if error}
  <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
    데이터 로드 실패: {error}
  </div>
{/if}
```

#### file:// 프로토콜 처리 중복

```javascript
// client.js:6-11
function getApiBase() {
  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
}

// websocket.js:24-30
function getWsUrl() {
  if (window.location.protocol === 'file:') {
    return 'ws://127.0.0.1:8000/ws/activity';
  }
  // ...
}

// Notification.svelte:258-261
function getImageUrl(imageId) {
  const base = window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000/api' : '/api';
  // ...
}
```

**해결 방안**: `lib/config.js`에서 `API_BASE`, `WS_BASE` 중앙 관리

### 3. SVG 아이콘 인라인 남발 (심각도: 낮)

```svelte
<!-- Layout.svelte - 7개 아이콘이 각각 6-7줄씩 인라인 -->
{#if item.icon === 'chart-pie'}
  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" ... d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
    <path stroke-linecap="round" ... d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
  </svg>
{:else if item.icon === 'chart-bar'}
  <!-- ... -->
```

**현재 문제 아님**: 7개 아이콘 정도는 관리 가능. 아이콘이 20개 이상 늘어나면 heroicons나 lucide-svelte 도입 고려.

### 4. 상태 변수 과다 (심각도: 낮)

```javascript
// Notification.svelte - 20개 이상의 상태 변수
let loading = true;
let error = null;
let toastEnabled = true;
let soundEnabled = false;
let soundMode = 'single';
let imageEnabled = false;
let imageMode = 'single';
let sounds = [];
let images = [];
let tagAlerts = [];
let selectedSoundId = 0;
let selectedImageId = 0;
let soundFileInput;
let imageFileInput;
let showSoundNameModal = false;
let showImageNameModal = false;
let showDeleteSoundModal = false;
let showDeleteImageModal = false;
let pendingSoundFile = null;
let pendingImageFile = null;
let pendingDeleteSoundId = null;
let pendingDeleteImageId = null;
let pendingSoundDefaultName = '';
```

**1인 개발에서는 OK**: 컴포넌트 분리 비용 vs 가독성 트레이드오프. 현재 수준에서는 분리하지 않는 게 더 효율적.

### 5. ~~Svelte 버전 혼재~~ (심각도: 낮) - **해결됨**

Counter.svelte 삭제로 해결. 현재 모든 파일이 Svelte 4 호환 방식 사용 중.

### 6. Chart.js 관리 패턴 (심각도: 낮)

```javascript
// Dashboard.svelte, Analysis.svelte에서 반복
function initCharts() { /* Chart 인스턴스 생성 */ }
function updateCharts() { /* 데이터 업데이트 */ }

onMount(() => {
  initCharts();
  loadData();
  return () => { chart?.destroy(); };
});
```

**현재는 OK**: 2개 페이지에서만 사용. 더 많은 차트 페이지가 생기면 `useChart` 유틸리티 고려.

---

## 구조적 제안

### 권장 컴포넌트 분리

```
현재:
lib/components/
  ├── Layout.svelte
  ├── Toast.svelte
  └── ConfirmModal.svelte

권장 추가:
lib/components/
  ├── DatePicker.svelte      # 날짜 선택 UI (Dashboard, Timeline 공용)
  ├── DateRangePicker.svelte # 기간 선택 UI (Analysis용)
  ├── ErrorBanner.svelte     # {#if error} 반복 제거
  └── LoadingOverlay.svelte  # 로딩 UI 통일
```

### 구조 개선안

```
lib/
  ├── api/
  │   └── client.js
  ├── config.js              # API_BASE, WS_BASE 등 상수
  ├── stores/
  │   ├── app.js
  │   ├── toast.js
  │   └── websocket.js
  ├── utils/
  │   └── date.js            # changeDate, formatDate 등
  └── components/
      └── ...
```

---

## 우선순위 권장 작업

| 우선순위 | 작업 | 예상 효과 | 상태 |
|---------|------|----------|------|
| 1 | Counter.svelte 삭제 | 혼란 방지 | **완료** |
| 2 | client.js의 createWebSocket 삭제 | 중복 제거 | **완료** |
| 3 | app.js 미사용 stores 정리 | 코드 간결화 | **완료** |
| 4 | file:// 프로토콜 로직 통합 | 유지보수성 향상 | - |
| 5 | DatePicker 컴포넌트 분리 | 중복 UI 제거 | - |

---

## 결론

전체적으로 **1인 개발에 적절한 수준**의 코드베이스입니다.

**좋은 판단**:
- 과도한 추상화를 피하고 실용적인 수준에서 컴포넌트 분리
- 복잡한 상태 관리 라이브러리 없이 Svelte stores로 해결
- SPA 라우터, 차트 라이브러리 등 목적에 맞는 가벼운 라이브러리 선택

**개선하면 좋을 점**:
- 미사용 코드 정리 (Counter.svelte, 중복 WebSocket 로직)
- 3곳 이상 반복되는 패턴은 추출 고려 (DatePicker, ErrorBanner)
- config 상수 중앙화

현재 앱이 잘 동작하고 있다면, 위 개선사항은 **리팩토링 시간이 생길 때** 점진적으로 적용하면 됩니다. 기능 개발 우선.
