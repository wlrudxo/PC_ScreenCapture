<script>
  import { selectedDate, formattedDate, formatDuration, formatTime } from '../lib/stores/app.js';

  // Demo data
  let activities = [
    { id: 1, startTime: '2024-01-15T09:00:00', endTime: '2024-01-15T09:30:00', processName: 'chrome.exe', windowTitle: 'GitHub - Project', chromeUrl: 'https://github.com/project', tag: { name: '업무', color: '#4CAF50' } },
    { id: 2, startTime: '2024-01-15T09:30:00', endTime: '2024-01-15T10:00:00', processName: 'Code.exe', windowTitle: 'main.py - VS Code', chromeUrl: null, tag: { name: '업무', color: '#4CAF50' } },
    { id: 3, startTime: '2024-01-15T10:00:00', endTime: '2024-01-15T10:15:00', processName: 'chrome.exe', windowTitle: 'YouTube', chromeUrl: 'https://youtube.com', tag: { name: '딴짓', color: '#FF5722' } },
    { id: 4, startTime: '2024-01-15T10:15:00', endTime: '2024-01-15T11:00:00', processName: 'Code.exe', windowTitle: 'api.py - VS Code', chromeUrl: null, tag: { name: '업무', color: '#4CAF50' } },
  ];

  let selectedTag = null;
  let tags = [
    { id: 1, name: '업무', color: '#4CAF50' },
    { id: 2, name: '딴짓', color: '#FF5722' },
    { id: 3, name: '자리비움', color: '#9E9E9E' },
    { id: 4, name: '미분류', color: '#607D8B' }
  ];

  function getActivityDuration(activity) {
    const start = new Date(activity.startTime);
    const end = activity.endTime ? new Date(activity.endTime) : new Date();
    return Math.floor((end - start) / 1000);
  }

  // Generate timeline bar segments
  function getTimelineSegments() {
    const segments = [];
    const dayStart = 9 * 60; // 9 AM in minutes
    const dayEnd = 18 * 60;  // 6 PM in minutes
    const totalMinutes = dayEnd - dayStart;

    activities.forEach(activity => {
      const start = new Date(activity.startTime);
      const end = activity.endTime ? new Date(activity.endTime) : new Date();

      const startMinutes = start.getHours() * 60 + start.getMinutes();
      const endMinutes = end.getHours() * 60 + end.getMinutes();

      const left = Math.max(0, ((startMinutes - dayStart) / totalMinutes) * 100);
      const width = Math.min(100 - left, ((endMinutes - startMinutes) / totalMinutes) * 100);

      segments.push({
        left: `${left}%`,
        width: `${Math.max(width, 0.5)}%`,
        color: activity.tag.color,
        activity
      });
    });

    return segments;
  }
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
        bind:value={selectedTag}
        class="px-3 py-2 rounded-lg bg-bg-secondary border border-border text-text-primary text-sm"
      >
        <option value={null}>모든 태그</option>
        {#each tags as tag}
          <option value={tag.id}>{tag.name}</option>
        {/each}
      </select>

      <!-- Date Navigation -->
      <div class="flex items-center gap-2">
        <button class="p-2 rounded-lg bg-bg-secondary border border-border hover:bg-bg-hover transition-colors">
          <svg class="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <input
          type="date"
          bind:value={$selectedDate}
          class="px-3 py-2 rounded-lg bg-bg-secondary border border-border text-text-primary text-sm"
        />
        <button class="p-2 rounded-lg bg-bg-secondary border border-border hover:bg-bg-hover transition-colors">
          <svg class="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Timeline Bar -->
  <div class="bg-bg-card rounded-xl p-5 border border-border">
    <h2 class="text-lg font-semibold text-text-primary mb-4">일간 타임라인</h2>

    <!-- Time labels -->
    <div class="flex justify-between text-xs text-text-muted mb-2 px-1">
      {#each Array(10) as _, i}
        <span>{9 + i}시</span>
      {/each}
    </div>

    <!-- Timeline bar -->
    <div class="relative h-10 bg-bg-tertiary rounded-lg overflow-hidden">
      {#each getTimelineSegments() as segment}
        <div
          class="absolute top-0 h-full cursor-pointer hover:brightness-110 transition-all"
          style="left: {segment.left}; width: {segment.width}; background-color: {segment.color}"
          title="{segment.activity.processName} - {formatTime(segment.activity.startTime)}"
        ></div>
      {/each}
    </div>
  </div>

  <!-- Activity Table -->
  <div class="bg-bg-card rounded-xl border border-border overflow-hidden">
    <div class="px-5 py-4 border-b border-border">
      <h2 class="text-lg font-semibold text-text-primary">활동 기록</h2>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-bg-secondary">
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
                {formatTime(activity.startTime)} - {formatTime(activity.endTime)}
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
              <td class="px-4 py-3 text-sm text-text-secondary">{activity.processName}</td>
              <td class="px-4 py-3 text-sm text-text-secondary max-w-xs truncate">{activity.windowTitle}</td>
              <td class="px-4 py-3 text-sm text-text-muted max-w-xs truncate">
                {activity.chromeUrl || '-'}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</div>
