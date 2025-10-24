"""
데이터베이스 마이그레이션 - 향상된 timestamp 매칭
"""
import sqlite3
from datetime import datetime
import re

DB_PATH = "./data/activity_test.db"

def parse_timestamp(ts_str):
    """다양한 timestamp 형식을 파싱하여 datetime 객체로 변환"""
    if not ts_str:
        return None

    # UTC 시간대가 포함된 경우 (예: 2025-10-23 02:19:16.438000+00:00)
    if '+00:00' in ts_str:
        # UTC를 로컬 시간으로 변환 (한국 시간 = UTC+9)
        ts_str = ts_str.replace('+00:00', '')
        dt = datetime.fromisoformat(ts_str)
        # UTC를 한국 시간으로 변환 (9시간 추가)
        from datetime import timedelta
        dt = dt + timedelta(hours=9)
        return dt
    else:
        # 일반 timestamp
        try:
            return datetime.fromisoformat(ts_str)
        except:
            return None

def find_matching_capture(conn, tag_timestamp_str):
    """
    태그의 timestamp에 가장 가까운 capture를 찾음
    """
    cursor = conn.cursor()

    tag_dt = parse_timestamp(tag_timestamp_str)
    if not tag_dt:
        return None

    # 초 단위까지만 비교 (밀리초 제거)
    tag_dt_str = tag_dt.strftime('%Y-%m-%d %H:%M:%S')

    # 같은 초에 해당하는 capture 찾기 (monitor_num=1만, 대표 capture)
    cursor.execute("""
        SELECT id, timestamp
        FROM captures
        WHERE strftime('%Y-%m-%d %H:%M:%S', timestamp) = ?
        AND monitor_num = 1
        LIMIT 1
    """, (tag_dt_str,))

    row = cursor.fetchone()
    if row:
        return row[0]  # capture_id

    # 정확히 매칭되지 않으면 ±10초 범위에서 가장 가까운 것 찾기
    cursor.execute("""
        SELECT id, timestamp,
               ABS(julianday(timestamp) - julianday(?)) as time_diff
        FROM captures
        WHERE monitor_num = 1
        AND ABS(julianday(timestamp) - julianday(?)) < 0.0001  -- 약 10초
        ORDER BY time_diff
        LIMIT 1
    """, (tag_dt_str, tag_dt_str))

    row = cursor.fetchone()
    return row[0] if row else None

def migrate_with_matching():
    """향상된 매칭 로직으로 마이그레이션"""
    print("=" * 60)
    print("향상된 마이그레이션 실행")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 백업 테이블이 있는지 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags_backup'")
    if not cursor.fetchone():
        print("❌ tags_backup 테이블이 없습니다. migration.sql을 먼저 실행하세요.")
        conn.close()
        return False

    # 2. 모든 태그 가져오기
    cursor.execute("SELECT * FROM tags_backup ORDER BY id")
    tags = cursor.fetchall()

    print(f"\n총 {len(tags)}개의 태그 처리 중...")

    matched_count = 0
    orphan_count = 0

    # 3. 각 태그에 대해 capture_id 찾기
    for i, tag in enumerate(tags):
        if (i + 1) % 50 == 0:
            print(f"  진행 중: {i + 1}/{len(tags)}")

        tag_id = tag['id']
        tag_timestamp = tag['timestamp']

        # capture_id 찾기
        capture_id = find_matching_capture(conn, tag_timestamp)

        if capture_id:
            matched_count += 1
        else:
            orphan_count += 1
            print(f"  ⚠️  매칭 실패 - Tag ID={tag_id}, timestamp={tag_timestamp}")

        # tags 테이블 업데이트
        cursor.execute("""
            UPDATE tags
            SET capture_id = ?
            WHERE id = ?
        """, (capture_id, tag_id))

    conn.commit()

    # 4. 결과 출력
    print(f"\n✓ 처리 완료:")
    print(f"  - 매칭 성공: {matched_count}")
    print(f"  - 매칭 실패 (orphan): {orphan_count}")

    # 5. 최종 검증
    cursor.execute("SELECT COUNT(*) FROM tags WHERE capture_id IS NULL")
    final_orphan_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tags WHERE capture_id IS NOT NULL")
    final_matched_count = cursor.fetchone()[0]

    print(f"\n최종 검증:")
    print(f"  - capture_id 있음: {final_matched_count}")
    print(f"  - capture_id NULL: {final_orphan_count}")

    # 6. 샘플 확인
    print(f"\n샘플 확인 (capture_id 있는 태그 3개):")
    cursor.execute("SELECT * FROM tags WHERE capture_id IS NOT NULL LIMIT 3")
    for row in cursor.fetchall():
        print(f"  Tag ID={row['id']}, timestamp={row['timestamp']}, capture_id={row['capture_id']}, category={row['category']}")

    if final_orphan_count > 0:
        print(f"\n샘플 확인 (orphan 태그 3개):")
        cursor.execute("SELECT * FROM tags WHERE capture_id IS NULL LIMIT 3")
        for row in cursor.fetchall():
            print(f"  Tag ID={row['id']}, timestamp={row['timestamp']}, category={row['category']}")

    conn.close()

    print("\n" + "=" * 60)
    if final_orphan_count > 0:
        print(f"⚠️  {final_orphan_count}개의 orphan tags가 남아있습니다.")
        return False
    else:
        print("✅ 모든 태그가 성공적으로 매칭되었습니다!")
        return True

if __name__ == "__main__":
    migrate_with_matching()
