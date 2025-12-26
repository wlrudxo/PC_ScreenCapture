<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client.js';

  let loading = true;
  let error = null;

  // Global settings
  let toastEnabled = true;
  let soundEnabled = false;
  let soundMode = 'single';
  let imageEnabled = false;
  let imageMode = 'single';

  // Lists
  let sounds = [];
  let images = [];
  let tagAlerts = [];

  // Selected IDs
  let selectedSoundId = 0;
  let selectedImageId = 0;

  // File input refs
  let soundFileInput;
  let imageFileInput;

  async function loadData() {
    loading = true;
    error = null;

    try {
      const [settingsRes, soundsRes, imagesRes, tagsRes] = await Promise.all([
        api.getAlertSettings(),
        api.getAlertSounds(),
        api.getAlertImages(),
        api.getTagAlertSettings()
      ]);

      toastEnabled = settingsRes.toast_enabled;
      soundEnabled = settingsRes.sound_enabled;
      soundMode = settingsRes.sound_mode;
      selectedSoundId = settingsRes.sound_selected;
      imageEnabled = settingsRes.image_enabled;
      imageMode = settingsRes.image_mode;
      selectedImageId = settingsRes.image_selected;

      sounds = soundsRes.sounds || [];
      images = imagesRes.images || [];
      tagAlerts = tagsRes.tags || [];

    } catch (err) {
      console.error('Failed to load notification settings:', err);
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function updateSetting(key, value) {
    try {
      await api.updateAlertSettings({ [key]: value });
    } catch (err) {
      console.error('Failed to update setting:', err);
      alert('설정 저장 실패: ' + err.message);
    }
  }

  async function handleToastToggle() {
    await updateSetting('toast_enabled', toastEnabled);
  }

  async function handleSoundToggle() {
    await updateSetting('sound_enabled', soundEnabled);
  }

  async function handleSoundModeToggle() {
    soundMode = soundMode === 'random' ? 'single' : 'random';
    await updateSetting('sound_mode', soundMode);
  }

  async function handleImageToggle() {
    await updateSetting('image_enabled', imageEnabled);
  }

  async function handleImageModeToggle() {
    imageMode = imageMode === 'random' ? 'single' : 'random';
    await updateSetting('image_mode', imageMode);
  }

  async function handleSoundSelect(soundId) {
    selectedSoundId = soundId;
    await updateSetting('sound_selected', soundId);
  }

  async function handleImageSelect(imageId) {
    selectedImageId = imageId;
    await updateSetting('image_selected', imageId);
  }

  // File upload handlers
  function triggerSoundUpload() {
    soundFileInput.click();
  }

  function triggerImageUpload() {
    imageFileInput.click();
  }

  async function handleSoundFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const name = prompt('사운드 이름을 입력하세요:', file.name.replace(/\.[^/.]+$/, ''));
    if (!name) return;

    try {
      await api.uploadAlertSound(file, name);
      await loadData();
    } catch (err) {
      alert('업로드 실패: ' + err.message);
    }

    event.target.value = '';
  }

  async function handleImageFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const name = prompt('이미지 이름을 입력하세요:', file.name.replace(/\.[^/.]+$/, ''));
    if (!name) return;

    try {
      await api.uploadAlertImage(file, name);
      await loadData();
    } catch (err) {
      alert('업로드 실패: ' + err.message);
    }

    event.target.value = '';
  }

  async function deleteSound(soundId) {
    if (!confirm('이 사운드를 삭제하시겠습니까?')) return;

    try {
      await api.deleteAlertSound(soundId);
      await loadData();
    } catch (err) {
      alert('삭제 실패: ' + err.message);
    }
  }

  async function deleteImage(imageId) {
    if (!confirm('이 이미지를 삭제하시겠습니까?')) return;

    try {
      await api.deleteAlertImage(imageId);
      await loadData();
    } catch (err) {
      alert('삭제 실패: ' + err.message);
    }
  }

  // Tag alert handlers
  async function updateTagAlert(tagId, field, value) {
    try {
      await api.updateTagAlertSettings(tagId, { [field]: value });
      // Update local state
      tagAlerts = tagAlerts.map(t =>
        t.id === tagId ? { ...t, [field]: value } : t
      );
    } catch (err) {
      alert('설정 저장 실패: ' + err.message);
      await loadData();
    }
  }

  function getFileName(filePath) {
    if (!filePath) return '';
    return filePath.split(/[/\\]/).pop();
  }

  function getImageUrl(imageId) {
    const base = window.location.protocol === 'file:'
      ? 'http://127.0.0.1:8000/api'
      : '/api';
    return `${base}/alerts/images/file/${imageId}`;
  }

  onMount(() => {
    loadData();
  });
