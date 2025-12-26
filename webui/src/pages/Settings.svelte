<script>
  let settings = {
    pollingInterval: 2,
    idleThreshold: 300,
    logRetentionDays: 30,
    autoStart: true
  };

  let showImportModal = false;
  let showExportModal = false;

  async function handleExport() {
    // TODO: Call API
    alert('내보내기 기능은 API 연동 후 사용 가능합니다.');
  }

  async function handleImport() {
    // TODO: Call API
    alert('가져오기 기능은 API 연동 후 사용 가능합니다.');
  }

  async function handleDeleteUnclassified() {
    if (confirm('미분류 활동을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      // TODO: Call API
      alert('삭제 기능은 API 연동 후 사용 가능합니다.');
    }
  }
</script>

<div class="p-6 space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-text-primary">설정</h1>
    <p class="text-sm text-text-secondary mt-1">애플리케이션 설정을 관리합니다</p>
  </div>

  <!-- General Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-5">
    <h2 class="text-lg font-semibold text-text-primary">일반 설정</h2>

    <div class="grid grid-cols-2 gap-6">
      <div>
        <label class="block text-sm font-medium text-text-secondary mb-2">
          폴링 간격 (초)
        </label>
        <input
          type="number"
          bind:value={settings.pollingInterval}
          min="1"
          max="10"
          class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
        />
        <p class="text-xs text-text-muted mt-1">활동 감지 주기 (기본값: 2초)</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-text-secondary mb-2">
          자리비움 감지 시간 (초)
        </label>
        <input
          type="number"
          bind:value={settings.idleThreshold}
          min="60"
          max="600"
          class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
        />
        <p class="text-xs text-text-muted mt-1">입력 없이 이 시간이 지나면 자리비움 처리 (기본값: 300초)</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-text-secondary mb-2">
          로그 보관 기간 (일)
        </label>
        <input
          type="number"
          bind:value={settings.logRetentionDays}
          min="7"
          max="90"
          class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
        />
        <p class="text-xs text-text-muted mt-1">활동 로그 자동 정리 기간 (기본값: 30일)</p>
      </div>

      <div class="flex items-center justify-between py-4">
        <div>
          <div class="text-text-primary font-medium">Windows 시작 시 자동 실행</div>
          <div class="text-sm text-text-muted">컴퓨터 시작 시 자동으로 실행됩니다</div>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" bind:checked={settings.autoStart} class="sr-only peer">
          <div class="w-11 h-6 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5"></div>
        </label>
      </div>
    </div>
  </div>

  <!-- Data Management -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-5">
    <h2 class="text-lg font-semibold text-text-primary">데이터 관리</h2>

    <div class="grid grid-cols-3 gap-4">
      <button
        on:click={handleExport}
        class="flex flex-col items-center gap-3 p-5 bg-bg-secondary rounded-xl border border-border hover:border-accent transition-colors group"
      >
        <svg class="w-8 h-8 text-text-muted group-hover:text-accent transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        <div class="text-center">
          <div class="font-medium text-text-primary">내보내기</div>
          <div class="text-xs text-text-muted mt-1">데이터베이스 백업</div>
        </div>
      </button>

      <button
        on:click={handleImport}
        class="flex flex-col items-center gap-3 p-5 bg-bg-secondary rounded-xl border border-border hover:border-accent transition-colors group"
      >
        <svg class="w-8 h-8 text-text-muted group-hover:text-accent transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <div class="text-center">
          <div class="font-medium text-text-primary">가져오기</div>
          <div class="text-xs text-text-muted mt-1">백업에서 복원</div>
        </div>
      </button>

      <button
        on:click={handleDeleteUnclassified}
        class="flex flex-col items-center gap-3 p-5 bg-bg-secondary rounded-xl border border-border hover:border-red-500/50 transition-colors group"
      >
        <svg class="w-8 h-8 text-text-muted group-hover:text-red-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        <div class="text-center">
          <div class="font-medium text-text-primary">미분류 삭제</div>
          <div class="text-xs text-text-muted mt-1">미분류 활동 정리</div>
        </div>
      </button>
    </div>
  </div>

  <!-- About -->
  <div class="bg-bg-card rounded-xl border border-border p-5">
    <h2 class="text-lg font-semibold text-text-primary mb-4">정보</h2>

    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-accent flex items-center justify-center">
          <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <div class="font-semibold text-text-primary">Activity Tracker V2</div>
          <div class="text-sm text-text-muted">Version 2.0.0</div>
        </div>
      </div>
      <div class="text-sm text-text-muted">
        PyWebView Edition
      </div>
    </div>
  </div>
</div>
