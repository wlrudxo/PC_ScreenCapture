import { writable, derived } from 'svelte/store';

// Current activity from WebSocket
export const currentActivity = writable(null);

// Tags list
export const tags = writable([]);

// Selected date for dashboard/timeline
export const selectedDate = writable(new Date().toISOString().split('T')[0]);

// Loading states
export const isLoading = writable(false);

// Error state
export const error = writable(null);

// Dashboard stats
export const dashboardStats = writable({
  tagStats: [],
  processStats: [],
  totalTime: 0,
  activityCount: 0
});

// Timeline data
export const timelineData = writable([]);

// Settings
export const settings = writable({});

// Derived: formatted current time
export const formattedDate = derived(selectedDate, ($date) => {
  const d = new Date($date);
  return d.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short'
  });
});

// Helper to format duration (hours and minutes only)
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '0초';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return minutes > 0 ? `${hours}시간 ${minutes}분` : `${hours}시간`;
  }
  if (minutes > 0) {
    return secs > 0 ? `${minutes}분 ${secs}초` : `${minutes}분`;
  }
  return `${secs}초`;
}

// Helper to format time (24h with seconds)
export function formatTime(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

// Helper to get tag color with fallback
export function getTagColor(tag) {
  return tag?.color || '#607D8B';
}
