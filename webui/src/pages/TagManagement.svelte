<script>
  let tags = [
    { id: 1, name: '업무', color: '#4CAF50', ruleCount: 5 },
    { id: 2, name: '딴짓', color: '#FF5722', ruleCount: 3 },
    { id: 3, name: '자리비움', color: '#9E9E9E', ruleCount: 0 },
    { id: 4, name: '미분류', color: '#607D8B', ruleCount: 0 }
  ];

  let rules = [
    { id: 1, name: 'GitHub 작업', priority: 100, enabled: true, processPattern: 'chrome.exe', urlPattern: '*github.com*', tag: { name: '업무', color: '#4CAF50' } },
    { id: 2, name: 'VS Code', priority: 90, enabled: true, processPattern: 'Code.exe', urlPattern: '', tag: { name: '업무', color: '#4CAF50' } },
    { id: 3, name: 'YouTube', priority: 50, enabled: true, processPattern: 'chrome.exe', urlPattern: '*youtube.com*', tag: { name: '딴짓', color: '#FF5722' } },
  ];

  let showTagModal = false;
  let showRuleModal = false;
  let editingTag = null;
  let editingRule = null;
</script>

<div class="p-6 space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-text-primary">태그 관리</h1>
      <p class="text-sm text-text-secondary mt-1">태그와 분류 규칙을 관리합니다</p>
    </div>
  </div>

  <!-- Tags Section -->
  <div class="bg-bg-card rounded-xl border border-border">
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">태그 목록</h2>
      <button
        class="px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
        on:click={() => { editingTag = null; showTagModal = true; }}
      >
        + 태그 추가
      </button>
    </div>

    <div class="grid grid-cols-4 gap-4 p-5">
      {#each tags as tag}
        <div class="bg-bg-secondary rounded-lg p-4 border border-border hover:border-border-light transition-colors">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-3">
              <div class="w-4 h-4 rounded-full" style="background-color: {tag.color}"></div>
              <span class="font-medium text-text-primary">{tag.name}</span>
            </div>
            <div class="flex items-center gap-1">
              <button class="p-1.5 rounded hover:bg-bg-hover transition-colors">
                <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <button class="p-1.5 rounded hover:bg-bg-hover transition-colors">
                <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
          <div class="text-sm text-text-muted">{tag.ruleCount}개 규칙</div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Rules Section -->
  <div class="bg-bg-card rounded-xl border border-border">
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">분류 규칙</h2>
      <button
        class="px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
        on:click={() => { editingRule = null; showRuleModal = true; }}
      >
        + 규칙 추가
      </button>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-bg-secondary">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">상태</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">우선순위</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">이름</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">태그</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">프로세스</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">URL 패턴</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider w-20">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          {#each rules as rule}
            <tr class="hover:bg-bg-hover transition-colors">
              <td class="px-4 py-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" bind:checked={rule.enabled} class="sr-only peer">
                  <div class="w-9 h-5 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                </label>
              </td>
              <td class="px-4 py-3 text-sm text-text-primary">{rule.priority}</td>
              <td class="px-4 py-3 text-sm text-text-primary font-medium">{rule.name}</td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white"
                  style="background-color: {rule.tag.color}"
                >
                  {rule.tag.name}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-text-secondary font-mono">{rule.processPattern || '-'}</td>
              <td class="px-4 py-3 text-sm text-text-secondary font-mono">{rule.urlPattern || '-'}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <button class="p-1.5 rounded hover:bg-bg-hover transition-colors">
                    <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button class="p-1.5 rounded hover:bg-bg-hover transition-colors">
                    <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</div>
