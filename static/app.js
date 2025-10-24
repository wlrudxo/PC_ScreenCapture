// 전역 변수
let categories = [];
let currentDate = null;
let allCaptures = [];
let allTags = [];
let currentFilter = 'all';
let currentPage = 1;
const itemsPerPage = 20;

// ========== 초기화 ==========

document.addEventListener('DOMContentLoaded', function() {
    // 현재 페이지 확인
    const path = window.location.pathname;

    if (path === '/' || path === '/index.html') {
        // 타임라인 페이지
        initTimeline();
    } else if (path === '/stats' || path === '/stats.html') {
        // 통계 페이지
        initStats();
    } else if (path === '/settings' || path === '/settings.html') {
        // 설정 페이지
        initSettings();
    }

    // 카테고리 로드
    loadCategories();
});

// ========== 타임라인 페이지 ==========

function initTimeline() {
    // 로컬 스토리지에서 필터 상태 복원
    const savedFilter = localStorage.getItem('captureFilter');
    if (savedFilter && ['all', 'tagged', 'untagged'].includes(savedFilter)) {
        currentFilter = savedFilter;

        // 필터 버튼 활성화 상태 업데이트
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        const filterBtn = document.querySelector(`.filter-btn[data-filter="${savedFilter}"]`);
        if (filterBtn) {
            filterBtn.classList.add('active');
        }
    }

    loadDates();
}

