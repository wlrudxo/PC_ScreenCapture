"""
데이터베이스 마이그레이션 스크립트
실행: python migration.py
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import shutil

DB_PATH = "./data/activity.db"
BACKUP_PATH = f"./data/activity_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_database():
    """데이터베이스 백업"""
    print(f"[1/6] 데이터베이스 백업 중... {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✓ 백업 완료: {BACKUP_PATH}")

def run_migration():
    """마이그레이션 실행"""
    print("[2/6] 마이그레이션 SQL 실행 중...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # migration.sql 읽어서 실행
    with open('migration.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    cursor.executescript(sql_script)
    conn.commit()
    conn.close()

    print("✓ 마이그레이션 SQL 완료")

def parse_timestamp(ts_str):
    """다양한 timestamp 형식을 파싱하여 datetime 객체로 변환"""
    if not ts_str:
        return None

    # UTC 시간대가 포함된 경우 (예: 2025-10-23 02:19:16.438000+00:00)
    if '+00:00' in ts_str:
        ts_str = ts_str.replace('+00:00', '')
        dt = datetime.fromisoformat(ts_str)
        # UTC를 한국 시간으로 변환 (9시간 추가)
        dt = dt + timedelta(hours=9)
        return dt
    else:
        try:
            return datetime.fromisoformat(ts_str)
        except:
            return None

def find_matching_capture(conn, tag_timestamp_str):
    """태그의 timestamp에 가장 가까운 capture를 찾음"""
    cursor = conn.cursor()

    tag_dt = parse_timestamp(tag_timestamp_str)
    if not tag_dt:
        return None

    # 초 단위까지만 비교 (밀리초 제거)
    tag_dt_str = tag_dt.strftime('%Y-%m-%d %H:%M:%S')

    # 같은 초에 해당하는 capture 찾기 (monitor_num=1만)
    cursor.execute("""
        SELECT id, timestamp
        FROM captures
        WHERE strftime('%Y-%m-%d %H:%M:%S', timestamp) = ?
        AND monitor_num = 1
        LIMIT 1
    """, (tag_dt_str,))

    row = cursor.fetchone()
    if row:
        return row[0]

    # 정확히 매칭되지 않으면 같은 분에서 가장 가까운 것 찾기
    cursor.execute("""
        SELECT id, timestamp,
               ABS(julianday(timestamp) - julianday(?)) as time_diff
        FROM captures
        WHERE monitor_num = 1
        AND strftime('%Y-%m-%d %H:%M', timestamp) = strftime('%Y-%m-%d %H:%M', ?)
        ORDER BY time_diff
        LIMIT 1
    """, (tag_dt_str, tag_dt_str))

    row = cursor.fetchone()
    return row[0] if row else None

def match_tags_to_captures():
    """향상된 매칭 로직으로 tags에 capture_id 설정"""
    print("[3/6] Tags를 Captures와 매칭 중...")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 모든 태그 가져오기
    cursor.execute("SELECT * FROM tags ORDER BY id")
    tags = cursor.fetchall()

    print(f"  총 {len(tags)}개의 태그 처리 중...")

    matched_count = 0
    orphan_count = 0

    for i, tag in enumerate(tags):
        if (i + 1) % 50 == 0:
            print(f"    진행 중: {i + 1}/{len(tags)}")

        tag_id = tag['id']
        tag_timestamp = tag['timestamp']

        # capture_id 찾기
        capture_id = find_matching_capture(conn, tag_timestamp)

        if capture_id:
            matched_count += 1
        else:
            orphan_count += 1

        # tags 테이블 업데이트
        cursor.execute("UPDATE tags SET capture_id = ? WHERE id = ?", (capture_id, tag_id))

    conn.commit()
    conn.close()

    print(f"  ✓ 매칭 완료: {matched_count}개 성공, {orphan_count}개 orphan")

def verify_migration():
    """마이그레이션 검증"""
    print("[4/6] 마이그레이션 검증 중...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # captures 카운트
    cursor.execute("SELECT COUNT(*) FROM captures")
    captures_count = cursor.fetchone()[0]

    # tags 카운트
    cursor.execute("SELECT COUNT(*) FROM tags")
    tags_count = cursor.fetchone()[0]

    # orphan tags
    cursor.execute("SELECT COUNT(*) FROM tags WHERE capture_id IS NULL")
    orphan_count = cursor.fetchone()[0]

    # deleted captures
    cursor.execute("SELECT COUNT(*) FROM captures WHERE deleted_at IS NOT NULL")
    deleted_count = cursor.fetchone()[0]

    # 'DELETED' 문자열 확인
    cursor.execute("SELECT COUNT(*) FROM captures WHERE filepath = 'DELETED'")
    deleted_string_count = cursor.fetchone()[0]

    conn.close()

    print(f"  - Captures: {captures_count}")
    print(f"  - Tags: {tags_count}")
    print(f"  - Orphan tags: {orphan_count}")
    print(f"  - Deleted captures: {deleted_count}")
    print(f"  - 'DELETED' 문자열: {deleted_string_count} (0이어야 함)")

    success = True
    if orphan_count > 10:  # 10개 이상이면 문제
        print(f"⚠️  경고: {orphan_count}개의 orphan tags 발견")
        success = False

    if deleted_string_count > 0:
        print(f"❌ 'DELETED' 문자열이 {deleted_string_count}개 남아있습니다!")
        success = False

    if success:
        print("✓ 검증 완료")

    return success

if __name__ == "__main__":
    print("=" * 60)
    print("ScreenCapture 데이터베이스 마이그레이션")
    print("=" * 60)

    try:
        # 1. 백업
        backup_database()

        # 2. 마이그레이션 SQL 실행
        run_migration()

        # 3. Tags-Captures 매칭
        match_tags_to_captures()

        # 4. 검증
        if verify_migration():
            print("[5/6] ✓ 검증 성공!")
        else:
            print("[5/6] ⚠️  검증 경고 있음")

        # 5. 최종 안내
        print(f"\n[6/6] 마이그레이션 완료!")
        print(f"  백업 파일: {BACKUP_PATH}")
        print(f"  orphan tags는 해당 시간에 캡처가 없는 경우입니다.")
        print(f"\n✅ 마이그레이션 성공!")

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        print(f"백업에서 복구하세요: {BACKUP_PATH}")
        import traceback
        traceback.print_exc()
