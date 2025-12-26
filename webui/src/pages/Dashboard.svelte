<script>
  import { onMount } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import { selectedDate, formattedDate, formatDuration } from '../lib/stores/app.js';

  Chart.register(...registerables);

  // Demo data for development
  let tagStats = [
    { id: 1, name: '업무', color: '#4CAF50', duration: 14400, percentage: 60 },
    { id: 2, name: '딴짓', color: '#FF5722', duration: 4800, percentage: 20 },
    { id: 3, name: '자리비움', color: '#9E9E9E', duration: 2400, percentage: 10 },
    { id: 4, name: '미분류', color: '#607D8B', duration: 2400, percentage: 10 }
  ];

  let processStats = [
    { name: 'chrome.exe', duration: 9600, percentage: 40 },
    { name: 'Code.exe', duration: 7200, percentage: 30 },
    { name: 'explorer.exe', duration: 4800, percentage: 20 },
    { name: 'Discord.exe', duration: 2400, percentage: 10 }
  ];

  let hourlyData = Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    업무: Math.random() * 50 + 10,
    딴짓: Math.random() * 20
  }));

  let summaryStats = {
    totalTime: 24000,
    activityCount: 156,
    firstActivity: '09:15',
    lastActivity: '18:45',
    tagSwitches: 42
  };

  let pieChart;
  let barChart;

  onMount(() => {
    // Pie Chart
    const pieCtx = document.getElementById('tagPieChart');
    if (pieCtx) {
      pieChart = new Chart(pieCtx, {
        type: 'doughnut',
        data: {
          labels: tagStats.map(t => t.name),
          datasets: [{
            data: tagStats.map(t => t.duration),
            backgroundColor: tagStats.map(t => t.color),
            borderWidth: 0,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '65%',
          plugins: {
            legend: {
              display: false
            }
          }
        }
      });
    }

    // Hourly Bar Chart
    const barCtx = document.getElementById('hourlyBarChart');
    if (barCtx) {
      barChart = new Chart(barCtx, {
        type: 'bar',
        data: {
          labels: hourlyData.map(d => `${d.hour}시`),
          datasets: [
            {
              label: '업무',
              data: hourlyData.map(d => d.업무),
              backgroundColor: '#4CAF50',
              borderRadius: 4
            },
            {
              label: '딴짓',
              data: hourlyData.map(d => d.딴짓),
              backgroundColor: '#FF5722',
              borderRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              stacked: true,
              grid: { display: false },
              ticks: { color: '#666' }
            },
            y: {
              stacked: true,
              grid: { color: '#333' },
              ticks: { color: '#666' }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              labels: { color: '#a0a0a0', usePointStyle: true }
            }
          }
        }
      });
    }

    return () => {
      pieChart?.destroy();
      barChart?.destroy();
    };
  });
</script>

<div class="p-6 space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-text-primary">대시보드</h1>
      <p class="text-sm text-text-secondary mt-1">{$formattedDate}</p>
    </div>
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

  <!-- Summary Cards -->
  <div class="grid grid-cols-5 gap-4">
    <div class="bg-bg-card rounded-xl p-4 border border-border">
      <div class="text-text-muted text-xs uppercase tracking-wide mb-1">총 활동 시간</div>
      <div class="text-2xl font-bold text-text-primary">{formatDuration(summaryStats.totalTime)}</div>
    </div>
    <div class="bg-bg-card rounded-xl p-4 border border-border">
      <div class="text-text-muted text-xs uppercase tracking-wide mb-1">활동 횟수</div>
      <div class="text-2xl font-bold text-text-primary">{summaryStats.activityCount}회</div>
    </div>
    <div class="bg-bg-card rounded-xl p-4 border border-border">
      <div class="text-text-muted text-xs uppercase tracking-wide mb-1">첫 활동</div>
      <div class="text-2xl font-bold text-text-primary">{summaryStats.firstActivity}</div>
    </div>
    <div class="bg-bg-card rounded-xl p-4 border border-border">
      <div class="text-text-muted text-xs uppercase tracking-wide mb-1">마지막 활동</div>
      <div class="text-2xl font-bold text-text-primary">{summaryStats.lastActivity}</div>
    </div>
    <div class="bg-bg-card rounded-xl p-4 border border-border">
      <div class="text-text-muted text-xs uppercase tracking-wide mb-1">태그 전환</div>
      <div class="text-2xl font-bold text-text-primary">{summaryStats.tagSwitches}회</div>
    </div>
  </div>

  <!-- Charts Row -->
  <div class="grid grid-cols-3 gap-6">
    <!-- Tag Distribution (Pie) -->
    <div class="bg-bg-card rounded-xl p-5 border border-border">
      <h2 class="text-lg font-semibold text-text-primary mb-4">태그별 시간</h2>
      <div class="relative h-48">
        <canvas id="tagPieChart"></canvas>
      </div>
      <div class="mt-4 space-y-2">
        {#each tagStats as tag}
          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full" style="background-color: {tag.color}"></div>
              <span class="text-text-secondary">{tag.name}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-text-primary font-medium">{formatDuration(tag.duration)}</span>
              <span class="text-text-muted w-12 text-right">{tag.percentage}%</span>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Hourly Distribution (Bar) -->
    <div class="col-span-2 bg-bg-card rounded-xl p-5 border border-border">
      <h2 class="text-lg font-semibold text-text-primary mb-4">시간대별 활동</h2>
      <div class="h-64">
        <canvas id="hourlyBarChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Process Stats -->
  <div class="bg-bg-card rounded-xl p-5 border border-border">
    <h2 class="text-lg font-semibold text-text-primary mb-4">프로세스별 사용 시간</h2>
    <div class="space-y-3">
      {#each processStats as proc}
        <div class="flex items-center gap-4">
          <span class="w-32 text-sm text-text-secondary truncate">{proc.name}</span>
          <div class="flex-1 h-6 bg-bg-tertiary rounded-lg overflow-hidden">
            <div
              class="h-full bg-accent rounded-lg transition-all duration-500"
              style="width: {proc.percentage}%"
            ></div>
          </div>
          <span class="w-20 text-sm text-text-primary text-right">{formatDuration(proc.duration)}</span>
          <span class="w-12 text-sm text-text-muted text-right">{proc.percentage}%</span>
        </div>
      {/each}
    </div>
  </div>
</div>
