<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client.js';
  import { selectedDate, formattedDate, formatDuration, formatTime } from '../lib/stores/app.js';

  let loading = true;
  let error = null;
  let activities = [];
  let tags = [];
  let selectedTag = null;

  // 날짜/태그 변경 시 데이터 다시 로드
  $: loadTimelineData($selectedDate, selectedTag);

  async function loadTimelineData(date, tagId) {
    loading = true;
    error = null;

    try {
      const [timelineRes, tagsRes] = await Promise.all([
        api.getTimeline(date, tagId),
        api.getTags()
      ]);

      activities = (timelineRes.activities || []).map(act => ({
        ...act,
        tag: {
          name: act.tag_name || '미분류',
          color: act.tag_color || '#607D8B'
        }
      }));

      tags = tagsRes.tags || [];

    } catch (err) {
      console.error('Failed to load timeline:', err);
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function getActivityDuration(activity) {
    if (!activity.start_time) return 0;
    const start = new Date(activity.start_time);
    const end = activity.end_time ? new Date(activity.end_time) : new Date();
    return Math.floor((end - start) / 1000);
  }

  function getTimelineSegments() {
    if (activities.length === 0) return [];

    const dayStart = 0;       // 0 AM (midnight)
    const dayEnd = 24 * 60;   // 24:00 (midnight)
    const totalMinutes = dayEnd - dayStart;
    const MERGE_GAP_THRESHOLD = 10; // 10초 이상 갭이면 병합 안함

    // 시간순 정렬
    const sorted = [...activities]
      .filter(a => a.start_time)
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    // 동일 태그 + 시간 갭 < 10초면 병합
    const merged = [];
    for (const activity of sorted) {
      const tagId = activity.tag_id;
      const start = new Date(activity.start_time);
      const end = activity.end_time ? new Date(activity.end_time) : new Date();

      const last = merged[merged.length - 1];
      if (last && last.tag_id === tagId) {
        // 이전 활동 종료 ~ 현재 활동 시작 간격 계산
        const gap = (start - last.end) / 1000; // seconds
        if (gap < MERGE_GAP_THRESHOLD) {
          // 병합: 끝 시간만 확장
          last.end = end;
          continue;
        }
      }

      merged.push({
        tag_id: tagId,
        start,
        end,
        color: activity.tag?.color || '#607D8B',
        activity
      });
    }

    // 세그먼트 변환
    const segments = [];
    for (const item of merged) {
      const startMinutes = item.start.getHours() * 60 + item.start.getMinutes();
      const endMinutes = item.end.getHours() * 60 + item.end.getMinutes();

      const clampedStart = Math.max(dayStart, Math.min(dayEnd, startMinutes));
      const clampedEnd = Math.max(dayStart, Math.min(dayEnd, endMinutes));

      if (clampedEnd <= clampedStart) continue;

      const left = ((clampedStart - dayStart) / totalMinutes) * 100;
      const width = ((clampedEnd - clampedStart) / totalMinutes) * 100;

      segments.push({
        left: `${left}%`,
        width: `${Math.max(width, 0.5)}%`,
        color: item.color,
        activity: item.activity
      });
    }

    return segments;
  }

  function changeDate(delta) {
    const current = new Date($selectedDate);
    current.setDate(current.getDate() + delta);
    $selectedDate = current.toISOString().split('T')[0];
  }

  function handleTagFilter(event) {
    const value = event.target.value;
    selectedTag = value === '' ? null : parseInt(value);
  }

  onMount(() => {
    loadTimelineData($selectedDate, selectedTag);
  });
</script>

<div class="p-6 space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-text-primary">타임라인</h1>
      <p class="text-sm text-text-secondary mt-1">{$formattedDate}</p>
    </div>
    <div class="flex items-center gap-4">
      <!-- Tag Filter -->
      <select
        on:change={handleTagFilter}
        class="px-3 py-2 rounded-lg bg-bg-secondary border border-border text-text-primary text-sm"
      >
        <option value="">모든 태그</option>
        {#each tags as tag}
          <option value={tag.id}>{tag.name}</option>
        {/each}
      </select>

      <!-- Date Navigation -->
      <div class="flex items-center gap-2">
        <button
          aria-label="이전 날짜"
          class="p-2 rounded-lg bg-bg-secondary border border-border hover:bg-bg-hover transition-colors"
          on:click={() => changeDate(-1)}
        >
          <svg class="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <input
          type="date"
          bind:value={$selectedDate}
          class="px-3 py-2 rounded-lg bg-bg-secondary border border-border text-text-primary text-sm"
        />
        <button
          aria-label="다음 날짜"
          class="p-2 rounded-lg bg-bg-secondary border border-border hover:bg-bg-hover transition-colors"
          on:click={() => changeDate(1)}
        >
          <svg class="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Error Banner -->
  {#if error}
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
      데이터 로드 실패: {error}
    </div>
  {/if}

  <!-- Timeline Bar -->
  <div class="bg-bg-card rounded-xl p-5 border border-border">
    <h2 class="text-lg font-semibold text-text-primary mb-4">일간 타임라인</h2>

    <!-- Time labels -->
    <div class="flex justify-between text-xs text-text-muted mb-2 px-1">
      {#each [0, 3, 6, 9, 12, 15, 18, 21, 24] as hour}
        <span>{hour}시</span>
      {/each}
    </div>

    <!-- Timeline bar -->
    <div class="relative h-10 bg-bg-tertiary rounded-lg overflow-hidden">
      {#if loading}
        <div class="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
          로딩 중...
        </div>
      {:else if getTimelineSegments().length === 0}
        <div class="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
          활동 없음
        </div>
      {:else}
        {#each getTimelineSegments() as segment}
          <div
            class="absolute top-0 h-full cursor-pointer hover:brightness-110 transition-all"
            style="left: {segment.left}; width: {segment.width}; background-color: {segment.color}"
            title="{segment.activity.process_name} - {formatTime(segment.activity.start_time)}"
          ></div>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Activity Table -->
  <div class="bg-bg-card rounded-xl border border-border overflow-hidden">
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">활동 기록</h2>
      <span class="text-sm text-text-muted">{activities.length}개</span>
    </div>

    {#if loading}
      <div class="p-8 text-center text-text-muted">로딩 중...</div>
    {:else if activities.length === 0}
      <div class="p-8 text-center text-text-muted">활동 기록이 없습니다</div>
    {:else}
      <div class="overflow-x-auto max-h-96">
        <table class="w-full">
          <thead class="bg-bg-secondary sticky top-0">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">시간</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">기간</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">태그</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">프로세스</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">창 제목</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">URL</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            {#each activities as activity}
              <tr class="hover:bg-bg-hover transition-colors">
                <td class="px-4 py-3 text-sm text-text-primary whitespace-nowrap">
                  {formatTime(activity.start_time)} - {activity.end_time ? formatTime(activity.end_time) : '진행중'}
                </td>
                <td class="px-4 py-3 text-sm text-text-secondary whitespace-nowrap">
                  {formatDuration(getActivityDuration(activity))}
                </td>
                <td class="px-4 py-3">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white"
                    style="background-color: {activity.tag.color}"
                  >
                    {activity.tag.name}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm text-text-secondary">{activity.process_name || '-'}</td>
                <td class="px-4 py-3 text-sm text-text-secondary max-w-xs truncate" title={activity.window_title}>
                  {activity.window_title || '-'}
                </td>
                <td class="px-4 py-3 text-sm text-text-muted max-w-xs truncate" title={activity.chrome_url}>
                  {activity.chrome_url || '-'}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
