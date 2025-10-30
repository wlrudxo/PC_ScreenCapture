"""
Import/Export 기능 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from backend.database import DatabaseManager
from backend.import_export import ImportExportManager


def test_export_rules():
    """룰 Export 테스트"""
    print("\n" + "=" * 70)
    print("룰 Export 테스트")
    print("=" * 70)

    db_manager = DatabaseManager()
    import_export = ImportExportManager(db_manager)

    # 현재 태그와 룰 확인
    tags = db_manager.get_all_tags()
    rules = db_manager.get_all_rules()

    print(f"\n현재 데이터:")
    print(f"  - 태그: {len(tags)}개")
    for tag in tags:
        print(f"    - {tag['name']} ({tag['color']})")

    print(f"\n  - 룰: {len(rules)}개")
    for rule in rules:
        print(f"    - {rule['name']} (우선순위: {rule['priority']}, 태그: {rule['tag_name']})")

    # Export 테스트
    export_path = Path(__file__).parent / "test_rules_export.json"
    success = import_export.export_rules(str(export_path))

    if success:
        print(f"\n✅ Export 성공: {export_path}")
        # 파일 내용 확인
        with open(export_path, 'r', encoding='utf-8') as f:
            import json
            data = json.load(f)
            print(f"\nExport된 데이터:")
            print(f"  - 버전: {data['version']}")
            print(f"  - 내보낸 날짜: {data['export_date']}")
            print(f"  - 태그: {len(data['tags'])}개")
            print(f"  - 룰: {len(data['rules'])}개")
    else:
        print(f"\n❌ Export 실패")

    return success


def test_import_rules():
    """룰 Import 테스트 (병합 모드)"""
    print("\n" + "=" * 70)
    print("룰 Import 테스트 (병합 모드)")
    print("=" * 70)

    db_manager = DatabaseManager()
    import_export = ImportExportManager(db_manager)

    export_path = Path(__file__).parent / "test_rules_export.json"

    if not export_path.exists():
        print(f"\n❌ Export 파일이 없습니다: {export_path}")
        return False

    # Import 전 룰 개수
    rules_before = db_manager.get_all_rules()
    print(f"\nImport 전 룰 개수: {len(rules_before)}개")

    # Import 실행
    success, message, stats = import_export.import_rules(str(export_path), merge_mode=True)

    if success:
        print(f"\n✅ Import 성공")
        print(f"\n{message}")

        # Import 후 룰 개수
        rules_after = db_manager.get_all_rules()
        print(f"\nImport 후 룰 개수: {len(rules_after)}개")
    else:
        print(f"\n❌ Import 실패: {message}")

    return success


def test_export_database():
    """DB 전체 백업 테스트"""
    print("\n" + "=" * 70)
    print("DB 전체 백업 테스트")
    print("=" * 70)

    db_manager = DatabaseManager()
    import_export = ImportExportManager(db_manager)

    backup_path = Path(__file__).parent / "test_db_backup.db"

    # 백업 실행
    success = import_export.export_database(str(backup_path))

    if success:
        print(f"\n✅ DB 백업 성공: {backup_path}")
        # 파일 크기 확인
        size = backup_path.stat().st_size
        print(f"  - 파일 크기: {size:,} bytes ({size / 1024:.2f} KB)")
    else:
        print(f"\n❌ DB 백업 실패")

    return success


def test_validate_rules_json():
    """룰 JSON 검증 테스트"""
    print("\n" + "=" * 70)
    print("룰 JSON 검증 테스트")
    print("=" * 70)

    db_manager = DatabaseManager()
    import_export = ImportExportManager(db_manager)

    export_path = Path(__file__).parent / "test_rules_export.json"

    if not export_path.exists():
        print(f"\n❌ Export 파일이 없습니다: {export_path}")
        return False

    # 검증 실행
    valid, message, preview = import_export.validate_rules_json(str(export_path))

    if valid:
        print(f"\n✅ 유효한 파일입니다")
        print(f"\n파일 정보:")
        print(f"  - 내보낸 날짜: {preview['export_date']}")
        print(f"  - 버전: {preview['version']}")
        print(f"  - 태그 개수: {preview['tags_count']}")
        print(f"  - 룰 개수: {preview['rules_count']}")
    else:
        print(f"\n❌ 유효하지 않은 파일: {message}")

    return valid


def main():
    """테스트 실행"""
    print("=" * 70)
    print("Import/Export 기능 테스트")
    print("=" * 70)

    try:
        # 1. 룰 Export 테스트
        if not test_export_rules():
            print("\n❌ 룰 Export 테스트 실패")
            return

        # 2. 룰 JSON 검증 테스트
        if not test_validate_rules_json():
            print("\n❌ 룰 JSON 검증 테스트 실패")
            return

        # 3. 룰 Import 테스트
        if not test_import_rules():
            print("\n❌ 룰 Import 테스트 실패")
            return

        # 4. DB 전체 백업 테스트
        if not test_export_database():
            print("\n❌ DB 백업 테스트 실패")
            return

        print("\n" + "=" * 70)
        print("✅ 모든 테스트 통과!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
