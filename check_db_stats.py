"""
DB 용량 및 레코드 통계 확인
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import DatabaseManager


def check_db_stats():
    """DB 통계 확인"""
    db_manager = DatabaseManager()
    cursor = db_manager.conn.cursor()

    print("=" * 70)
    print("데이터베이스 통계")
    print("=" * 70)

    # 1. 파일 크기
    db_path = Path(db_manager.db_path)
    db_size = db_path.stat().st_size
    print(f"\n📁 DB 파일 크기: {db_size:,} bytes ({db_size / 1024 / 1024:.2f} MB)")

    # WAL 파일 크기
    wal_path = db_path.with_suffix('.db-wal')
    if wal_path.exists():
        wal_size = wal_path.stat().st_size
        print(f"📁 WAL 파일 크기: {wal_size:,} bytes ({wal_size / 1024 / 1024:.2f} MB)")
        total_size = db_size + wal_size
        print(f"📁 총 크기: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    else:
        total_size = db_size

    # 2. 레코드 수
    cursor.execute("SELECT COUNT(*) FROM activities")
    total_activities = cursor.fetchone()[0]
    print(f"\n📊 총 활동 레코드: {total_activities:,}개")

    if total_activities == 0:
        print("\n⚠️ 활동 데이터가 없습니다.")
        return

    # 3. 날짜 범위
    cursor.execute("SELECT MIN(start_time), MAX(start_time) FROM activities")
    first_date, last_date = cursor.fetchone()
    print(f"📅 첫 레코드: {first_date}")
    print(f"📅 마지막 레코드: {last_date}")

    # 기간 계산
    if first_date and last_date:
        first_dt = datetime.fromisoformat(first_date)
        last_dt = datetime.fromisoformat(last_date)
        days = (last_dt - first_dt).days + 1
        print(f"📅 기간: {days}일")

        if days > 0:
            avg_per_day = total_activities / days
            print(f"📊 하루 평균 레코드: {avg_per_day:.1f}개")

    # 4. 레코드당 평균 크기
    avg_size_per_record = total_size / total_activities if total_activities > 0 else 0
    print(f"\n💾 레코드당 평균 크기: {avg_size_per_record:.1f} bytes")

    # 5. 텍스트 필드 평균 길이
    cursor.execute("""
        SELECT
            AVG(LENGTH(COALESCE(process_name, ''))) as avg_process,
            AVG(LENGTH(COALESCE(window_title, ''))) as avg_title,
            AVG(LENGTH(COALESCE(chrome_url, ''))) as avg_url
        FROM activities
    """)
    avg_process, avg_title, avg_url = cursor.fetchone()
    print(f"\n📝 평균 텍스트 길이:")
    print(f"   - process_name: {avg_process:.1f} 글자")
    print(f"   - window_title: {avg_title:.1f} 글자")
    print(f"   - chrome_url: {avg_url:.1f} 글자")

    # 6. 용량 예측
    print("\n" + "=" * 70)
    print("용량 예측 (하루 2000개 레코드 기준)")
    print("=" * 70)

    daily_records = 2000
    size_per_record = avg_size_per_record

    predictions = [
        ("1개월", 30, daily_records * 30),
        ("3개월", 90, daily_records * 90),
        ("6개월", 180, daily_records * 180),
        ("1년", 365, daily_records * 365),
        ("2년", 730, daily_records * 730),
        ("3년", 1095, daily_records * 1095),
    ]

    for period, days, records in predictions:
        estimated_size = records * size_per_record
        mb = estimated_size / 1024 / 1024
        gb = estimated_size / 1024 / 1024 / 1024

        if gb >= 1:
            size_str = f"{gb:.2f} GB"
        else:
            size_str = f"{mb:.1f} MB"

        print(f"   {period:8s} ({days:4d}일): {records:,}개 → 약 {size_str}")

    # 7. 권장사항
    print("\n" + "=" * 70)
    print("권장사항")
    print("=" * 70)

    one_year_size_mb = (daily_records * 365 * size_per_record) / 1024 / 1024

    if one_year_size_mb < 100:
        print("✅ 1년치 데이터가 100MB 이하입니다.")
        print("   → 용량 관리 필요 없음, 2-3년은 문제없이 사용 가능")
    elif one_year_size_mb < 500:
        print("⚠️ 1년치 데이터가 100-500MB 정도입니다.")
        print("   → 1-2년은 문제없으나, 장기 사용 시 자동 정리 고려")
    else:
        print("⚠️ 1년치 데이터가 500MB 이상입니다.")
        print("   → 6개월-1년마다 오래된 데이터 삭제/아카이빙 권장")

    print("\n💡 팁:")
    print("   - 현재 인덱스가 잘 설정되어 있어 수십만 레코드도 빠름")
    print("   - '전체 백업' 기능으로 주기적으로 백업 후")
    print("   - 오래된 데이터는 수동으로 정리 가능")


if __name__ == "__main__":
    check_db_stats()
