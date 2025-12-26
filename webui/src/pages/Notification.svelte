<script>
  let toastEnabled = true;
  let soundEnabled = true;
  let soundMode = 'random'; // 'single' | 'random'
  let imageEnabled = true;
  let imageMode = 'random';

  let sounds = [
    { id: 1, name: 'alert1.wav', path: 'sounds/alert1.wav' },
    { id: 2, name: 'beep.wav', path: 'sounds/beep.wav' }
  ];

  let images = [
    { id: 1, name: 'focus.png', path: 'images/focus.png' },
    { id: 2, name: 'warning.png', path: 'images/warning.png' }
  ];

  let tagAlerts = [
    { id: 2, name: '딴짓', color: '#FF5722', alertEnabled: true, alertMessage: '집중하세요!', alertCooldown: 30 }
  ];
</script>

<div class="p-6 space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-text-primary">알림 설정</h1>
    <p class="text-sm text-text-secondary mt-1">토스트 알림, 사운드, 이미지 설정을 관리합니다</p>
  </div>

  <!-- Global Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
    <h2 class="text-lg font-semibold text-text-primary">전역 설정</h2>

    <div class="flex items-center justify-between py-2">
      <div>
        <div class="text-text-primary font-medium">토스트 알림</div>
        <div class="text-sm text-text-muted">Windows 토스트 알림을 표시합니다</div>
      </div>
      <label class="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" bind:checked={toastEnabled} class="sr-only peer">
        <div class="w-11 h-6 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5"></div>
      </label>
    </div>
  </div>

  <!-- Sound Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">사운드</h2>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2">
          <input type="checkbox" bind:checked={soundEnabled} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
          <span class="text-sm text-text-secondary">사운드 재생</span>
        </label>
        <label class="flex items-center gap-2">
          <input type="checkbox" checked={soundMode === 'random'} on:change={() => soundMode = soundMode === 'random' ? 'single' : 'random'} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
          <span class="text-sm text-text-secondary">랜덤</span>
        </label>
      </div>
    </div>

    <div class="space-y-2">
      {#each sounds as sound}
        <div class="flex items-center justify-between p-3 bg-bg-secondary rounded-lg">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
            <span class="text-text-primary">{sound.name}</span>
          </div>
          <div class="flex items-center gap-2">
            <button class="p-2 rounded-lg hover:bg-bg-hover transition-colors">
              <svg class="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <button class="p-2 rounded-lg hover:bg-bg-hover transition-colors">
              <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      {/each}
    </div>

    <button class="w-full py-2 border-2 border-dashed border-border rounded-lg text-text-muted hover:border-accent hover:text-accent transition-colors">
      + 사운드 추가
    </button>
  </div>

  <!-- Image Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">이미지</h2>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2">
          <input type="checkbox" bind:checked={imageEnabled} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
          <span class="text-sm text-text-secondary">이미지 표시</span>
        </label>
        <label class="flex items-center gap-2">
          <input type="checkbox" checked={imageMode === 'random'} on:change={() => imageMode = imageMode === 'random' ? 'single' : 'random'} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
          <span class="text-sm text-text-secondary">랜덤</span>
        </label>
      </div>
    </div>

    <div class="grid grid-cols-4 gap-4">
      {#each images as image}
        <div class="relative group bg-bg-secondary rounded-lg overflow-hidden border border-border">
          <div class="aspect-[2/1] bg-bg-tertiary flex items-center justify-center">
            <svg class="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div class="p-2">
            <div class="text-sm text-text-primary truncate">{image.name}</div>
          </div>
          <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <button class="p-2 rounded-lg bg-bg-card hover:bg-bg-hover transition-colors">
              <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      {/each}
      <button class="aspect-[2/1] border-2 border-dashed border-border rounded-lg text-text-muted hover:border-accent hover:text-accent transition-colors flex items-center justify-center">
        + 이미지 추가
      </button>
    </div>
  </div>

  <!-- Per-Tag Alert Settings -->
  <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
    <h2 class="text-lg font-semibold text-text-primary">태그별 알림</h2>

    <div class="space-y-3">
      {#each tagAlerts as tag}
        <div class="flex items-center gap-4 p-4 bg-bg-secondary rounded-lg">
          <div class="w-4 h-4 rounded-full" style="background-color: {tag.color}"></div>
          <span class="font-medium text-text-primary w-20">{tag.name}</span>

          <label class="flex items-center gap-2">
            <input type="checkbox" bind:checked={tag.alertEnabled} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
            <span class="text-sm text-text-secondary">활성화</span>
          </label>

          <input
            type="text"
            bind:value={tag.alertMessage}
            placeholder="알림 메시지"
            class="flex-1 px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />

          <div class="flex items-center gap-2">
            <span class="text-sm text-text-muted">쿨다운</span>
            <input
              type="number"
              bind:value={tag.alertCooldown}
              min="0"
              class="w-16 px-2 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary text-sm text-center focus:border-accent focus:ring-1 focus:ring-accent outline-none"
            />
            <span class="text-sm text-text-muted">초</span>
          </div>
        </div>
      {/each}
    </div>
  </div>
</div>
