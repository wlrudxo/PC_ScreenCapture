<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client.js';
  import { toast } from '../lib/stores/toast.js';
  import ConfirmModal from '../lib/components/ConfirmModal.svelte';

  let loading = true;
  let error = null;
  let saving = false;

  // General settings
  let settings = {
    polling_interval: '2',
    idle_threshold: '300',
    log_retention_days: '30',
    target_daily_hours: '7',
    target_distraction_ratio: '20'
  };

  // Auto start
  let autoStartEnabled = false;
  let autoStartLoading = false;

  // File inputs
  let dbRestoreInput;
  let rulesImportInput;

  // Processing states
  let backupInProgress = false;
  let restoreInProgress = false;
  let rulesExportInProgress = false;
  let rulesImportInProgress = false;

  // Rules import modal
  let showRulesImportModal = false;
  let rulesImportFile = null;
  let rulesImportMergeMode = true;

  // DB Restore modal
  let showDbRestoreModal = false;
  let dbRestoreFile = null;

  // Exit app
  let showExitModal = false;
  let exitInProgress = false;
  let activeBlocks = [];

  async function loadData() {
    loading = true;
    error = null;

    try {
      const [settingsRes, autoStartRes] = await Promise.all([
        api.getSettings(),
        api.getAutoStart()
      ]);

      settings = {
        polling_interval: settingsRes.settings?.polling_interval || '2',
        idle_threshold: settingsRes.settings?.idle_threshold || '300',
        log_retention_days: settingsRes.settings?.log_retention_days || '30',
        target_daily_hours: settingsRes.settings?.target_daily_hours || '7',
        target_distraction_ratio: settingsRes.settings?.target_distraction_ratio || '20'
      };

      autoStartEnabled = autoStartRes.enabled;
    } catch (err) {
      console.error('Failed to load settings:', err);
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function saveSettings() {
    saving = true;
    try {
      await api.updateSettings({ settings });
      toast.success('설정이 저장되었습니다.');
    } catch (err) {
      toast.error('저장 실패: ' + err.message);
    } finally {
      saving = false;
    }
  }

  async function toggleAutoStart() {
    autoStartLoading = true;
    try {
      const res = await api.setAutoStart(autoStartEnabled);
      autoStartEnabled = res.enabled;
    } catch (err) {
      toast.error('자동 시작 설정 실패: ' + err.message);
      autoStartEnabled = !autoStartEnabled; // 롤백
    } finally {
      autoStartLoading = false;
    }
  }

  // === DB Backup/Restore ===
  async function handleDbBackup() {
    backupInProgress = true;
    try {
      await api.backupDatabase();
      toast.success('백업 파일 다운로드 시작');
    } catch (err) {
      toast.error('백업 실패: ' + err.message);
    } finally {
      backupInProgress = false;
    }
  }

  function triggerDbRestore() {
    dbRestoreInput.click();
  }

  function handleDbRestoreSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    dbRestoreFile = file;
    showDbRestoreModal = true;
    event.target.value = '';
  }

  async function confirmDbRestore() {
    if (!dbRestoreFile) return;

    showDbRestoreModal = false;
    restoreInProgress = true;
    try {
      const res = await api.restoreDatabase(dbRestoreFile);
      toast.success(res.message + ' - 앱을 재시작해주세요.', 5000);
    } catch (err) {
      toast.error('복원 실패: ' + err.message);
    } finally {
      restoreInProgress = false;
      dbRestoreFile = null;
    }
  }

  function cancelDbRestore() {
    showDbRestoreModal = false;
    dbRestoreFile = null;
  }

  // === Rules Export/Import ===
  async function handleRulesExport() {
    rulesExportInProgress = true;
    try {
      const data = await api.exportRules();

      // JSON 파일 다운로드
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const filename = `rules_export_${timestamp}.json`;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);

      toast.success(`룰 내보내기 완료 (태그 ${data.tags?.length || 0}개, 룰 ${data.rules?.length || 0}개)`);
    } catch (err) {
      toast.error('내보내기 실패: ' + err.message);
    } finally {
      rulesExportInProgress = false;
    }
  }

  function triggerRulesImport() {
    rulesImportInput.click();
  }

  function handleRulesFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    rulesImportFile = file;
    rulesImportMergeMode = true;
    showRulesImportModal = true;
    event.target.value = '';
  }

  async function confirmRulesImport() {
    if (!rulesImportFile) return;

    rulesImportInProgress = true;
    try {
      const res = await api.importRules(rulesImportFile, rulesImportMergeMode);
      toast.success(res.message);
      showRulesImportModal = false;
      rulesImportFile = null;
    } catch (err) {
      toast.error('가져오기 실패: ' + err.message);
    } finally {
      rulesImportInProgress = false;
    }
  }

  function cancelRulesImport() {
    showRulesImportModal = false;
    rulesImportFile = null;
  }

  // === App Exit ===
  async function handleExitClick() {
    try {
      const status = await api.getFocusStatus();
      activeBlocks = status.activeBlocks || [];
      showExitModal = true;
    } catch (err) {
      // 상태 체크 실패해도 종료 모달은 표시
      activeBlocks = [];
      showExitModal = true;
    }
  }

  async function confirmExit() {
    exitInProgress = true;
    try {
      await api.exitApp();
      toast.success('앱을 종료합니다...');
    } catch (err) {
      toast.error('종료 실패: ' + err.message);
      exitInProgress = false;
    }
  }

  function cancelExit() {
    showExitModal = false;
    activeBlocks = [];
  }

  onMount(loadData);