</script>

<!-- Hidden file inputs -->
<input
  type="file"
  accept=".wav,.mp3,.ogg,.flac"
  bind:this={soundFileInput}
  on:change={handleSoundFileSelect}
  class="hidden"
/>
<input
  type="file"
  accept=".png,.jpg,.jpeg"
  bind:this={imageFileInput}
  on:change={handleImageFileSelect}
  class="hidden"
/>

<div class="p-6 space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-text-primary">알림 설정</h1>
    <p class="text-sm text-text-secondary mt-1">토스트 알림, 사운드, 이미지, 태그별 알림을 설정합니다</p>
  </div>

  <!-- Error Banner -->
  {#if error}
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
      데이터 로드 실패: {error}
    </div>
  {/if}

  {#if loading}
    <div class="flex items-center justify-center py-12">
      <div class="text-text-muted">로딩 중...</div>
    </div>
  {:else}
    <!-- Global Settings -->
    <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
      <h2 class="text-lg font-semibold text-text-primary">전역 설정</h2>

      <div class="flex items-center justify-between py-2">
        <div>
          <div class="text-text-primary font-medium">토스트 알림</div>
          <div class="text-sm text-text-muted">Windows 토스트 알림을 표시합니다</div>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" bind:checked={toastEnabled} on:change={handleToastToggle} class="sr-only peer">
          <div class="w-11 h-6 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5"></div>
        </label>
      </div>
    </div>

    <!-- Sound Settings -->
    <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-text-primary">사운드</h2>
        <div class="flex items-center gap-4">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" bind:checked={soundEnabled} on:change={handleSoundToggle} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
            <span class="text-sm text-text-secondary">사운드 재생</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={soundMode === 'random'} on:change={handleSoundModeToggle} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
            <span class="text-sm text-text-secondary">랜덤</span>
          </label>
        </div>
      </div>

      <div class="space-y-2">
        {#each sounds as sound}
          <div
            class="flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors {selectedSoundId === sound.id ? 'bg-accent/20 border border-accent/50' : 'bg-bg-secondary hover:bg-bg-hover'}"
            on:click={() => handleSoundSelect(sound.id)}
            on:keypress={(e) => e.key === 'Enter' && handleSoundSelect(sound.id)}
            role="button"
            tabindex="0"
          >
            <div class="flex items-center gap-3">
              <svg class="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
              <div>
                <span class="text-text-primary">{sound.name}</span>
                <span class="text-xs text-text-muted ml-2">({getFileName(sound.file_path)})</span>
              </div>
            </div>
            <button
              class="p-2 rounded-lg hover:bg-red-500/20 transition-colors"
              on:click|stopPropagation={() => deleteSound(sound.id)}
              aria-label="삭제"
            >
              <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        {:else}
          <div class="text-center py-4 text-text-muted text-sm">등록된 사운드가 없습니다</div>
        {/each}
      </div>

      <button
        class="w-full py-2 border-2 border-dashed border-border rounded-lg text-text-muted hover:border-accent hover:text-accent transition-colors"
        on:click={triggerSoundUpload}
      >
        + 사운드 추가
      </button>

      <p class="text-xs text-text-muted">WAV, MP3, OGG, FLAC 지원. 사운드가 없으면 시스템 기본음 재생.</p>
    </div>

    <!-- Image Settings -->
    <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-text-primary">이미지</h2>
        <div class="flex items-center gap-4">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" bind:checked={imageEnabled} on:change={handleImageToggle} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
            <span class="text-sm text-text-secondary">이미지 표시</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={imageMode === 'random'} on:change={handleImageModeToggle} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0">
            <span class="text-sm text-text-secondary">랜덤</span>
          </label>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-4">
        {#each images as image}
          <div
            class="relative group rounded-lg overflow-hidden border cursor-pointer transition-all {selectedImageId === image.id ? 'border-accent ring-2 ring-accent/30' : 'border-border hover:border-accent/50'}"
            on:click={() => handleImageSelect(image.id)}
            on:keypress={(e) => e.key === 'Enter' && handleImageSelect(image.id)}
            role="button"
            tabindex="0"
          >
            <div class="aspect-[2/1] bg-bg-tertiary">
              <img
                src={getImageUrl(image.id)}
                alt={image.name}
                class="w-full h-full object-cover"
              />
            </div>
            <div class="p-2 bg-bg-secondary">
              <div class="text-sm text-text-primary truncate">{image.name}</div>
            </div>
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <button
                class="p-2 rounded-lg bg-bg-card hover:bg-red-500/20 transition-colors"
                on:click|stopPropagation={() => deleteImage(image.id)}
                aria-label="삭제"
              >
                <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        {/each}
        <button
          class="aspect-[2/1] border-2 border-dashed border-border rounded-lg text-text-muted hover:border-accent hover:text-accent transition-colors flex items-center justify-center"
          on:click={triggerImageUpload}
        >
          + 이미지 추가
        </button>
      </div>

      <p class="text-xs text-text-muted">PNG, JPG 지원. 2:1 비율로 자동 크롭됩니다.</p>
    </div>

    <!-- Per-Tag Alert Settings -->
    <div class="bg-bg-card rounded-xl border border-border p-5 space-y-4">
      <h2 class="text-lg font-semibold text-text-primary">태그별 알림</h2>
      <p class="text-xs text-text-muted -mt-2">특정 태그 활동 감지 시 알림을 보냅니다. 쿨다운 시간 동안 중복 알림을 방지합니다.</p>

      <div class="space-y-3">
        {#each tagAlerts as tag}
          <div class="flex items-center gap-4 p-4 bg-bg-secondary rounded-lg">
            <div class="w-4 h-4 rounded-full flex-shrink-0" style="background-color: {tag.color}"></div>
            <span class="font-medium text-text-primary w-20 flex-shrink-0">{tag.name}</span>

            <label class="flex items-center gap-2 cursor-pointer flex-shrink-0">
              <input
                type="checkbox"
                checked={tag.alert_enabled}
                on:change={(e) => updateTagAlert(tag.id, 'alert_enabled', e.target.checked)}
                class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent focus:ring-accent focus:ring-offset-0"
              >
              <span class="text-sm text-text-secondary">활성화</span>
            </label>

            <input
              type="text"
              value={tag.alert_message}
              placeholder="알림 메시지"
              on:blur={(e) => updateTagAlert(tag.id, 'alert_message', e.target.value)}
              class="flex-1 px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none"
            />

            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="text-sm text-text-muted">쿨다운</span>
              <input
                type="number"
                value={tag.alert_cooldown}
                min="1"
                on:blur={(e) => updateTagAlert(tag.id, 'alert_cooldown', parseInt(e.target.value) || 30)}
                class="w-16 px-2 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary text-sm text-center focus:border-accent focus:ring-1 focus:ring-accent outline-none"
              />
              <span class="text-sm text-text-muted">초</span>
            </div>
          </div>
        {:else}
          <div class="text-center py-4 text-text-muted text-sm">태그가 없습니다</div>
        {/each}
      </div>
    </div>
  {/if}
</div>
