import { writable } from 'svelte/store';

// WebSocket 연결 상태
export const wsConnected = writable(false);

// 업데이트 이벤트 (컴포넌트에서 구독)
export const activityUpdated = writable(0);

let ws = null;
let reconnectTimeout = null;
let pingInterval = null;

/**
 * WebSocket 연결 시작
 */
/**
 * WebSocket URL 결정
 * - file:// 프로토콜: PyWebView에서 로드, 절대 경로 사용
 * - http(s)://: 개발 서버, 현재 호스트 사용
 */
function getWsUrl() {
  if (window.location.protocol === 'file:') {
    return 'ws://127.0.0.1:8000/ws/activity';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/activity`;
}

export function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    return;
  }

  const wsUrl = getWsUrl();

  console.log('[WebSocket] Connecting to', wsUrl);

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      wsConnected.set(true);

      // Ping 시작 (30초마다)
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') {
        return; // ping 응답 무시
      }

      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] Received:', data);

        if (data.type === 'activity_update') {
          // 업데이트 카운터 증가 (컴포넌트에서 반응하도록)
          activityUpdated.update(n => n + 1);
        }
      } catch (err) {
        console.error('[WebSocket] Parse error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      wsConnected.set(false);
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
      wsConnected.set(false);

      if (pingInterval) {
        clearInterval(pingInterval);
        pingInterval = null;
      }

      // 3초 후 재연결
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(() => {
        console.log('[WebSocket] Reconnecting...');
        connectWebSocket();
      }, 3000);
    };

  } catch (err) {
    console.error('[WebSocket] Connection failed:', err);
    wsConnected.set(false);
  }
}

/**
 * WebSocket 연결 종료
 */
export function disconnectWebSocket() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  if (pingInterval) {
    clearInterval(pingInterval);
    pingInterval = null;
  }

  if (ws) {
    ws.close();
    ws = null;
  }

  wsConnected.set(false);
}
