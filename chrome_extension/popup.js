// DOM 요소
const profileNameInput = document.getElementById('profileName');
const saveBtn = document.getElementById('saveBtn');
const currentProfileSpan = document.getElementById('currentProfile');
const statusDiv = document.getElementById('status');

// 페이지 로드 시 저장된 프로필 불러오기
chrome.storage.local.get(['profileName'], (result) => {
  if (result.profileName) {
    profileNameInput.value = result.profileName;
    currentProfileSpan.textContent = result.profileName;
    updateStatus('connected', `✅ "${result.profileName}" 프로필로 추적 중`);
  } else {
    updateStatus('not-set', '⚠️ 프로필 이름을 설정해주세요');
  }
});

// 저장 버튼 클릭
saveBtn.addEventListener('click', () => {
  const profileName = profileNameInput.value.trim();

  if (!profileName) {
    alert('프로필 이름을 입력해주세요!');
    return;
  }

  // chrome.storage에 저장
  chrome.storage.local.set({ profileName: profileName }, () => {
    currentProfileSpan.textContent = profileName;
    updateStatus('connected', `✅ "${profileName}" 프로필로 저장됨`);

    // background.js에 프로필 변경 알림
    chrome.runtime.sendMessage({
      type: 'profile_updated',
      profileName: profileName
    });

    // 0.5초 후 팝업 닫기
    setTimeout(() => {
      window.close();
    }, 500);
  });
});

// Enter 키로도 저장 가능
profileNameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    saveBtn.click();
  }
});

// 상태 표시 업데이트
function updateStatus(type, message) {
  statusDiv.className = `status ${type}`;
  statusDiv.textContent = message;
}