async function loadDates() {
    try {
        const response = await fetch('/api/dates');
        const data = await response.json();

        if (data.success) {
            renderDateList(data.dates);
        } else {
            showError('날짜 목록을 불러오는데 실패했습니다.');
        }
    } catch (error) {
        showError('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

function renderDateList(dates) {
    const dateList = document.getElementById('dateList');

    if (dates.length === 0) {
        dateList.innerHTML = '<p class="info-message">캡처된 날짜가 없습니다.</p>';
        return;
    }

    dateList.innerHTML = dates.map(date =>
        `<div class="date-item" onclick="selectDate('${date}', this)">${date}</div>`
    ).join('');

    // 오늘 날짜 계산 (YYYY-MM-DD 형식)
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    // 오늘 날짜가 목록에 있으면 선택, 없으면 가장 최근 날짜(첫 번째) 선택
    let dateToSelect = dates.includes(todayStr) ? todayStr : dates[0];

    // 자동으로 날짜 선택
    if (dateToSelect) {
        selectDate(dateToSelect);
    }
}

async function selectDate(date, clickedElement = null) {
    currentDate = date;

    // 활성 상태 표시
    document.querySelectorAll('.date-item').forEach(item => {
        item.classList.remove('active');
    });

    // 클릭된 요소가 있으면 그것을 활성화, 없으면 date로 찾아서 활성화
    if (clickedElement) {
        clickedElement.classList.add('active');
    } else {
        // 모든 date-item을 순회하면서 해당 날짜를 찾아 활성화
        document.querySelectorAll('.date-item').forEach(item => {
            if (item.textContent === date) {
                item.classList.add('active');
            }
        });
    }

    // 헤더 업데이트
    document.getElementById('selectedDate').textContent = date;

    // 캡처 목록 로드
    await loadCaptures(date);
}

async function loadCaptures(date) {
    try {
        // 캡처 목록과 태그 정보 동시 로드
        const [capturesResponse, tagsResponse] = await Promise.all([
            fetch(`/api/captures/${date}`),
            fetch(`/api/tags/${date}`)
        ]);

        const capturesData = await capturesResponse.json();
        const tagsData = await tagsResponse.json();

        if (capturesData.success && tagsData.success) {
            allCaptures = capturesData.captures;
            allTags = tagsData.tags;
            currentPage = 1;
            applyFilterAndRender();
        } else {
            showError('캡처 목록을 불러오는데 실패했습니다.');
        }
    } catch (error) {
        showError('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

function setFilter(filter) {
    currentFilter = filter;
    currentPage = 1;

    // 로컬 스토리지에 필터 상태 저장
    localStorage.setItem('captureFilter', filter);

    // 필터 버튼 활성화 상태 업데이트
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.filter-btn[data-filter="${filter}"]`).classList.add('active');

    applyFilterAndRender();
}

function applyFilterAndRender() {
    if (allCaptures.length === 0) {
        document.getElementById('captureGrid').innerHTML = '<p class="info-message">이 날짜의 캡처가 없습니다.</p>';
        updatePagination(0, 0);
        return;
    }

    // 태그를 타임스탬프로 매핑
    const tagMap = {};
    allTags.forEach(tag => {
        const tagTime = new Date(tag.timestamp).getTime();
        tagMap[tagTime] = tag;
    });

    // 필터링
    let filteredCaptures = allCaptures.filter(capture => {
        const captureTime = new Date(capture.timestamp).getTime();
        const isTagged = !!tagMap[captureTime];

        if (currentFilter === 'tagged') return isTagged;
        if (currentFilter === 'untagged') return !isTagged;
        return true; // 'all'
    });

    // 페이지네이션
    const totalPages = Math.ceil(filteredCaptures.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedCaptures = filteredCaptures.slice(startIndex, endIndex);

    renderCaptures(paginatedCaptures, allTags);
    updatePagination(currentPage, totalPages);
}

function updatePagination(page, totalPages) {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const pageInfo = document.getElementById('pageInfo');

    if (totalPages === 0) {
        pageInfo.textContent = '0 / 0';
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
    }

    pageInfo.textContent = `${page} / ${totalPages}`;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= totalPages;
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        applyFilterAndRender();
    }
}

function nextPage() {
    const totalPages = Math.ceil(
        allCaptures.filter(capture => {
            const captureTime = new Date(capture.timestamp).getTime();
            const tagMap = {};
            allTags.forEach(tag => {
                const tagTime = new Date(tag.timestamp).getTime();
                tagMap[tagTime] = tag;
            });
            const isTagged = !!tagMap[captureTime];

            if (currentFilter === 'tagged') return isTagged;
            if (currentFilter === 'untagged') return !isTagged;
            return true;
        }).length / itemsPerPage
    );

    if (currentPage < totalPages) {
        currentPage++;
        applyFilterAndRender();
    }
}

function toggleCapture(captureId) {
    const captureItem = document.querySelector(`.capture-item[data-capture-id="${captureId}"]`);
    captureItem.classList.toggle('collapsed');
}

function renderCaptures(captures, tags = []) {
    const grid = document.getElementById('captureGrid');

    if (captures.length === 0) {
        grid.innerHTML = '<p class="info-message">이 날짜의 캡처가 없습니다.</p>';
        return;
    }

    // 태그를 capture_id로 매핑
    const tagMap = {};
    tags.forEach(tag => {
        tagMap[tag.capture_id] = tag;
    });

    grid.innerHTML = captures.map((capture) => {
        const captureId = capture.capture_id;
        const captureTime = new Date(capture.timestamp);
        const time = captureTime.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const monitorImages = Object.entries(capture.monitors).map(([key, monitor]) => {
            // filepath가 null이면 이미지 삭제됨 표시
            if (!monitor.filepath) {
                return `<div class="deleted-image">이미지 삭제됨 (Monitor ${monitor.monitor_num})</div>`;
            }
            const filepath = monitor.filepath.replace(/\\/g, '/');
            const webPath = filepath.split('data/screenshots/')[1];
            return `<img src="/screenshots/${webPath}" alt="Monitor ${monitor.monitor_num}" onclick="openImage('/screenshots/${webPath}')">`;
        }).join('');

        // 이 캡처에 해당하는 태그 찾기
        const existingTag = tagMap[captureId];

        // 카테고리 버튼 생성
        const categoryButtons = categories.map(cat => {
            const isActive = existingTag && existingTag.category === cat.name ? 'active' : '';
            return `<button class="category-btn ${isActive}" data-capture-id="${captureId}" data-category="${cat.name}" onclick="selectCategory(${captureId}, '${cat.name}')">${cat.name}</button>`;
        }).join('');

        // 활동 버튼 생성 (선택된 카테고리가 있을 때만)
        let activityButtons = '';
        if (existingTag) {
            const category = categories.find(cat => cat.name === existingTag.category);
            if (category) {
                activityButtons = category.activities.map(activity => {
                    const isActive = existingTag.activity === activity ? 'active' : '';
                    return `<button class="activity-btn ${isActive}" data-capture-id="${captureId}" data-activity="${activity}" onclick="selectActivity(${captureId}, '${existingTag.category}', '${activity}')">${activity}</button>`;
                }).join('');
            }
        }

        const isTagged = existingTag ? 'tagged' : '';
        const isCollapsed = existingTag ? 'collapsed' : '';
        const toggleIcon = existingTag ? '<span class="toggle-icon" onclick="toggleCapture(' + captureId + ')">▼</span>' : '';

        return `
            <div class="capture-item ${isTagged} ${isCollapsed}" data-timestamp="${capture.timestamp}" data-capture-id="${captureId}">
                <div class="capture-checkbox">
                    <input type="checkbox" id="check-${captureId}" class="item-checkbox" onchange="updateSelectedCount()">
                </div>
                <div class="capture-time" onclick="toggleCapture(${captureId})">${time}${toggleIcon}</div>
                <div class="monitor-images">
                    ${monitorImages}
                </div>
                <div class="capture-tagging" data-selected-category="${existingTag ? existingTag.category : ''}">
                    <div class="category-buttons">
                        ${categoryButtons}
                    </div>
                    <div class="activity-buttons" ${!existingTag ? 'style="display:none;"' : ''}>
                        ${activityButtons}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function openImage(url) {
    window.open(url, '_blank');
}

// ========== 인라인 태깅 ==========

function selectCategory(captureId, categoryName) {
    const captureItem = document.querySelector(`.capture-item[data-capture-id="${captureId}"]`);
    const taggingDiv = captureItem.querySelector('.capture-tagging');
    const activityButtonsDiv = taggingDiv.querySelector('.activity-buttons');

    // 이미 선택된 카테고리를 다시 클릭하면 숨기기
    const currentCategory = taggingDiv.dataset.selectedCategory;
    if (currentCategory === categoryName && activityButtonsDiv.style.display !== 'none') {
        activityButtonsDiv.style.display = 'none';
        taggingDiv.dataset.selectedCategory = '';

        // 모든 카테고리 버튼 비활성화
        taggingDiv.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        return;
    }

    // 선택된 카테고리 저장
    taggingDiv.dataset.selectedCategory = categoryName;

    // 카테고리 버튼 활성화 상태 업데이트
    taggingDiv.querySelectorAll('.category-btn').forEach(btn => {
        if (btn.dataset.category === categoryName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // 해당 카테고리의 활동 버튼 생성
    const category = categories.find(cat => cat.name === categoryName);
    if (category) {
        const activityButtons = category.activities.map(activity =>
            `<button class="activity-btn" data-capture-id="${captureId}" data-activity="${activity}" onclick="selectActivity(${captureId}, '${categoryName}', '${activity}')">${activity}</button>`
        ).join('');

        activityButtonsDiv.innerHTML = activityButtons;
        activityButtonsDiv.style.display = 'flex';
    }
}

async function selectActivity(captureId, category, activity) {
    const captureItem = document.querySelector(`.capture-item[data-capture-id="${captureId}"]`);
    const taggingDiv = captureItem.querySelector('.capture-tagging');

    // 클릭된 활동 버튼 활성화 표시
    taggingDiv.querySelectorAll('.activity-btn').forEach(btn => {
        if (btn.dataset.activity === activity) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // 태그 저장 (capture_id 기반)
    try {
        const response = await fetch('/api/tags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                capture_id: captureId,
                category: category,
                activity: activity
            })
        });

        const data = await response.json();

        if (data.success) {
            // 성공 표시
            captureItem.classList.add('tagged');
            captureItem.style.backgroundColor = '#e8f5e9';

            // 약간의 딜레이 후 원래 색으로
            setTimeout(() => {
                captureItem.style.backgroundColor = '';
            }, 1000);

            // allTags에 새 태그 추가 (다음 렌더링을 위해)
            allTags.push({
                capture_id: captureId,
                category: category,
                activity: activity
            });

            // 페이지 새로고침 없이 성공 표시만
            // 다음에 날짜를 다시 선택하면 접혀있는 상태로 나타남
        } else {
            alert('태그 저장에 실패했습니다: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();

        if (data.success) {
            categories = data.categories;

            // 일괄 태깅 UI에 카테고리 옵션 추가
            const bulkCategory = document.getElementById('bulkCategory');
            if (bulkCategory) {
                categories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.name;
                    option.textContent = cat.name;
                    bulkCategory.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('카테고리 로드 실패:', error);
    }
}

// ========== 일괄 태깅 ==========

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.item-checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });

    updateSelectedCount();
}

function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.item-checkbox');
    const checkedCheckboxes = document.querySelectorAll('.item-checkbox:checked');
    const count = checkedCheckboxes.length;
    const countEl = document.getElementById('selectedCount');
    const saveBtn = document.getElementById('bulkSaveBtn');
    const deleteBtn = document.getElementById('bulkDeleteBtn');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');

    if (countEl) {
        countEl.textContent = `${count}개 선택됨`;
    }

    // 전체 선택 체크박스 상태 업데이트
    if (selectAllCheckbox && checkboxes.length > 0) {
        if (count === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (count === checkboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;  // 일부만 선택된 상태
        }
    }

    // 선택된 항목이 있고, 카테고리와 활동이 선택되어 있으면 저장 버튼 활성화
    const bulkCategory = document.getElementById('bulkCategory');
    const bulkActivity = document.getElementById('bulkActivity');

    if (saveBtn && bulkCategory && bulkActivity) {
        saveBtn.disabled = !(count > 0 && bulkCategory.value && bulkActivity.value);
    }

    // 선택된 항목이 있으면 삭제 버튼 활성화
    if (deleteBtn) {
        deleteBtn.disabled = count === 0;
    }
}

function onBulkCategoryChange() {
    const bulkCategory = document.getElementById('bulkCategory');
    const bulkActivity = document.getElementById('bulkActivity');
    const categoryName = bulkCategory.value;

    if (!categoryName) {
        bulkActivity.disabled = true;
        bulkActivity.innerHTML = '<option value="">활동 선택</option>';
        updateSelectedCount();
        return;
    }

    // 해당 카테고리의 활동 목록 가져오기
    const category = categories.find(cat => cat.name === categoryName);

    if (category) {
        const activityOptions = category.activities.map(activity =>
            `<option value="${activity}">${activity}</option>`
        ).join('');

        bulkActivity.innerHTML = '<option value="">활동 선택</option>' + activityOptions;
        bulkActivity.disabled = false;
    }

    updateSelectedCount();
}

async function bulkSaveTags() {
    const bulkCategory = document.getElementById('bulkCategory');
    const bulkActivity = document.getElementById('bulkActivity');
    const checkboxes = document.querySelectorAll('.item-checkbox:checked');

    const category = bulkCategory.value;
    const activity = bulkActivity.value;

    if (!category || !activity || checkboxes.length === 0) {
        alert('카테고리, 활동, 선택된 항목을 확인해주세요.');
        return;
    }

    let successCount = 0;
    let failCount = 0;

    // 각 선택된 항목에 대해 태깅
    for (const checkbox of checkboxes) {
        const captureId = parseInt(checkbox.id.replace('check-', ''));
        const captureItem = document.querySelector(`.capture-item[data-capture-id="${captureId}"]`);

        try {
            const response = await fetch('/api/tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    capture_id: captureId,
                    category: category,
                    activity: activity
                })
            });

            const data = await response.json();

            if (data.success) {
                successCount++;
                captureItem.classList.add('tagged');

                // allTags에 새 태그 추가
                allTags.push({
                    capture_id: captureId,
                    category: category,
                    activity: activity
                });
            } else {
                failCount++;
            }
        } catch (error) {
            console.error('태그 저장 실패:', error);
            failCount++;
        }
    }

    // 결과 알림
    if (successCount > 0) {
        alert(`${successCount}개 항목이 태깅되었습니다.` + (failCount > 0 ? ` (실패: ${failCount}개)` : ''));

        // 드롭다운 초기화
        bulkCategory.value = '';
        bulkActivity.value = '';
        bulkActivity.disabled = true;
        bulkActivity.innerHTML = '<option value="">활동 선택</option>';

        // 페이지 새로고침하여 태깅된 항목을 접힌 상태로 표시
        if (currentDate) {
            await loadCaptures(currentDate);
        }
    } else {
        alert('태깅에 실패했습니다.');
    }
}

async function bulkDeleteCaptures() {
    const checkboxes = document.querySelectorAll('.item-checkbox:checked');

    if (checkboxes.length === 0) {
        alert('삭제할 항목을 선택해주세요.');
        return;
    }

    // 확인 메시지
    const confirmed = confirm(`선택한 ${checkboxes.length}개 항목을 삭제하시겠습니까?`);
    if (!confirmed) return;

    // capture_ids 목록 수집
    const captureIds = [];
    checkboxes.forEach(checkbox => {
        const captureId = parseInt(checkbox.id.replace('check-', ''));
        captureIds.push(captureId);
    });

    try {
        const response = await fetch('/api/captures/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                capture_ids: captureIds
            })
        });

        const data = await response.json();

        if (data.success) {
            alert(`${data.deleted_count}개 항목이 삭제되었습니다.`);

            // 페이지 새로고침하여 삭제된 항목 제거 및 선택 상태 초기화
            if (currentDate) {
                await loadCaptures(currentDate);
            }
        } else {
            alert('삭제 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

// ========== 통계 페이지 ==========

function initStats() {
    // 오늘 날짜 설정
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    document.getElementById('endDate').value = todayStr;

    // 일주일 전 날짜 설정
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const weekAgoStr = weekAgo.toISOString().split('T')[0];

    document.getElementById('startDate').value = weekAgoStr;

    // 조회 버튼
    document.getElementById('loadStats').addEventListener('click', loadStats);

    // 초기 로드
    loadStats();
}

async function loadStats() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) {
        alert('시작일과 종료일을 입력해주세요.');
        return;
    }

    try {
        // 카테고리 통계
        const categoryResponse = await fetch(`/api/stats/category?start_date=${startDate}&end_date=${endDate}`);
        const categoryData = await categoryResponse.json();

        // 활동 통계
        const activityResponse = await fetch(`/api/stats/activity?start_date=${startDate}&end_date=${endDate}`);
        const activityData = await activityResponse.json();

        if (categoryData.success && activityData.success) {
            renderCategoryChart(categoryData.stats);
            renderActivityChart(activityData.stats);
            renderStatsTable(activityData.stats);
        } else {
            showError('통계를 불러오는데 실패했습니다.');
        }
    } catch (error) {
        showError('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

function renderCategoryChart(stats) {
    const ctx = document.getElementById('categoryChart');

    // 기존 차트 삭제
    if (window.categoryChartInstance) {
        window.categoryChartInstance.destroy();
    }

    const labels = stats.map(s => s.category);
    const data = stats.map(s => s.total_minutes);

    // 카테고리별 색상 매핑
    const colorMap = {
        '연구': '#4CAF50',
        '행정': '#2196F3',
        '개인': '#FF9800',
        '기타': '#9E9E9E',
        '미분류': '#E0E0E0'
    };
    const colors = labels.map(label => colorMap[label] || '#CCCCCC');

    window.categoryChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const minutes = context.parsed;
                            const hours = Math.floor(minutes / 60);
                            const mins = minutes % 60;
                            return `${context.label}: ${hours}시간 ${mins}분`;
                        }
                    }
                }
            }
        }
    });
}

function renderActivityChart(stats) {
    const ctx = document.getElementById('activityChart');

    // 기존 차트 삭제
    if (window.activityChartInstance) {
        window.activityChartInstance.destroy();
    }

    const labels = stats.map(s => s.activity);
    const data = stats.map(s => s.total_minutes / 60); // 시간으로 변환

    window.activityChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '시간 (h)',
                data: data,
                backgroundColor: '#4CAF50'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + 'h';
                        }
                    }
                }
            }
        }
    });
}

