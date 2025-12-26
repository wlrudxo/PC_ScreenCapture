<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client.js';

  let loading = true;
  let error = null;
  let tags = [];
  let rules = [];

  // Modal states
  let showTagModal = false;
  let showRuleModal = false;
  let editingTag = null;
  let editingRule = null;

  // Form data
  let tagForm = { name: '', color: '#4CAF50' };
  let ruleForm = {
    name: '',
    tag_id: null,
    priority: 50,
    enabled: true,
    process_pattern: '',
    url_pattern: '',
    window_title_pattern: '',
    chrome_profile: '',
    process_path_pattern: ''
  };

  async function loadData() {
    loading = true;
    error = null;

    try {
      const [tagsRes, rulesRes] = await Promise.all([
        api.getTags(),
        api.getRules()
      ]);

      tags = tagsRes.tags || [];
      rules = (rulesRes.rules || []).map(rule => ({
        ...rule,
        tag: tags.find(t => t.id === rule.tag_id) || { name: '미분류', color: '#607D8B' }
      }));

    } catch (err) {
      console.error('Failed to load data:', err);
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Tag CRUD
  function openTagModal(tag = null) {
    editingTag = tag;
    tagForm = tag
      ? { name: tag.name, color: tag.color }
      : { name: '', color: '#4CAF50' };
    showTagModal = true;
  }

  async function saveTag() {
    try {
      if (editingTag) {
        await api.updateTag(editingTag.id, tagForm);
      } else {
        await api.createTag(tagForm);
      }
      showTagModal = false;
      await loadData();
    } catch (err) {
      alert('저장 실패: ' + err.message);
    }
  }

  async function deleteTag(tag) {
    if (!confirm(`'${tag.name}' 태그를 삭제하시겠습니까?`)) return;

    try {
      await api.deleteTag(tag.id);
      await loadData();
    } catch (err) {
      alert('삭제 실패: ' + err.message);
    }
  }

  // Rule CRUD
  function openRuleModal(rule = null) {
    editingRule = rule;
    ruleForm = rule
      ? {
          name: rule.name,
          tag_id: rule.tag_id,
          priority: rule.priority,
          enabled: rule.enabled,
          process_pattern: rule.process_pattern || '',
          url_pattern: rule.url_pattern || '',
          window_title_pattern: rule.window_title_pattern || '',
          chrome_profile: rule.chrome_profile || '',
          process_path_pattern: rule.process_path_pattern || ''
        }
      : {
          name: '',
          tag_id: tags[0]?.id || null,
          priority: 50,
          enabled: true,
          process_pattern: '',
          url_pattern: '',
          window_title_pattern: '',
          chrome_profile: '',
          process_path_pattern: ''
        };
    showRuleModal = true;
  }

  async function saveRule() {
    try {
      const data = {
        ...ruleForm,
        process_pattern: ruleForm.process_pattern || null,
        url_pattern: ruleForm.url_pattern || null,
        window_title_pattern: ruleForm.window_title_pattern || null,
        chrome_profile: ruleForm.chrome_profile || null,
        process_path_pattern: ruleForm.process_path_pattern || null
      };

      if (editingRule) {
        await api.updateRule(editingRule.id, data);
      } else {
        await api.createRule(data);
      }
      showRuleModal = false;
      await loadData();
    } catch (err) {
      alert('저장 실패: ' + err.message);
    }
  }

  async function deleteRule(rule) {
    if (!confirm(`'${rule.name}' 규칙을 삭제하시겠습니까?`)) return;

    try {
      await api.deleteRule(rule.id);
      await loadData();
    } catch (err) {
      alert('삭제 실패: ' + err.message);
    }
  }

  async function toggleRule(rule) {
    try {
      await api.updateRule(rule.id, { enabled: !rule.enabled });
      await loadData();
    } catch (err) {
      alert('변경 실패: ' + err.message);
    }
  }

  onMount(loadData);
</script>

<div class="p-6 space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-text-primary">태그 관리</h1>
      <p class="text-sm text-text-secondary mt-1">태그와 분류 규칙을 관리합니다</p>
    </div>
  </div>

  <!-- Error Banner -->
  {#if error}
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
      데이터 로드 실패: {error}
    </div>
  {/if}

  <!-- Tags Section -->
  <div class="bg-bg-card rounded-xl border border-border">
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">태그 목록</h2>
      <button
        class="px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
        on:click={() => openTagModal()}
      >
        + 태그 추가
      </button>
    </div>

    {#if loading}
      <div class="p-8 text-center text-text-muted">로딩 중...</div>
    {:else}
      <div class="grid grid-cols-4 gap-4 p-5">
        {#each tags as tag}
          <div class="bg-bg-secondary rounded-lg p-4 border border-border hover:border-border-light transition-colors">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-3">
                <div class="w-4 h-4 rounded-full" style="background-color: {tag.color}"></div>
                <span class="font-medium text-text-primary">{tag.name}</span>
              </div>
              <div class="flex items-center gap-1">
                <button
                  aria-label="수정"
                  class="p-1.5 rounded hover:bg-bg-hover transition-colors"
                  on:click={() => openTagModal(tag)}
                >
                  <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
                <button
                  aria-label="삭제"
                  class="p-1.5 rounded hover:bg-bg-hover transition-colors"
                  on:click={() => deleteTag(tag)}
                >
                  <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="text-sm text-text-muted">{tag.rule_count || 0}개 규칙</div>
          </div>
        {:else}
          <div class="col-span-4 text-center text-text-muted py-8">태그가 없습니다</div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Rules Section -->
  <div class="bg-bg-card rounded-xl border border-border">
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">분류 규칙</h2>
      <button
        class="px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
        on:click={() => openRuleModal()}
      >
        + 규칙 추가
      </button>
    </div>

    {#if loading}
      <div class="p-8 text-center text-text-muted">로딩 중...</div>
    {:else if rules.length === 0}
      <div class="p-8 text-center text-text-muted">규칙이 없습니다</div>
    {:else}
      <table class="w-full table-fixed">
        <thead class="bg-bg-secondary">
          <tr>
            <th class="w-16 px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">상태</th>
            <th class="w-16 px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">우선</th>
            <th class="w-28 px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">이름</th>
            <th class="w-20 px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">태그</th>
            <th class="px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">프로세스</th>
            <th class="px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">URL 패턴</th>
            <th class="w-20 px-3 py-3 text-left text-xs font-medium text-text-muted uppercase">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          {#each rules as rule}
            <tr class="hover:bg-bg-hover transition-colors">
              <td class="px-3 py-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    on:change={() => toggleRule(rule)}
                    class="sr-only peer"
                  >
                  <div class="w-9 h-5 bg-bg-tertiary rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                </label>
              </td>
              <td class="px-3 py-3 text-sm text-text-primary">{rule.priority}</td>
              <td class="px-3 py-3 text-sm text-text-primary font-medium truncate" title={rule.name}>{rule.name}</td>
              <td class="px-3 py-3">
                <span
                  class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white whitespace-nowrap"
                  style="background-color: {rule.tag?.color || '#607D8B'}"
                >
                  {rule.tag?.name || rule.tag_name || '미분류'}
                </span>
              </td>
              <td class="px-3 py-3 text-sm text-text-secondary font-mono truncate" title={rule.process_pattern || ''}>{rule.process_pattern || '-'}</td>
              <td class="px-3 py-3 text-sm text-text-secondary font-mono truncate" title={rule.url_pattern || ''}>{rule.url_pattern || '-'}</td>
              <td class="px-3 py-3">
                <div class="flex items-center gap-1">
                  <button
                    aria-label="수정"
                    class="p-1.5 rounded hover:bg-bg-secondary transition-colors"
                    on:click={() => openRuleModal(rule)}
                  >
                    <svg class="w-4 h-4 text-text-muted hover:text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  <button
                    aria-label="삭제"
                    class="p-1.5 rounded hover:bg-bg-secondary transition-colors"
                    on:click={() => deleteRule(rule)}
                  >
                    <svg class="w-4 h-4 text-red-400 hover:text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

<!-- Tag Modal -->
{#if showTagModal}
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" on:click={() => showTagModal = false}>
    <div class="bg-bg-card rounded-xl p-6 w-96 border border-border" on:click|stopPropagation>
      <h3 class="text-lg font-semibold text-text-primary mb-4">
        {editingTag ? '태그 수정' : '태그 추가'}
      </h3>

      <div class="space-y-4">
        <div>
          <label class="block text-sm text-text-secondary mb-1">이름</label>
          <input
            type="text"
            bind:value={tagForm.name}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent focus:ring-1 focus:ring-accent outline-none"
            placeholder="태그 이름"
          />
        </div>
        <div>
          <label class="block text-sm text-text-secondary mb-1">색상</label>
          <div class="flex items-center gap-3">
            <input
              type="color"
              bind:value={tagForm.color}
              class="w-12 h-10 rounded border border-border cursor-pointer"
            />
            <input
              type="text"
              bind:value={tagForm.color}
              class="flex-1 px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm"
            />
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button
          class="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
          on:click={() => showTagModal = false}
        >
          취소
        </button>
        <button
          class="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          on:click={saveTag}
        >
          저장
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Rule Modal -->
{#if showRuleModal}
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" on:click={() => showRuleModal = false}>
    <div class="bg-bg-card rounded-xl p-6 w-[500px] border border-border" on:click|stopPropagation>
      <h3 class="text-lg font-semibold text-text-primary mb-4">
        {editingRule ? '규칙 수정' : '규칙 추가'}
      </h3>

      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-text-secondary mb-1">이름</label>
            <input
              type="text"
              bind:value={ruleForm.name}
              class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent outline-none"
              placeholder="규칙 이름"
            />
          </div>
          <div>
            <label class="block text-sm text-text-secondary mb-1">태그</label>
            <select
              bind:value={ruleForm.tag_id}
              class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent outline-none"
            >
              {#each tags as tag}
                <option value={tag.id}>{tag.name}</option>
              {/each}
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-text-secondary mb-1">우선순위</label>
            <input
              type="number"
              bind:value={ruleForm.priority}
              min="0"
              max="100"
              class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary focus:border-accent outline-none"
            />
          </div>
          <div class="flex items-center pt-6">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" bind:checked={ruleForm.enabled} class="w-4 h-4 rounded border-border bg-bg-tertiary text-accent">
              <span class="text-sm text-text-secondary">활성화</span>
            </label>
          </div>
        </div>

        <div>
          <label class="block text-sm text-text-secondary mb-1">프로세스 패턴</label>
          <input
            type="text"
            bind:value={ruleForm.process_pattern}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm focus:border-accent outline-none"
            placeholder="예: chrome.exe, *code*.exe"
          />
        </div>

        <div>
          <label class="block text-sm text-text-secondary mb-1">URL 패턴</label>
          <input
            type="text"
            bind:value={ruleForm.url_pattern}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm focus:border-accent outline-none"
            placeholder="예: *youtube.com*, *github.com*"
          />
        </div>

        <div>
          <label class="block text-sm text-text-secondary mb-1">창 제목 패턴</label>
          <input
            type="text"
            bind:value={ruleForm.window_title_pattern}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm focus:border-accent outline-none"
            placeholder="예: *Visual Studio*"
          />
        </div>

        <div>
          <label class="block text-sm text-text-secondary mb-1">Chrome 프로필</label>
          <input
            type="text"
            bind:value={ruleForm.chrome_profile}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm focus:border-accent outline-none"
            placeholder="예: Profile 1, Default"
          />
        </div>

        <div>
          <label class="block text-sm text-text-secondary mb-1">프로세스 경로 패턴</label>
          <input
            type="text"
            bind:value={ruleForm.process_path_pattern}
            class="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-text-primary font-mono text-sm focus:border-accent outline-none"
            placeholder="예: *\\Obsidian\\*, *\\AnkiProgramFiles\\*"
          />
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button
          class="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
          on:click={() => showRuleModal = false}
        >
          취소
        </button>
        <button
          class="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          on:click={saveRule}
        >
          저장
        </button>
      </div>
    </div>
  </div>
{/if}
