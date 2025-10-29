// WebSocket 연결
let ws = null;
let profileName = null;

// 저장된 프로필 이름 불러오기
chrome.storage.local.get(['profileName'], (result) => {
  if (result.profileName) {
    profileName = result.profileName;
    console.log(`[Activity Tracker] 프로필 로드: "${profileName}"`);
  } else {
    console.warn('[Activity Tracker] ⚠️ 프로필이 설정되지 않았습니다. 확장 프로그램 아이콘을 클릭해서 설정하세요.');
  }
});

// popup에서 프로필 변경 메시지 수신
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'profile_updated') {
    profileName = message.profileName;
    console.log(`[Activity Tracker] 프로필 업데이트: "${profileName}"`);
  }
});

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8766');

  ws.onopen = () => {
    console.log('[Activity Tracker] ✅ WebSocket 연결됨');
  };

  ws.onclose = () => {
    console.log('[Activity Tracker] ❌ WebSocket 연결 끊김, 5초 후 재연결...');
    setTimeout(connectWebSocket, 5000);
  };

  ws.onerror = (error) => {
    console.error('[Activity Tracker] WebSocket 에러:', error);
  };
}

// 탭 업데이트 감지
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // URL이나 제목이 변경되었을 때만 전송
  if (changeInfo.url || changeInfo.title) {
    sendUrlToServer(tabId, tab.url, tab.title);
  }
});

// 활성 탭 변경 감지
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  sendUrlToServer(activeInfo.tabId, tab.url, tab.title);
});

// 창 포커스 변경 감지
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    return; // Chrome이 포커스를 잃음
  }

  const [activeTab] = await chrome.tabs.query({ active: true, windowId: windowId });
  if (activeTab) {
    sendUrlToServer(activeTab.id, activeTab.url, activeTab.title);
  }
});

function sendUrlToServer(tabId, url, title) {
  // WebSocket이 끊어져 있으면 즉시 재연결 시도
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.log('[Activity Tracker] ⚠️ WebSocket 끊김 감지, 즉시 재연결 시도...');
    connectWebSocket();
    return;
  }

  const data = {
    type: 'url_change',
    profileName: profileName || 'Unknown',
    tabId: tabId,
    url: url,
    title: title,
    timestamp: Date.now()
  };

  ws.send(JSON.stringify(data));
  console.log(`[Activity Tracker] 📤 [${profileName || 'Unknown'}] URL 전송:`, url);
}

// 시작
connectWebSocket();
