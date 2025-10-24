"""
데이터베이스 v3.0 마이그레이션 스크립트

주요 변경사항:
1. activities 테이블 신규 생성 (활동을 1급 객체로 승격)
2. categories 테이블 확장 (order_index, updated_at 추가)
3. tags 테이블 리팩토링 (TEXT -> INT FK, ON DELETE RESTRICT)
4. config.json -> activities 테이블로 마이그레이션 (초기 시드만)
"""

import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path


class MigrationV3:
    def __init__(self, db_path: str, config_path: str):
        self.db_path = db_path
        self.config_path = config_path
        self.backup_path = None

    def create_backup(self) -> str:
        """마이그레이션 전 백업 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.db_path.replace('.db', f'_backup_v3_{timestamp}.db')
        shutil.copy2(self.db_path, backup_path)
        self.backup_path = backup_path
        print(f"[OK] 백업 생성: {backup_path}")
        return backup_path

    def load_config(self) -> dict:
        """config.json 로드"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def migrate(self):
        """메인 마이그레이션 로직"""
        print("\n" + "="*60)
        print("ScreenCapture v3.0 데이터베이스 마이그레이션 시작")
        print("="*60 + "\n")

        # 1. 백업 생성
        self.create_backup()

        # 2. config.json 로드
        config = self.load_config()
        categories_data = config['categories']

        # 3. 마이그레이션 실행 (트랜잭션)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.cursor()

            # 트랜잭션 시작
            cursor.execute("BEGIN TRANSACTION")

            # Step 1: activities 테이블 생성
            print("[Step 1] activities 테이블 생성...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                    UNIQUE (category_id, name)
                )
            """)
            print("   [OK] activities 테이블 생성 완료")

            # Step 2: categories 테이블 확장 준비
            print("\n[Step 2] categories 테이블 확장...")

            # 기존 categories 데이터 백업
            cursor.execute("SELECT * FROM categories")
            old_categories = cursor.fetchall()

            # categories_new 테이블 생성 (확장 스키마)
            cursor.execute("""
                CREATE TABLE categories_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 기존 데이터를 새 테이블로 복사
            category_id_map = {}  # old_id -> new_id 매핑
            for idx, old_cat in enumerate(old_categories):
                cursor.execute("""
                    INSERT INTO categories_new (name, color, order_index)
                    VALUES (?, ?, ?)
                """, (old_cat['name'], old_cat['color'], idx))
                category_id_map[old_cat['id']] = cursor.lastrowid

            # 기존 테이블 삭제 후 교체
            cursor.execute("DROP TABLE categories")
            cursor.execute("ALTER TABLE categories_new RENAME TO categories")
            print(f"   [OK] categories 테이블 확장 완료 ({len(old_categories)}개)")

            # Step 3: config.json -> activities 마이그레이션
            print("\n[Step 3] config.json -> activities 마이그레이션...")

            activity_count = 0
            for cat_data in categories_data:
                # 카테고리 ID 찾기
                cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_data['name'],))
                row = cursor.fetchone()

                if not row:
                    print(f"   [WARN] 카테고리 '{cat_data['name']}' 없음 (스킵)")
                    continue

                category_id = row['id']

                # 활동 추가
                for idx, activity_name in enumerate(cat_data['activities']):
                    cursor.execute("""
                        INSERT INTO activities (category_id, name, order_index)
                        VALUES (?, ?, ?)
                    """, (category_id, activity_name, idx))
                    activity_count += 1

            print(f"   [OK] activities 마이그레이션 완료 ({activity_count}개)")

            # Step 4: tags 테이블 리팩토링
            print("\n[Step 4] tags 테이블 리팩토링 (TEXT -> INT FK)...")

            # 기존 tags 데이터 조회
            cursor.execute("SELECT * FROM tags")
            old_tags = cursor.fetchall()

            # tags_new 테이블 생성 (INT FK 스키마)
            cursor.execute("""
                CREATE TABLE tags_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    category_id INTEGER NOT NULL,
                    activity_id INTEGER NOT NULL,
                    duration_min INTEGER NOT NULL,
                    capture_id INTEGER,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
                    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE RESTRICT,
                    FOREIGN KEY (capture_id) REFERENCES captures(id)
                )
            """)

            # Step 5: 데이터 변환 및 검증
            print("\n[Step 5] 태그 데이터 변환 및 검증...")

            converted_count = 0
            failed_tags = []

            for tag in old_tags:
                # category TEXT -> category_id
                cursor.execute("SELECT id FROM categories WHERE name = ?", (tag['category'],))
                cat_row = cursor.fetchone()

                if not cat_row:
                    failed_tags.append({
                        'id': tag['id'],
                        'reason': f"카테고리 '{tag['category']}' 없음",
                        'data': dict(tag)
                    })
                    continue

                category_id = cat_row['id']

                # activity TEXT -> activity_id
                cursor.execute("""
                    SELECT id FROM activities
                    WHERE category_id = ? AND name = ?
                """, (category_id, tag['activity']))
                act_row = cursor.fetchone()

                if not act_row:
                    failed_tags.append({
                        'id': tag['id'],
                        'reason': f"활동 '{tag['activity']}' (카테고리: {tag['category']}) 없음",
                        'data': dict(tag)
                    })
                    continue

                activity_id = act_row['id']

                # tags_new에 삽입
                cursor.execute("""
                    INSERT INTO tags_new (timestamp, category_id, activity_id, duration_min, capture_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (tag['timestamp'], category_id, activity_id, tag['duration_min'], tag['capture_id']))

                converted_count += 1

            print(f"   [OK] 변환 성공: {converted_count}/{len(old_tags)}개")

            if failed_tags:
                print(f"   [WARN] 변환 실패: {len(failed_tags)}개")
                for fail in failed_tags[:5]:  # 최대 5개만 표시
                    print(f"      - Tag ID {fail['id']}: {fail['reason']}")

                # 실패 로그 저장
                log_path = self.db_path.replace('.db', '_migration_failed_tags.json')
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(failed_tags, f, indent=2, ensure_ascii=False)
                print(f"   [INFO] 전체 실패 로그: {log_path}")

            # Step 6: 테이블 교체
            print("\n[Step 6] 테이블 교체...")
            cursor.execute("DROP TABLE tags")
            cursor.execute("ALTER TABLE tags_new RENAME TO tags")
            print("   [OK] 테이블 교체 완료")

            # Step 7: 인덱스 생성
            print("\n[Step 7] 인덱스 생성...")
            cursor.execute("CREATE INDEX idx_activities_category_id ON activities(category_id)")
            cursor.execute("CREATE INDEX idx_tags_category_id ON tags(category_id)")
            cursor.execute("CREATE INDEX idx_tags_activity_id ON tags(activity_id)")
            print("   [OK] 인덱스 생성 완료")

            # 커밋
            conn.commit()
            print("\n" + "="*60)
            print("[SUCCESS] 마이그레이션 성공!")
            print("="*60)

            # 최종 통계
            self.print_stats(conn)

        except Exception as e:
            # 롤백
            conn.rollback()
            print("\n" + "="*60)
            print(f"[ERROR] 마이그레이션 실패: {e}")
            print(f"[ROLLBACK] 롤백 완료 (백업: {self.backup_path})")
            print("="*60)
            raise

        finally:
            conn.close()

    def print_stats(self, conn: sqlite3.Connection):
        """마이그레이션 후 통계 출력"""
        cursor = conn.cursor()

        print("\n[STATS] 마이그레이션 후 통계:")

        cursor.execute("SELECT COUNT(*) FROM categories")
        print(f"   - 카테고리: {cursor.fetchone()[0]}개")

        cursor.execute("SELECT COUNT(*) FROM activities")
        print(f"   - 활동: {cursor.fetchone()[0]}개")

        cursor.execute("SELECT COUNT(*) FROM tags")
        print(f"   - 태그: {cursor.fetchone()[0]}개")

        cursor.execute("SELECT COUNT(*) FROM captures")
        print(f"   - 캡처: {cursor.fetchone()[0]}개")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='ScreenCapture v3.0 데이터베이스 마이그레이션')
    parser.add_argument('--db', default='./data/activity.db', help='데이터베이스 경로')
    parser.add_argument('--config', default='./config.json', help='설정 파일 경로')
    parser.add_argument('--test', action='store_true', help='테스트 DB로 실행 (원본 보존)')

    args = parser.parse_args()

    # 테스트 모드: 복사본으로 실행
    db_path = args.db
    if args.test:
        test_db = args.db.replace('.db', '_test.db')
        shutil.copy2(args.db, test_db)
        db_path = test_db
        print(f"[TEST MODE] 테스트 DB: {test_db}")

    # 마이그레이션 실행
    migration = MigrationV3(db_path, args.config)
    migration.migrate()


if __name__ == "__main__":
    main()