function renderStatsTable(stats) {
    const tbody = document.querySelector('#statsTable tbody');

    if (stats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="info-message">데이터가 없습니다.</td></tr>';
        return;
    }

    // 전체 시간 합계 계산
    const totalMinutes = stats.reduce((sum, stat) => sum + stat.total_minutes, 0);

    // 카테고리별로 그룹화 (미분류 포함)
    const categoryTotals = {};
    stats.forEach(stat => {
        if (!categoryTotals[stat.category]) {
            categoryTotals[stat.category] = 0;
        }
        categoryTotals[stat.category] += stat.total_minutes;
    });

    // 데이터 행 생성
    const dataRows = stats.map(stat => {
        const hours = Math.floor(stat.total_minutes / 60);
        const minutes = stat.total_minutes % 60;
        const percentage = totalMinutes > 0 ? ((stat.total_minutes / totalMinutes) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td>${stat.category}</td>
                <td>${stat.activity || '-'}</td>
                <td>${hours}시간 ${minutes}분</td>
                <td>${percentage}%</td>
            </tr>
        `;
    }).join('');

    // 합계 행 생성
    const totalHours = Math.floor(totalMinutes / 60);
    const totalMins = totalMinutes % 60;
    const summaryRow = `
        <tr style="background-color: #f5f5f5; font-weight: 600; border-top: 2px solid #4CAF50;">
            <td colspan="2">합계</td>
            <td>${totalHours}시간 ${totalMins}분</td>
            <td>100%</td>
        </tr>
    `;

    tbody.innerHTML = dataRows + summaryRow;
}

// ========== 설정 페이지 ==========

function initSettings() {
    // 현재 설정 로드
    loadCurrentSettings();

    // 상태 주기적 업데이트
    updateStatus();
    setInterval(updateStatus, 3000);

    // 저장 공간 정보 로드
    loadStorageInfo();

    // 이벤트 리스너
    document.getElementById('imageQuality').addEventListener('input', function() {
        document.getElementById('qualityValue').textContent = this.value;
    });

    document.getElementById('pauseResumeBtn').addEventListener('click', togglePauseResume);
    document.getElementById('manualCaptureBtn').addEventListener('click', manualCapture);
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('setScheduledStopBtn').addEventListener('click', setScheduledStop);
    document.getElementById('cancelScheduledStopBtn').addEventListener('click', cancelScheduledStop);
    document.getElementById('deleteAllImagesBtn').addEventListener('click', deleteAllImages);
}

async function loadCurrentSettings() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();

        if (data.success) {
            const cfg = data.config;
            document.getElementById('intervalMinutes').value = cfg.capture.interval_minutes;
            document.getElementById('imageQuality').value = cfg.capture.image_quality;
            document.getElementById('qualityValue').textContent = cfg.capture.image_quality;
            document.getElementById('autoDelete').checked = cfg.storage.auto_delete_after_tagging;
        }
    } catch (error) {
        console.error('설정 로드 실패:', error);
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.success) {
            const status = data.status;
            const statusEl = document.getElementById('captureStatus');
            const pauseBtn = document.getElementById('pauseResumeBtn');

            if (status.is_paused) {
                statusEl.textContent = '일시정지';
                statusEl.classList.add('paused');
                pauseBtn.textContent = '재개';
            } else if (status.is_running) {
                statusEl.textContent = '실행 중';
                statusEl.classList.remove('paused');
                pauseBtn.textContent = '일시정지';
            } else {
                statusEl.textContent = '중지됨';
                statusEl.classList.add('paused');
            }

            // 예약 종료 정보
            const scheduledInfo = document.getElementById('scheduledStopInfo');
            if (status.scheduled_stop) {
                scheduledInfo.textContent = `예약됨: ${status.scheduled_stop}에 자동 종료`;
            } else {
                scheduledInfo.textContent = '예약된 종료 없음';
            }
        }
    } catch (error) {
        console.error('상태 조회 실패:', error);
    }
}

async function togglePauseResume() {
    try {
        const statusResponse = await fetch('/api/status');
        const statusData = await statusResponse.json();

        const isPaused = statusData.success && statusData.status.is_paused;
        const endpoint = isPaused ? '/api/control/resume' : '/api/control/pause';

        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            alert(isPaused ? '캡처가 재개되었습니다.' : '캡처가 일시정지되었습니다.');
            updateStatus();
        } else {
            alert('작업 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

async function manualCapture() {
    const btn = document.getElementById('manualCaptureBtn');
    btn.disabled = true;
    btn.textContent = '캡처 중...';

    try {
        const response = await fetch('/api/control/capture', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            alert(`캡처 완료! ${data.files.length}개의 모니터가 캡처되었습니다.`);
        } else {
            alert('캡처 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    } finally {
        btn.disabled = false;
        btn.textContent = '즉시 캡처';
    }
}

async function saveSettings() {
    const intervalMinutes = parseInt(document.getElementById('intervalMinutes').value);
    const imageQuality = parseInt(document.getElementById('imageQuality').value);
    const autoDelete = document.getElementById('autoDelete').checked;

    if (intervalMinutes < 1 || intervalMinutes > 60) {
        alert('캡처 간격은 1~60분 사이여야 합니다.');
        return;
    }

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interval_minutes: intervalMinutes,
                image_quality: imageQuality,
                auto_delete_after_tagging: autoDelete
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('설정이 저장되었습니다!');
        } else {
            alert('설정 저장 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

async function setScheduledStop() {
    const stopTime = document.getElementById('scheduledStop').value;

    if (!stopTime) {
        alert('종료 시간을 선택해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/scheduled-stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stop_time: stopTime })
        });

        const data = await response.json();

        if (data.success) {
            alert(`${stopTime}에 자동 종료가 예약되었습니다.`);
            updateStatus();
        } else {
            alert('예약 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

async function cancelScheduledStop() {
    try {
        const response = await fetch('/api/scheduled-stop', {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            alert('예약이 취소되었습니다.');
            updateStatus();
        } else {
            alert('취소 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

async function loadStorageInfo() {
    try {
        const response = await fetch('/api/storage');
        const data = await response.json();

        if (data.success) {
            const storage = data.storage;
            document.getElementById('totalCaptures').textContent = `${storage.total_captures}장`;
            document.getElementById('estimatedSize').textContent = `${storage.total_size_mb} MB`;
        }
    } catch (error) {
        console.error('저장 공간 정보 로드 실패:', error);
    }
}

async function deleteAllImages() {
    const confirmed = confirm('⚠️ 경고: 모든 캡처 이미지가 삭제됩니다.\n태그 정보는 유지됩니다.\n\n정말 삭제하시겠습니까?');

    if (!confirmed) return;

    const doubleConfirm = confirm('다시 한번 확인합니다.\n이 작업은 되돌릴 수 없습니다.\n\n계속하시겠습니까?');

    if (!doubleConfirm) return;

    try {
        const response = await fetch('/api/storage/delete-all', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            alert(`${data.deleted_count}개의 이미지가 삭제되었습니다.`);
            loadStorageInfo();
        } else {
            alert('삭제 실패: ' + data.error);
        }
    } catch (error) {
        alert('서버 연결에 실패했습니다.');
        console.error(error);
    }
}

// ========== 유틸리티 ==========

function showError(message) {
    console.error(message);
    // 간단한 알림 (나중에 토스트 알림으로 개선 가능)
    alert(message);
}
