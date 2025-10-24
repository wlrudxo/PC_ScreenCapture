"""
테스트 DB 마이그레이션 스크립트
"""
import sqlite3

DB_PATH = "./data/activity_test.db"

def run_test_migration():
    """테스트 DB에 마이그레이션 실행"""
    print("=" * 60)
    print("테스트 DB 마이그레이션 실행")
    print("=" * 60)

    print(f"테스트 DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # migration.sql 읽어서 실행
    print("\n[1/3] migration.sql 실행 중...")
    with open('migration.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("✓ 마이그레이션 SQL 실행 완료")
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.close()
        return False

    # 검증
    print("\n[2/3] 마이그레이션 검증 중...")

    # captures 카운트
    cursor.execute("SELECT COUNT(*) FROM captures")
    captures_count = cursor.fetchone()[0]
    print(f"  - Captures: {captures_count}")

    # tags 카운트
    cursor.execute("SELECT COUNT(*) FROM tags")
    tags_count = cursor.fetchone()[0]
    print(f"  - Tags: {tags_count}")

    # orphan tags
    cursor.execute("SELECT COUNT(*) FROM tags WHERE capture_id IS NULL")
    orphan_count = cursor.fetchone()[0]
    print(f"  - Orphan tags: {orphan_count}")

    # deleted captures ('DELETED' → NULL 변환 확인)
    cursor.execute("SELECT COUNT(*) FROM captures WHERE deleted_at IS NOT NULL")
    deleted_count = cursor.fetchone()[0]
    print(f"  - Deleted captures (filepath=NULL): {deleted_count}")

    # 'DELETED' 문자열이 남아있는지 확인
    cursor.execute("SELECT COUNT(*) FROM captures WHERE filepath = 'DELETED'")
    deleted_string_count = cursor.fetchone()[0]
    print(f"  - 'DELETED' 문자열 남아있음: {deleted_string_count}")

    # 샘플 데이터 확인
    print("\n[3/3] 샘플 데이터 확인...")
    cursor.execute("SELECT * FROM captures LIMIT 3")
    print("\n  Captures 샘플:")
    for row in cursor.fetchall():
        print(f"    ID={row['id']}, timestamp={row['timestamp']}, monitor={row['monitor_num']}, filepath={row['filepath'][:30] if row['filepath'] else 'NULL'}..., deleted_at={row['deleted_at']}")

    cursor.execute("SELECT * FROM tags LIMIT 3")
    print("\n  Tags 샘플:")
    for row in cursor.fetchall():
        print(f"    ID={row['id']}, timestamp={row['timestamp']}, category={row['category']}, activity={row['activity']}, capture_id={row['capture_id']}")

    conn.close()

    print("\n" + "=" * 60)
    if orphan_count > 0:
        print(f"⚠️  경고: {orphan_count}개의 orphan tags 발견")
        print("이 태그들은 capture_id가 NULL입니다.")
        return False

    if deleted_string_count > 0:
        print(f"⚠️  경고: {deleted_string_count}개의 'DELETED' 문자열이 남아있습니다.")
        return False

    print("✅ 테스트 마이그레이션 성공!")
    return True

if __name__ == "__main__":
    run_test_migration()