</script>

<!-- Hidden file inputs -->
<input
  type="file"
  accept=".db"
  bind:this={dbRestoreInput}
  on:change={handleDbRestoreSelect}
  class="hidden"
/>
<input
  type="file"
  accept=".json"
  bind:this={rulesImportInput}
  on:change={handleRulesFileSelect}
  class="hidden"
/>

<div class="p-6 space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-text-primary">설정</h1>
    <p class="text-sm text-text-secondary mt-1">애플리케이션 설정을 관리합니다</p>
  </div>

  <!-- Error Banner -->
  {#if error}
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
      데이터 로드 실패: {error}
    </div>
  {/if}

  <!-- General Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">일반 설정</h2>
      <button
        on:click={saveSettings}
        disabled={saving}
        class="px-6 py-2 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white rounded-lg transition-colors"
      >
        {saving ? '저장 중...' : '저장'}
      </button>
    </div>

    {#if loading}
      <div class="text-center text-text-muted py-4">로딩 중...</div>
    {:else}
      <!-- Auto Start Toggle -->
      <div class="flex items-center justify-between py-3 border-b border-border">
        <div>
          <div class="text-text-primary font-medium">Windows 시작 시 자동 실행</div>
          <div class="text-sm text-text-muted">컴퓨터 시작 시 자동으로 실행됩니다</div>
        </div>
        <label class="relative inline-flex items-center {autoStartLoading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}">
          <input
            type="checkbox"
            bind:checked={autoStartEnabled}
            on:change={toggleAutoStart}
            disabled={autoStartLoading}
            class="sr-only peer"
          >
          <div class="w-11 h-6 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5"></div>
        </label>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div>
          <label for="polling" class="block text-sm font-medium text-text-secondary mb-2">
            폴링 간격 (초)
          </label>
          <input
            id="polling"
            type="number"
            bind:value={settings.polling_interval}
            min="1"
            max="10"
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </div>

        <div>
          <label for="idle" class="block text-sm font-medium text-text-secondary mb-2">
            자리비움 감지 (초)
          </label>
          <input
            id="idle"
            type="number"
            bind:value={settings.idle_threshold}
            min="60"
            max="600"
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </div>

        <div>
          <label for="retention" class="block text-sm font-medium text-text-secondary mb-2">
            로그 보관 (일)
          </label>
          <input
            id="retention"
            type="number"
            bind:value={settings.log_retention_days}
            min="7"
            max="90"
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </div>
      </div>
    {/if}
  </div>

  <!-- Goal Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-text-primary">목표 설정</h2>
        <p class="text-sm text-text-muted">분석 탭에서 목표 달성 여부를 판단하는 기준값입니다.</p>
      </div>
      <button
        on:click={saveSettings}
        disabled={saving}
        class="px-6 py-2 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white rounded-lg transition-colors"
      >
        {saving ? '저장 중...' : '저장'}
      </button>
    </div>

    <div class="grid grid-cols-2 gap-6">
      <div>
        <label for="targetHours" class="block text-sm font-medium text-text-secondary mb-2">
          일일 목표 활동시간 (시간)
        </label>
        <input
          id="targetHours"
          type="number"
          bind:value={settings.target_daily_hours}
          min="1"
          max="12"
          step="0.5"
          class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
        />
        <p class="text-xs text-text-muted mt-1">이 시간 이상 활동해야 목표 달성</p>
      </div>

      <div>
        <label for="targetRatio" class="block text-sm font-medium text-text-secondary mb-2">
          딴짓 비율 상한 (%)
        </label>
        <input
          id="targetRatio"
          type="number"
          bind:value={settings.target_distraction_ratio}
          min="5"
          max="50"
          step="5"
          class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
        />
        <p class="text-xs text-text-muted mt-1">딴짓 비율이 이 값 미만이어야 목표 달성</p>
      </div>
    </div>
  </div>

  <!-- Data Management -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-5">
    <h2 class="text-lg font-semibold text-text-primary">데이터 관리</h2>

    <!-- DB Backup/Restore -->
    <div class="space-y-3">
      <div class="flex items-center gap-2">
        <span class="font-medium text-text-primary">데이터베이스</span>
        <span class="text-xs text-text-muted">(활동 기록 포함)</span>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <button
          on:click={handleDbBackup}
          disabled={backupInProgress}
          class="flex items-center justify-center gap-2 px-4 py-3 bg-bg-secondary rounded-lg border border-border hover:border-accent transition-colors disabled:opacity-50"
        >
          <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          <span class="text-text-primary">{backupInProgress ? '백업 중...' : '전체 백업'}</span>
        </button>

        <button
          on:click={triggerDbRestore}
          disabled={restoreInProgress}
          class="flex items-center justify-center gap-2 px-4 py-3 bg-bg-secondary rounded-lg border border-border hover:border-accent transition-colors disabled:opacity-50"
        >
          <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span class="text-text-primary">{restoreInProgress ? '복원 중...' : '백업 복원'}</span>
        </button>
      </div>
    </div>

    <!-- Rules Export/Import -->
    <div class="space-y-3 pt-3 border-t border-border">
      <div class="flex items-center gap-2">
        <span class="font-medium text-text-primary">분류 룰</span>
        <span class="text-xs text-text-muted">(태그 + 룰, 활동 기록 미포함)</span>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <button
          on:click={handleRulesExport}
          disabled={rulesExportInProgress}
          class="flex items-center justify-center gap-2 px-4 py-3 bg-bg-secondary rounded-lg border border-border hover:border-accent transition-colors disabled:opacity-50"
        >
          <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          <span class="text-text-primary">{rulesExportInProgress ? '내보내기 중...' : '룰 내보내기'}</span>
        </button>

        <button
          on:click={triggerRulesImport}
          disabled={rulesImportInProgress}
          class="flex items-center justify-center gap-2 px-4 py-3 bg-bg-secondary rounded-lg border border-border hover:border-accent transition-colors disabled:opacity-50"
        >
          <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span class="text-text-primary">{rulesImportInProgress ? '가져오기 중...' : '룰 가져오기'}</span>
        </button>
      </div>
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

  <!-- App Exit -->
  <div class="bg-bg-card rounded-xl border border-red-500/30 p-5">
    <h2 class="text-lg font-semibold text-text-primary mb-4">앱 종료</h2>
    <p class="text-sm text-text-muted mb-4">Activity Tracker를 완전히 종료합니다. 트레이 아이콘도 함께 종료됩니다.</p>
    <button
      on:click={handleExitClick}
      disabled={exitInProgress}
      class="flex items-center justify-center gap-2 px-4 py-3 bg-red-500/10 rounded-lg border border-red-500/30 hover:bg-red-500/20 transition-colors disabled:opacity-50"
    >
      <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
      </svg>
      <span class="text-red-400 font-medium">{exitInProgress ? '종료 중...' : '앱 종료'}</span>
    </button>
  </div>
</div>

<!-- Rules Import Modal -->
{#if showRulesImportModal}
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    on:click={cancelRulesImport}
    on:keydown={(e) => e.key === 'Escape' && cancelRulesImport()}
    role="dialog"
    tabindex="-1"
  >
    <div
      class="bg-bg-card rounded-xl p-6 w-96 border border-border"
      on:click|stopPropagation
      on:keydown|stopPropagation
      role="document"
    >
      <h3 class="text-lg font-semibold text-text-primary mb-4">룰 가져오기</h3>

      <div class="space-y-4">
        <div class="text-sm text-text-secondary">
          파일: <span class="text-text-primary">{rulesImportFile?.name}</span>
        </div>

        <div class="space-y-3">
          <label class="flex items-start gap-3 p-3 bg-bg-secondary rounded-lg cursor-pointer border {rulesImportMergeMode ? 'border-accent' : 'border-transparent'}">
            <input
              type="radio"
              bind:group={rulesImportMergeMode}
              value={true}
              class="mt-1"
            />
            <div>
              <div class="font-medium text-text-primary">병합 모드</div>
              <div class="text-xs text-text-muted">기존 룰 유지 + 새 룰 추가. 같은 이름의 태그는 기존 것 사용.</div>
            </div>
          </label>

          <label class="flex items-start gap-3 p-3 bg-bg-secondary rounded-lg cursor-pointer border {!rulesImportMergeMode ? 'border-accent' : 'border-transparent'}">
            <input
              type="radio"
              bind:group={rulesImportMergeMode}
              value={false}
              class="mt-1"
            />
            <div>
              <div class="font-medium text-text-primary">교체 모드</div>
              <div class="text-xs text-yellow-500">기존 룰 삭제 + 새 룰만 추가. 태그는 유지.</div>
            </div>
          </label>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button
          on:click={cancelRulesImport}
          class="px-4 py-2 bg-bg-secondary text-text-primary rounded-lg hover:bg-bg-hover transition-colors"
        >
          취소
        </button>
        <button
          on:click={confirmRulesImport}
          disabled={rulesImportInProgress}
          class="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover disabled:opacity-50 transition-colors"
        >
          {rulesImportInProgress ? '가져오는 중...' : '가져오기'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- DB Restore Confirm Modal -->
<ConfirmModal
  show={showDbRestoreModal}
  title="데이터베이스 복원"
  type="danger"
  confirmText="복원"
  on:confirm={confirmDbRestore}
  on:cancel={cancelDbRestore}
>
  <p class="text-red-400 font-medium">경고: 현재 데이터베이스가 백업 파일로 교체됩니다.</p>
  <p>파일: <strong class="text-text-primary">{dbRestoreFile?.name}</strong></p>
  <p class="mt-2 text-yellow-400">이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?</p>
</ConfirmModal>

<!-- Exit Confirm Modal -->
<ConfirmModal
  show={showExitModal}
  title="앱 종료"
  type={activeBlocks.length > 0 ? 'danger' : 'warning'}
  confirmText="종료"
  on:confirm={confirmExit}
  on:cancel={cancelExit}
>
  {#if activeBlocks.length > 0}
    <p class="text-red-400 font-medium">현재 집중 모드가 활성화되어 있습니다!</p>
    <p>차단 중인 태그: <strong class="text-red-400">{activeBlocks.map(b => b.name).join(', ')}</strong></p>
    <p class="mt-2">앱을 종료하면 집중 모드가 해제되어 차단된 앱들을 다시 사용할 수 있게 됩니다.</p>
    <p class="text-yellow-400">정말로 종료하시겠습니까?</p>
  {:else}
    <p>Activity Tracker를 종료합니다.</p>
    <p class="text-text-muted">트레이 아이콘과 모든 모니터링이 중지됩니다.</p>
  {/if}
</ConfirmModal>
