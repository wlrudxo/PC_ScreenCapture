"""
개발 계획 v3.0을 SQLite 데이터베이스에 저장
실행: python save_plan_to_db.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "./development_plan.db"

def create_tables(conn):
    """테이블 생성"""
    cursor = conn.cursor()

    # 1. 개발 단계 (Phases)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phases (
            id INTEGER PRIMARY KEY,
            phase_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            estimated_hours REAL NOT NULL,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. 체크리스트 (Tasks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (phase_id) REFERENCES phases(id)
        )
    """)

    # 3. 리스크 (Risks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_description TEXT NOT NULL,
            impact TEXT NOT NULL CHECK(impact IN ('높음', '중간', '낮음')),
            mitigation TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. 스키마 변경사항 (Schema Changes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            change_type TEXT NOT NULL CHECK(change_type IN ('CREATE', 'ALTER', 'DROP')),
            sql_statement TEXT NOT NULL,
            description TEXT,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. API 엔드포인트 (API Endpoints)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT NOT NULL CHECK(method IN ('GET', 'POST', 'PUT', 'DELETE')),
            path TEXT NOT NULL,
            description TEXT NOT NULL,
            is_new BOOLEAN DEFAULT 1,
            request_example TEXT,
            response_example TEXT,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 6. 데이터베이스 메서드 (Database Methods)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS database_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_name TEXT NOT NULL,
            description TEXT NOT NULL,
            is_new BOOLEAN DEFAULT 1,
            parameters TEXT,
            returns TEXT,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 7. 프론트엔드 변경사항 (Frontend Changes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS frontend_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            function_name TEXT,
            change_type TEXT NOT NULL CHECK(change_type IN ('NEW', 'MODIFY', 'DELETE')),
            description TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. 프로젝트 메타데이터
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_metadata (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            version TEXT NOT NULL,
            total_estimated_hours REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print("✓ 테이블 생성 완료")

def insert_phases(conn):
    """개발 단계 삽입"""
    cursor = conn.cursor()

    phases = [
        (0, "백업 및 준비", 0.5, 0),
        (1, "데이터베이스 마이그레이션", 2.5, 1),
        (2, "백엔드 - database.py", 3.0, 2),
        (3, "백엔드 - viewer.py", 2.0, 3),
        (4, "프론트엔드 - Settings UI", 4.0, 4),
        (5, "프론트엔드 - Timeline 색상 반영", 2.0, 5),
        (6, "테스트 및 검증", 2.0, 6),
        (7, "문서 업데이트", 1.0, 7),
    ]

    cursor.executemany("""
        INSERT INTO phases (phase_number, name, estimated_hours, order_index)
        VALUES (?, ?, ?, ?)
    """, phases)

    conn.commit()
    print(f"✓ {len(phases)}개 단계 삽입 완료")

def insert_tasks(conn):
    """체크리스트 삽입"""
    cursor = conn.cursor()

    tasks = [
        # Phase 0
        (1, "현재 DB 전체 백업", 0),
        (1, "migration_v3.py 작성 (트랜잭션, 롤백, 검증 포함)", 1),
        (1, "로컬 테스트 DB 생성", 2),

        # Phase 1
        (2, "activities 테이블 생성", 0),
        (2, "categories 확장 (order_index, updated_at)", 1),
        (2, "config.json → activities 마이그레이션 (초기 시드)", 2),
        (2, "tags 테이블 리팩토링 (TEXT → INT FK, ON DELETE RESTRICT)", 3),
        (2, "데이터 변환 및 검증 (실패 케이스 로깅)", 4),
        (2, "인덱스 생성", 5),
        (2, "프로덕션 DB 마이그레이션", 6),

        # Phase 2
        (3, "init_categories() 수정 - 비어있을 때만 로드", 0),
        (3, "get_categories_with_activities() 구현 (JOIN)", 1),
        (3, "add_category(), update_category(), delete_category() 구현", 2),
        (3, "add_activity(), update_activity(), delete_activity() 구현", 3),
        (3, "add_tag() 수정 (category_id, activity_id)", 4),
        (3, "get_tags_by_date_with_details() 구현 (JOIN)", 5),
        (3, "통계 쿼리 수정 (JOIN 기반)", 6),

        # Phase 3
        (4, "GET /api/categories 수정 (activities 포함)", 0),
        (4, "POST /api/categories 구현", 1),
        (4, "PUT /api/categories/:id 구현", 2),
        (4, "DELETE /api/categories/:id 구현 (RESTRICT 에러 처리)", 3),
        (4, "POST /api/categories/:id/activities 구현", 4),
        (4, "PUT /api/activities/:id 구현", 5),
        (4, "DELETE /api/activities/:id 구현 (RESTRICT 에러 처리)", 6),
        (4, "POST /api/tags 수정 (category_id, activity_id)", 7),
        (4, "GET /api/tags/<date> 수정 (JOIN 응답)", 8),

        # Phase 4
        (5, "settings.html에 '카테고리 및 활동 관리' 섹션 추가", 0),
        (5, "카테고리 목록 렌더링 (색상 picker 포함)", 1),
        (5, "카테고리 CRUD 이벤트 핸들러", 2),
        (5, "활동 목록 렌더링 (카테고리별)", 3),
        (5, "활동 CRUD 이벤트 핸들러", 4),
        (5, "에러 처리 (RESTRICT 메시지 표시)", 5),
        (5, "CSS 스타일링", 6),

        # Phase 5
        (6, "hexToRgba(), getCategoryColor() 유틸리티 추가", 0),
        (6, "loadCategories() 수정 (activities 포함 응답)", 1),
        (6, "renderCaptures() 수정 - category_id 기반 버튼, 색상 스타일", 2),
        (6, "selectCategory() 수정 (category_id)", 3),
        (6, "selectActivity() 수정 - category_id, activity_id 전송, 색상 하이라이트", 4),
        (6, "모달 뷰어 색상 반영", 5),

        # Phase 6
        (7, "마이그레이션 검증 (데이터 정합성)", 0),
        (7, "카테고리 CRUD 테스트", 1),
        (7, "활동 CRUD 테스트", 2),
        (7, "카테고리 이름 변경 → 기존 태그 자동 반영", 3),
        (7, "RESTRICT 동작 확인 (삭제 불가 메시지)", 4),
        (7, "색상 변경 → 타임라인 반영", 5),
        (7, "통계 페이지 (JOIN 쿼리)", 6),
        (7, "재시작 후 config.json 덮어쓰기 안 되는지 확인", 7),

        # Phase 7
        (8, "ARCHITECTURE.md v3.0 업데이트", 0),
        (8, "migration_v3.py 주석", 1),
        (8, "API 엔드포인트 문서화", 2),
    ]

    cursor.executemany("""
        INSERT INTO tasks (phase_id, description, order_index)
        VALUES (?, ?, ?)
    """, tasks)

    conn.commit()
    print(f"✓ {len(tasks)}개 작업 삽입 완료")

def insert_risks(conn):
    """리스크 삽입"""
    cursor = conn.cursor()

    risks = [
        ("마이그레이션 실패", "높음", "트랜잭션 + 자동 롤백 + 백업", 0),
        ("RESTRICT로 삭제 불가", "중간", "명확한 에러 메시지 + 해결 방법 안내", 1),
        ("기존 태그 많아서 JOIN 느림", "낮음", "인덱스로 최적화, 필요시 캐싱", 2),
        ("config.json 충돌", "높음", "init_categories 수정 (비어있을 때만)", 3),
        ("색상 투명도 브라우저 호환성", "낮음", "hexToRgba 함수로 해결", 4),
    ]

    cursor.executemany("""
        INSERT INTO risks (risk_description, impact, mitigation, order_index)
        VALUES (?, ?, ?, ?)
    """, risks)

    conn.commit()
    print(f"✓ {len(risks)}개 리스크 삽입 완료")

def insert_schema_changes(conn):
    """스키마 변경사항 삽입"""
    cursor = conn.cursor()

    changes = [
        ("activities", "CREATE", """CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE (category_id, name)
)""", "활동 테이블 생성 (카테고리별 하위 태그)", 0),

        ("categories", "ALTER", "ALTER TABLE categories ADD COLUMN order_index INTEGER DEFAULT 0", "정렬 순서 컬럼 추가", 1),
        ("categories", "ALTER", "ALTER TABLE categories ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP", "수정 시간 컬럼 추가", 2),

        ("tags", "ALTER", """CREATE TABLE tags_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    category_id INTEGER NOT NULL,
    activity_id INTEGER NOT NULL,
    duration_min INTEGER NOT NULL,
    capture_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE RESTRICT,
    FOREIGN KEY (capture_id) REFERENCES captures(id)
)""", "tags 테이블 리팩토링 (TEXT → INT FK)", 3),

        ("activities", "CREATE", "CREATE INDEX idx_activities_category_id ON activities(category_id)", "활동 카테고리 인덱스", 4),
        ("tags", "CREATE", "CREATE INDEX idx_tags_category_id ON tags(category_id)", "태그 카테고리 인덱스", 5),
        ("tags", "CREATE", "CREATE INDEX idx_tags_activity_id ON tags(activity_id)", "태그 활동 인덱스", 6),
    ]

    cursor.executemany("""
        INSERT INTO schema_changes (table_name, change_type, sql_statement, description, order_index)
        VALUES (?, ?, ?, ?, ?)
    """, changes)

    conn.commit()
    print(f"✓ {len(changes)}개 스키마 변경 삽입 완료")

def insert_api_endpoints(conn):
    """API 엔드포인트 삽입"""
    cursor = conn.cursor()

    endpoints = [
        ("GET", "/api/categories", "카테고리 + 활동 조회", 0, None,
         '{"success": true, "categories": [{"id": 1, "name": "연구", "color": "#4CAF50", "activities": [...]}]}', 0),

        ("POST", "/api/categories", "카테고리 추가", 1,
         '{"name": "새 카테고리", "color": "#FF5722"}',
         '{"success": true, "id": 5}', 1),

        ("PUT", "/api/categories/:id", "카테고리 수정", 1,
         '{"name": "수정된 이름", "color": "#2196F3"}',
         '{"success": true}', 2),

        ("DELETE", "/api/categories/:id", "카테고리 삭제", 1, None,
         '{"success": false, "error": "이 카테고리를 사용하는 태그가 N개 있습니다"}', 3),

        ("POST", "/api/categories/:id/activities", "활동 추가", 1,
         '{"name": "새 활동"}',
         '{"success": true, "id": 10}', 4),

        ("PUT", "/api/activities/:id", "활동 수정", 1,
         '{"name": "수정된 활동"}',
         '{"success": true}', 5),

        ("DELETE", "/api/activities/:id", "활동 삭제", 1, None,
         '{"success": false, "error": "이 활동을 사용하는 태그가 N개 있습니다"}', 6),

        ("POST", "/api/tags", "태그 추가 (수정)", 0,
         '{"capture_id": 123, "category_id": 1, "activity_id": 2}',
         '{"success": true}', 7),

        ("GET", "/api/tags/<date>", "태그 조회 (수정)", 0, None,
         '{"success": true, "tags": [{"id": 1, "category": {"id": 1, "name": "연구", "color": "#4CAF50"}, "activity": {...}}]}', 8),
    ]

    cursor.executemany("""
        INSERT INTO api_endpoints (method, path, description, is_new, request_example, response_example, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, endpoints)

    conn.commit()
    print(f"✓ {len(endpoints)}개 API 엔드포인트 삽입 완료")

def insert_database_methods(conn):
    """데이터베이스 메서드 삽입"""
    cursor = conn.cursor()

    methods = [
        ("init_categories", "DB가 비어있을 때만 config.json에서 초기화", 0,
         "categories_config: list", "None", 0),

        ("get_categories_with_activities", "카테고리 + 활동 조회 (JOIN)", 1,
         "None", "list[dict]", 1),

        ("add_category", "카테고리 추가", 1,
         "name: str, color: str, order_index: int = None", "int (category_id)", 2),

        ("update_category", "카테고리 수정", 1,
         "category_id: int, name: str = None, color: str = None, order_index: int = None", "None", 3),

        ("delete_category", "카테고리 삭제 (RESTRICT)", 1,
         "category_id: int", "None (IntegrityError 발생 가능)", 4),

        ("add_activity", "활동 추가", 1,
         "category_id: int, name: str, order_index: int = None", "int (activity_id)", 5),

        ("update_activity", "활동 수정", 1,
         "activity_id: int, name: str = None, order_index: int = None", "None", 6),

        ("delete_activity", "활동 삭제 (RESTRICT)", 1,
         "activity_id: int", "None (IntegrityError 발생 가능)", 7),

        ("add_tag", "태그 추가 (수정)", 0,
         "timestamp: datetime, category_id: int, activity_id: int, duration_min: int, capture_id: int = None", "None", 8),

        ("get_tags_by_date_with_details", "태그 조회 (JOIN)", 1,
         "date: str", "list[dict] (카테고리/활동 정보 포함)", 9),
    ]

    cursor.executemany("""
        INSERT INTO database_methods (method_name, description, is_new, parameters, returns, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
    """, methods)

    conn.commit()
    print(f"✓ {len(methods)}개 데이터베이스 메서드 삽입 완료")

def insert_frontend_changes(conn):
    """프론트엔드 변경사항 삽입"""
    cursor = conn.cursor()

    changes = [
        ("settings.html", None, "NEW", "카테고리 및 활동 관리 섹션 추가", 0),

        ("app.js", "hexToRgba", "NEW", "HEX 색상을 RGBA로 변환", 1),
        ("app.js", "getCategoryColor", "NEW", "카테고리 ID로 색상 조회", 2),

        ("app.js", "renderCategoryManager", "NEW", "카테고리 관리 UI 렌더링", 3),
        ("app.js", "addCategory", "NEW", "카테고리 추가", 4),
        ("app.js", "updateCategoryName", "NEW", "카테고리 이름 수정", 5),
        ("app.js", "updateCategoryColor", "NEW", "카테고리 색상 수정", 6),
        ("app.js", "deleteCategory", "NEW", "카테고리 삭제", 7),

        ("app.js", "addActivity", "NEW", "활동 추가", 8),
        ("app.js", "updateActivityName", "NEW", "활동 이름 수정", 9),
        ("app.js", "deleteActivity", "NEW", "활동 삭제", 10),

        ("app.js", "loadCategories", "MODIFY", "activities 포함 응답 처리", 11),
        ("app.js", "renderCaptures", "MODIFY", "category_id 기반, 카테고리 색상 스타일", 12),
        ("app.js", "selectCategory", "MODIFY", "category_id 파라미터", 13),
        ("app.js", "selectActivity", "MODIFY", "category_id, activity_id 전송, 색상 하이라이트", 14),
        ("app.js", "selectModalActivity", "MODIFY", "모달에서 ID 기반 태깅", 15),

        ("style.css", None, "MODIFY", "카테고리 관리 UI 스타일 추가", 16),
        ("style.css", None, "MODIFY", "색상 picker 스타일 추가", 17),
        ("style.css", None, "MODIFY", "카테고리별 색상 버튼 스타일", 18),
    ]

    cursor.executemany("""
        INSERT INTO frontend_changes (file_name, function_name, change_type, description, order_index)
        VALUES (?, ?, ?, ?, ?)
    """, changes)

    conn.commit()
    print(f"✓ {len(changes)}개 프론트엔드 변경사항 삽입 완료")

def insert_metadata(conn):
    """프로젝트 메타데이터 삽입"""
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO project_metadata (id, version, total_estimated_hours)
        VALUES (1, '3.0.0', 17.0)
    """)

    conn.commit()
    print("✓ 프로젝트 메타데이터 삽입 완료")

def main():
    """메인 실행"""
    print("=" * 60)
    print("개발 계획 v3.0 데이터베이스 생성")
    print("=" * 60)

    # 기존 DB 삭제 (있으면)
    db_path = Path(DB_PATH)
    if db_path.exists():
        print(f"\n기존 DB 발견: {DB_PATH}")
        choice = input("삭제하고 새로 만들까요? (y/N): ")
        if choice.lower() == 'y':
            db_path.unlink()
            print("✓ 기존 DB 삭제 완료")
        else:
            print("종료합니다.")
            return

    # DB 연결
    conn = sqlite3.connect(DB_PATH)
    print(f"\n✓ 데이터베이스 생성: {DB_PATH}")

    try:
        # 테이블 생성
        create_tables(conn)

        # 데이터 삽입
        print("\n데이터 삽입 중...")
        insert_phases(conn)
        insert_tasks(conn)
        insert_risks(conn)
        insert_schema_changes(conn)
        insert_api_endpoints(conn)
        insert_database_methods(conn)
        insert_frontend_changes(conn)
        insert_metadata(conn)

        print("\n" + "=" * 60)
        print("✅ 개발 계획 DB 생성 완료!")
        print("=" * 60)
        print(f"\n파일 위치: {db_path.absolute()}")
        print("\n조회 예시:")
        print("  sqlite3 development_plan.db")
        print("  > SELECT * FROM phases;")
        print("  > SELECT * FROM tasks WHERE phase_id = 1;")
        print("  > SELECT * FROM api_endpoints WHERE is_new = 1;")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()

if __name__ == "__main__":
    main()
