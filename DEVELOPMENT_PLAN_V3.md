# ScreenCapture v3.0 개발 계획

**작성일**: 2025-10-24
**버전**: 3.0.0
**예상 소요 시간**: 17시간

---

## 📋 목차

1. [요구사항 정리](#요구사항-정리)
2. [데이터베이스 구조 변경](#데이터베이스-구조-변경)
3. [마이그레이션 전략](#마이그레이션-전략)
4. [API 엔드포인트 설계](#api-엔드포인트-설계)
5. [프론트엔드 구현](#프론트엔드-구현)
6. [개발 단계별 체크리스트](#개발-단계별-체크리스트)
7. [리스크 및 대응](#리스크-및-대응)

---

## 🎯 요구사항 정리

### 핵심 기능

1. **태그(카테고리) 및 하위태그(활동) 관리**
   - 설정 페이지에서 CRUD (추가, 수정, 삭제)
   - 로컬 DB에 저장 (config.json은 초기 시드만)

2. **카테고리별 색상 차별화**
   - 현재: 태그 완료 시 녹색만
   - 변경: 카테고리별 다른 색상 표시
   - 색상 선택 가능 (Color Picker)

3. **ID 기반 참조 (중요)**
   - 현재: `category TEXT`, `activity TEXT` → 이름 변경 시 문제
   - 변경: `category_id INT`, `activity_id INT` → 이름 변경해도 자동 반영

### 핵심 문제점

1. **config.json 충돌**: 재시작 시마다 DB 덮어쓰기 → 사용자 수정 사라짐
2. **색상 미반영**: 하이라이트 항상 녹색 고정
3. **CASCADE 위험성**: 실수 삭제 시 복구 불가 → RESTRICT로 변경

---

## 🏗️ 데이터베이스 구조 변경

### v3.0 스키마

#### 1. categories 테이블 (확장)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- 중복 방지
    color TEXT NOT NULL,                -- HEX (#4CAF50)
    order_index INTEGER DEFAULT 0,      -- 정렬 순서
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**변경사항**:
- `name` → `UNIQUE` 제약 추가
- `order_index` 컬럼 추가 (정렬 순서)
- `updated_at` 컬럼 추가

#### 2. activities 테이블 (신규) ⭐
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE (category_id, name)          -- 같은 카테고리 내 중복 방지
);
CREATE INDEX idx_activities_category_id ON activities(category_id);
```

**특징**:
- 각 활동이 1급 객체로 승격
- 카테고리별로 활동 관리
- 다른 카테고리에 동일한 활동명 허용 (예: "연구-코딩", "개인-코딩")

#### 3. tags 테이블 (리팩토링) ⭐
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    category_id INTEGER NOT NULL,       -- TEXT → INTEGER FK
    activity_id INTEGER NOT NULL,       -- TEXT → INTEGER FK
    duration_min INTEGER NOT NULL,
    capture_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,  -- ⚠️ RESTRICT
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE RESTRICT,  -- ⚠️ RESTRICT
    FOREIGN KEY (capture_id) REFERENCES captures(id)
);
CREATE INDEX idx_tags_category_id ON tags(category_id);
CREATE INDEX idx_tags_activity_id ON tags(activity_id);
```

**주요 변경**:
- `category TEXT` → `category_id INTEGER`
- `activity TEXT` → `activity_id INTEGER`
- `ON DELETE RESTRICT` → 안전성 우선 (실수 방지)

### 장점

| 항목 | v2.0 (TEXT) | v3.0 (ID FK) |
|------|-------------|--------------|
| 이름 변경 | 모든 tags UPDATE 필요 | 자동 반영 |
| 삭제 시 | Orphan tags 발생 | RESTRICT 에러 (안전) |
| 색상 조회 | JOIN 필요 없음 | JOIN 1회 (빠름) |
| 데이터 무결성 | 없음 (오타 가능) | FK 제약 보장 |
| 저장 공간 | ~15 bytes/tag | ~8 bytes/tag |

---

## 🔄 마이그레이션 전략

### migration_v3.py 주요 기능

1. **트랜잭션 + 롤백**: 실패 시 자동 복구
2. **백업**: 마이그레이션 전 자동 백업
3. **검증**: FK 무결성, orphan 태그 체크
4. **실패 로깅**: 변환 실패 케이스 상세 로그

### 마이그레이션 단계

```
1. 백업 (activity_backup_v3_YYYYMMDD_HHMMSS.db)
   ↓
2. 트랜잭션 시작
   ↓
3. activities 테이블 생성
   ↓
4. categories 확장 (order_index, updated_at)
   ↓
5. config.json → activities 데이터 마이그레이션
   ↓
6. tags_new 테이블 생성 (INT FK)
   ↓
7. 기존 tags 데이터 변환
   - category TEXT → category_id (SELECT id FROM categories WHERE name=?)
   - activity TEXT → activity_id (SELECT id FROM activities WHERE name=?)
   ↓
8. 검증 (orphan 체크)
   ↓
9. 테이블 교체 (DROP tags, RENAME tags_new)
   ↓
10. 인덱스 생성
   ↓
11. 커밋
```

---

## 📡 API 엔드포인트 설계

### 카테고리 관리

| Method | Path | 설명 | 신규 |
|--------|------|------|------|
| GET | `/api/categories` | 카테고리 + 활동 조회 | 수정 |
| POST | `/api/categories` | 카테고리 추가 | ✅ |
| PUT | `/api/categories/:id` | 카테고리 수정 | ✅ |
| DELETE | `/api/categories/:id` | 카테고리 삭제 | ✅ |

**GET /api/categories 응답**:
```json
{
  "success": true,
  "categories": [
    {
      "id": 1,
      "name": "연구",
      "color": "#4CAF50",
      "order_index": 0,
      "activities": [
        {"id": 1, "name": "코딩", "order_index": 0},
        {"id": 2, "name": "자료 조사", "order_index": 1}
      ]
    }
  ]
}
```

**POST /api/categories 요청**:
```json
{
  "name": "새 카테고리",
  "color": "#FF5722"
}
```

**DELETE 에러 (RESTRICT)**:
```json
{
  "success": false,
  "error": "이 카테고리를 사용하는 태그가 10개 있습니다. 먼저 태그를 삭제하거나 다른 카테고리로 변경하세요."
}
```

### 활동 관리

| Method | Path | 설명 | 신규 |
|--------|------|------|------|
| POST | `/api/categories/:id/activities` | 활동 추가 | ✅ |
| PUT | `/api/activities/:id` | 활동 수정 | ✅ |
| DELETE | `/api/activities/:id` | 활동 삭제 | ✅ |

### 태그 생성 (수정)

**POST /api/tags**:
```json
// 요청
{
  "capture_id": 123,
  "category_id": 1,      // TEXT → INT
  "activity_id": 2       // TEXT → INT
}
```

### 태그 조회 (수정 - JOIN)

**GET /api/tags/<date>**:
```json
{
  "success": true,
  "tags": [
    {
      "id": 1,
      "timestamp": "2025-10-24 15:01:08",
      "capture_id": 123,
      "category": {
        "id": 1,
        "name": "연구",
        "color": "#4CAF50"
      },
      "activity": {
        "id": 2,
        "name": "코딩"
      },
      "duration_min": 3
    }
  ]
}
```

---

## 💾 database.py 주요 메서드

### 신규 메서드

| 메서드 | 파라미터 | 반환 | 설명 |
|--------|----------|------|------|
| `get_categories_with_activities()` | - | `list[dict]` | JOIN으로 조회 |
| `add_category()` | `name, color, order_index` | `int` | 카테고리 추가 |
| `update_category()` | `id, name, color, order_index` | - | 카테고리 수정 |
| `delete_category()` | `id` | - | 삭제 (RESTRICT) |
| `add_activity()` | `category_id, name, order_index` | `int` | 활동 추가 |
| `update_activity()` | `id, name, order_index` | - | 활동 수정 |
| `delete_activity()` | `id` | - | 삭제 (RESTRICT) |
| `get_tags_by_date_with_details()` | `date` | `list[dict]` | JOIN으로 조회 |

### 수정 메서드

| 메서드 | 변경사항 |
|--------|----------|
| `init_categories()` | ⚠️ **DB가 비어있을 때만 로드** |
| `add_tag()` | `category_id, activity_id` 파라미터로 변경 |
| 통계 쿼리들 | JOIN 기반으로 재작성 |

---

## 🎨 프론트엔드 구현

### Settings 페이지 - 카테고리 관리 UI

**HTML 구조**:
```html
<section class="settings-section">
  <h2>카테고리 및 활동 관리</h2>

  <div id="category-list">
    <!-- 카테고리 항목 -->
    <div class="category-item" data-category-id="1">
      <div class="category-header">
        <input type="color" value="#4CAF50" onchange="updateCategoryColor(1, this.value)">
        <input type="text" value="연구" onchange="updateCategoryName(1, this.value)">
        <button onclick="deleteCategory(1)">삭제</button>
      </div>

      <!-- 활동 목록 -->
      <div class="activity-list">
        <div class="activity-item" data-activity-id="1">
          <input type="text" value="코딩" onchange="updateActivityName(1, this.value)">
          <button onclick="deleteActivity(1)">삭제</button>
        </div>
        <button onclick="addActivity(1)">+ 활동 추가</button>
      </div>
    </div>
  </div>

  <button onclick="addCategory()">+ 카테고리 추가</button>
</section>
```

### Timeline 페이지 - 색상 반영

**유틸리티 함수**:
```javascript
// HEX를 RGBA로 변환
function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// 카테고리 색상 조회
function getCategoryColor(categoryId, alpha = 1) {
    const category = categories.find(c => c.id === categoryId);
    if (!category) return `rgba(76, 175, 80, ${alpha})`;
    return hexToRgba(category.color, alpha);
}
```

**버튼 렌더링 (색상 반영)**:
```javascript
const categoryButtons = categories.map(cat => {
    const isActive = existingTag && existingTag.category.id === cat.id;
    const borderColor = cat.color;
    const bgColor = isActive ? hexToRgba(cat.color, 0.1) : 'transparent';

    return `<button
        class="category-btn ${isActive ? 'active' : ''}"
        data-category-id="${cat.id}"
        style="border: 2px solid ${borderColor}; background: ${bgColor};"
        onclick="selectCategory(${captureId}, ${cat.id})"
    >${cat.name}</button>`;
}).join('');
```

**태그 완료 하이라이트 (색상 반영)**:
```javascript
if (data.success) {
    const highlightColor = getCategoryColor(categoryId, 0.15);
    captureItem.style.backgroundColor = highlightColor;

    setTimeout(() => {
        captureItem.style.backgroundColor = '';
    }, 1000);
}
```

---

## ✅ 개발 단계별 체크리스트

### Phase 0: 백업 및 준비 (0.5시간) ✅ 완료

- [x] 현재 DB 전체 백업
- [x] migration_v3.py 작성 (트랜잭션, 롤백, 검증 포함)
- [x] 로컬 테스트 DB 생성

---

### Phase 1: 데이터베이스 마이그레이션 (2.5시간) ✅ 완료

- [x] activities 테이블 생성
- [x] categories 확장 (order_index, updated_at)
- [x] config.json → activities 마이그레이션 (초기 시드)
- [x] tags 테이블 리팩토링 (TEXT → INT FK, ON DELETE RESTRICT)
- [x] 데이터 변환 및 검증 (실패 케이스 로깅)
- [x] 인덱스 생성
- [x] 프로덕션 DB 마이그레이션

---

### Phase 2: 백엔드 - database.py (3시간) ✅ 완료

- [x] `init_categories()` 수정 ⚠️ **비어있을 때만 로드**
- [x] `get_categories_with_activities()` 구현 (JOIN)
- [x] `add_category()`, `update_category()`, `delete_category()` 구현
- [x] `add_activity()`, `update_activity()`, `delete_activity()` 구현
- [x] `add_tag()` 수정 (category_id, activity_id)
- [x] `get_tags_by_date_with_details()` 구현 (JOIN)
- [x] 통계 쿼리 수정 (JOIN 기반)

---

### Phase 3: 백엔드 - viewer.py (2시간) ✅ 완료

- [x] `GET /api/categories` 수정 (activities 포함)
- [x] `POST /api/categories` 구현
- [x] `PUT /api/categories/:id` 구현
- [x] `DELETE /api/categories/:id` 구현 (RESTRICT 에러 처리)
- [x] `POST /api/categories/:id/activities` 구현
- [x] `PUT /api/activities/:id` 구현
- [x] `DELETE /api/activities/:id` 구현 (RESTRICT 에러 처리)
- [x] `POST /api/tags` 수정 (category_id, activity_id)
- [x] `GET /api/tags/<date>` 수정 (JOIN 응답)

---

### Phase 4: 프론트엔드 - Settings UI (4시간) ✅ 완료

- [x] settings.html에 "카테고리 및 활동 관리" 섹션 추가
- [x] 카테고리 목록 렌더링 (색상 picker 포함)
- [x] 카테고리 CRUD 이벤트 핸들러
- [x] 활동 목록 렌더링 (카테고리별)
- [x] 활동 CRUD 이벤트 핸들러
- [x] 에러 처리 (RESTRICT 메시지 표시)
- [x] CSS 스타일링

---

### Phase 5: 프론트엔드 - Timeline 색상 반영 (2시간)

- [ ] `hexToRgba()`, `getCategoryColor()` 유틸리티 추가
- [ ] `loadCategories()` 수정 (activities 포함 응답)
- [ ] `renderCaptures()` 수정
  - category_id 기반 버튼
  - 카테고리 색상 스타일
- [ ] `selectCategory()` 수정 (category_id)
- [ ] `selectActivity()` 수정
  - category_id, activity_id 전송
  - 카테고리 색상 하이라이트
- [ ] 모달 뷰어 색상 반영

---

### Phase 6: 테스트 및 검증 (2시간)

- [ ] 마이그레이션 검증 (데이터 정합성)
- [ ] 카테고리 CRUD 테스트
- [ ] 활동 CRUD 테스트
- [ ] 카테고리 이름 변경 → 기존 태그 자동 반영
- [ ] RESTRICT 동작 확인 (삭제 불가 메시지)
- [ ] 색상 변경 → 타임라인 반영
- [ ] 통계 페이지 (JOIN 쿼리)
- [ ] ⚠️ 재시작 후 config.json 덮어쓰기 안 되는지 확인

---

### Phase 7: 문서 업데이트 (1시간)

- [ ] ARCHITECTURE.md v3.0 업데이트
- [ ] migration_v3.py 주석
- [ ] API 엔드포인트 문서화

---

## ⚡ 예상 소요 시간

| Phase | 시간 | 누적 |
|-------|------|------|
| Phase 0: 백업 및 준비 | 0.5h | 0.5h |
| Phase 1: 데이터베이스 마이그레이션 | 2.5h | 3h |
| Phase 2: 백엔드 - database.py | 3h | 6h |
| Phase 3: 백엔드 - viewer.py | 2h | 8h |
| Phase 4: 프론트엔드 - Settings UI | 4h | 12h |
| Phase 5: 프론트엔드 - Timeline 색상 | 2h | 14h |
| Phase 6: 테스트 및 검증 | 2h | 16h |
| Phase 7: 문서 업데이트 | 1h | **17h** |

**총 예상 시간: 17시간**

---

## 🚨 리스크 및 대응

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| 마이그레이션 실패 | 높음 | 트랜잭션 + 자동 롤백 + 백업 |
| RESTRICT로 삭제 불가 | 중간 | 명확한 에러 메시지 + 해결 방법 안내 |
| 기존 태그 많아서 JOIN 느림 | 낮음 | 인덱스로 최적화, 필요시 캐싱 |
| config.json 충돌 | 높음 | init_categories 수정 (비어있을 때만) |
| 색상 투명도 브라우저 호환성 | 낮음 | hexToRgba 함수로 해결 |

---

## 📊 변경사항 요약

### 데이터베이스
- **신규**: activities 테이블
- **확장**: categories (order_index, updated_at)
- **리팩토링**: tags (TEXT → INT FK, ON DELETE RESTRICT)
- **인덱스**: 3개 추가

### 백엔드
- **신규 API**: 9개 (카테고리/활동 CRUD)
- **수정 API**: 3개 (categories, tags 조회)
- **신규 메서드**: 7개 (database.py)
- **수정 메서드**: 3개 (init_categories, add_tag, 통계)

### 프론트엔드
- **신규 페이지**: Settings - 카테고리 관리 섹션
- **신규 함수**: 12개 (CRUD + 유틸리티)
- **수정 함수**: 5개 (Timeline 색상 반영)
- **CSS**: 카테고리 관리 UI, 색상 버튼 스타일

---

## 🎯 핵심 의사결정

### 1. config.json vs DB
**선택**: DB가 단일 진실 공급원
**이유**: config.json은 초기 시드만, 모든 변경은 DB에 저장

### 2. CASCADE vs RESTRICT
**선택**: ON DELETE RESTRICT
**이유**: 안전성 우선, 실수 삭제 방지, 명확한 에러 메시지

### 3. 색상 저장 형식
**선택**: HEX 문자열 (#RRGGBB)
**이유**: HTML5 color picker 호환, CSS 직접 사용, JS에서 투명도 처리

---

**최종 업데이트**: 2025-10-24
**상태**: 계획 완료, 구현 대기 중
