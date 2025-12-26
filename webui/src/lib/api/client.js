/**
 * API 기본 URL 결정
 * - file:// 프로토콜: PyWebView에서 로드, 절대 경로 사용
 * - http(s)://: 개발 서버나 프록시 사용, 상대 경로 사용
 */
function getApiBase() {
  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
}

const API_BASE = getApiBase();

/**
 * Fetch wrapper with error handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

export const api = {
  // Dashboard
  getDashboardDaily: (date) => request(`/dashboard/daily?date=${date}`),
  getDashboardPeriod: (start, end) => request(`/dashboard/period?start=${start}&end=${end}`),
  getDashboardHourly: (date) => request(`/dashboard/hourly?date=${date}`),

  // Timeline
  getTimeline: (date, tagId = null) => {
    let url = `/timeline?date=${date}`;
    if (tagId) url += `&tag_id=${tagId}`;
    return request(url);
  },

  // Tags
  getTags: () => request('/tags'),
  createTag: (data) => request('/tags', { method: 'POST', body: JSON.stringify(data) }),
  updateTag: (id, data) => request(`/tags/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTag: (id) => request(`/tags/${id}`, { method: 'DELETE' }),

  // Rules
  getRules: () => request('/rules'),
  createRule: (data) => request('/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) => request(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRule: (id) => request(`/rules/${id}`, { method: 'DELETE' }),

  // Reclassify
  reclassifyUntagged: () => request('/reclassify/untagged', { method: 'POST' }),
  reclassifyAll: () => request('/reclassify/all', { method: 'POST' }),
  getUnclassifiedActivities: () => request('/activities/unclassified'),
  deleteActivities: (ids) => request('/activities/delete', { method: 'POST', body: JSON.stringify({ ids }) }),

  // Settings
  getSettings: () => request('/settings'),
  updateSettings: (data) => request('/settings', { method: 'PUT', body: JSON.stringify(data) }),

  // Alerts
  getAlertSounds: () => request('/alerts/sounds'),
  getAlertImages: () => request('/alerts/images'),
  testAlert: (tagId) => request(`/alerts/test/${tagId}`, { method: 'POST' }),

  // Focus
  getFocusSettings: () => request('/focus'),
  updateFocusSettings: (tagId, data) => request(`/focus/${tagId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Import/Export
  exportData: () => request('/data/export'),
  importData: (data) => request('/data/import', { method: 'POST', body: JSON.stringify(data) })
};

/**
 * WebSocket connection for real-time updates
 */
export function createWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/activity`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket closed, reconnecting in 3s...');
    setTimeout(() => createWebSocket(onMessage), 3000);
  };

  return ws;
}
