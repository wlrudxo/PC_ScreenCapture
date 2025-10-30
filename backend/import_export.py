"""
Import/Export 유틸리티

데이터베이스 전체 백업/복원 및 룰 Import/Export 기능
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class ImportExportManager:
    """
    Import/Export 관리 클래스

    기능:
    1. DB 전체 백업 (SQLite 파일 복사)
    2. DB 복원 (백업 파일로 교체)
    3. 룰 Export (JSON)
    4. 룰 Import (JSON)
    """

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self.db_manager = db_manager
        self.db_path = Path(db_manager.db_path)

    # === DB 전체 백업/복원 ===

    def export_database(self, backup_path: str) -> bool:
        """
        데이터베이스 전체를 백업 파일로 Export

        Args:
            backup_path: 백업 파일 경로 (.db 확장자)

        Returns:
            성공 여부
        """
        try:
            backup_path = Path(backup_path)

            # 확장자 체크
            if backup_path.suffix.lower() != '.db':
                backup_path = backup_path.with_suffix('.db')

            # WAL 파일도 함께 백업 (일관성 보장)
            # 먼저 체크포인트를 실행하여 WAL 내용을 메인 DB에 반영
            self.db_manager.conn.execute("PRAGMA wal_checkpoint(FULL)")
            self.db_manager.conn.commit()

            # 메인 DB 파일 복사
            shutil.copy2(self.db_path, backup_path)

            print(f"[ImportExport] DB 백업 완료: {backup_path}")
            return True

        except Exception as e:
            print(f"[ImportExport] DB 백업 실패: {e}")
            return False

    def import_database(self, backup_path: str) -> Tuple[bool, str]:
        """
        백업 파일로 데이터베이스 복원

        주의: 이 함수는 DB 파일을 교체하지만, 앱이 재시작되기 전까지는
              기존 connection이 유지되므로 앱 재시작이 필요합니다.

        Args:
            backup_path: 백업 파일 경로

        Returns:
            (성공 여부, 에러 메시지)
        """
        try:
            backup_path = Path(backup_path)

            # 백업 파일 존재 확인
            if not backup_path.exists():
                return False, "백업 파일이 존재하지 않습니다."

            # 백업 파일 유효성 체크 (SQLite 파일인지)
            if backup_path.suffix.lower() != '.db':
                return False, "올바른 데이터베이스 파일이 아닙니다. (.db 파일만 가능)"

            # 기존 DB를 임시 백업 (롤백용)
            temp_backup = self.db_path.with_suffix('.db.tmp')

            try:
                # 모든 connection 닫기
                self.db_manager.conn.close()

                # 기존 DB 임시 백업
                shutil.copy2(self.db_path, temp_backup)

                # WAL 파일도 백업
                wal_path = self.db_path.with_suffix('.db-wal')
                if wal_path.exists():
                    shutil.copy2(wal_path, temp_backup.with_suffix('.db-wal.tmp'))

                # 새 DB로 교체
                shutil.copy2(backup_path, self.db_path)

                # 임시 백업 삭제
                temp_backup.unlink()
                if temp_backup.with_suffix('.db-wal.tmp').exists():
                    temp_backup.with_suffix('.db-wal.tmp').unlink()

                print(f"[ImportExport] DB 복원 완료: {backup_path}")
                return True, "데이터베이스가 복원되었습니다.\n앱을 재시작해야 변경사항이 적용됩니다."

            except Exception as e:
                # 롤백
                if temp_backup.exists():
                    shutil.copy2(temp_backup, self.db_path)
                    temp_backup.unlink()
                raise e

        except Exception as e:
            print(f"[ImportExport] DB 복원 실패: {e}")
            return False, f"복원 중 오류 발생: {str(e)}"

    # === 룰 Import/Export (JSON) ===

    def export_rules(self, json_path: str) -> bool:
        """
        태그와 룰을 JSON 파일로 Export

        JSON 구조:
        {
            "export_date": "2024-01-01 12:00:00",
            "version": "1.0",
            "tags": [...],
            "rules": [...]
        }

        Args:
            json_path: JSON 파일 경로

        Returns:
            성공 여부
        """
        try:
            json_path = Path(json_path)

            # 확장자 체크
            if json_path.suffix.lower() != '.json':
                json_path = json_path.with_suffix('.json')

            # 태그와 룰 조회
            tags = self.db_manager.get_all_tags()
            rules = self.db_manager.get_all_rules(order_by='priority DESC')

            # JSON 데이터 구성
            export_data = {
                "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "tags": tags,
                "rules": rules
            }

            # JSON 파일로 저장
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            print(f"[ImportExport] 룰 Export 완료: {json_path}")
            print(f"  - 태그: {len(tags)}개")
            print(f"  - 룰: {len(rules)}개")
            return True

        except Exception as e:
            print(f"[ImportExport] 룰 Export 실패: {e}")
            return False

    def import_rules(self, json_path: str, merge_mode: bool = True) -> Tuple[bool, str, Dict[str, int]]:
        """
        JSON 파일에서 태그와 룰을 Import

        동작:
        1. 태그: 같은 이름이 있으면 기존 것 사용, 없으면 새로 생성
        2. 룰: merge_mode에 따라 처리
           - merge_mode=True: 기존 룰 유지 + 새 룰 추가 (기본)
           - merge_mode=False: 기존 룰 삭제 + 새 룰만 추가

        Args:
            json_path: JSON 파일 경로
            merge_mode: True=기존 룰 유지, False=기존 룰 삭제

        Returns:
            (성공 여부, 메시지, 통계 딕셔너리)
        """
        try:
            json_path = Path(json_path)

            # JSON 파일 존재 확인
            if not json_path.exists():
                return False, "JSON 파일이 존재하지 않습니다.", {}

            # JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 버전 체크 (미래에 확장 가능)
            version = import_data.get('version', '1.0')
            if version != '1.0':
                return False, f"지원하지 않는 버전입니다: {version}", {}

            tags_data = import_data.get('tags', [])
            rules_data = import_data.get('rules', [])

            # 통계
            stats = {
                'tags_imported': 0,
                'tags_existed': 0,
                'rules_imported': 0,
                'rules_deleted': 0
            }

            # 태그 ID 매핑 (JSON의 tag_id -> DB의 tag_id)
            tag_id_mapping = {}

            # 1. 태그 Import
            for tag in tags_data:
                tag_name = tag['name']
                tag_color = tag['color']

                # 같은 이름의 태그가 있는지 확인
                existing_tag = self.db_manager.get_tag_by_name(tag_name)

                if existing_tag:
                    # 기존 태그 사용
                    tag_id_mapping[tag['id']] = existing_tag['id']
                    stats['tags_existed'] += 1
                else:
                    # 새 태그 생성
                    new_tag_id = self.db_manager.create_tag(tag_name, tag_color)
                    tag_id_mapping[tag['id']] = new_tag_id
                    stats['tags_imported'] += 1

            # 2. 룰 Import
            if not merge_mode:
                # 기존 룰 모두 삭제
                existing_rules = self.db_manager.get_all_rules()
                for rule in existing_rules:
                    self.db_manager.delete_rule(rule['id'])
                    stats['rules_deleted'] += 1

            # 새 룰 추가
            for rule in rules_data:
                # 태그 ID 매핑
                old_tag_id = rule['tag_id']
                if old_tag_id not in tag_id_mapping:
                    print(f"[ImportExport] 경고: 룰 '{rule['name']}'의 태그 ID {old_tag_id}를 찾을 수 없습니다. 건너뜁니다.")
                    continue

                new_tag_id = tag_id_mapping[old_tag_id]

                # 룰 생성
                self.db_manager.create_rule(
                    name=rule['name'],
                    tag_id=new_tag_id,
                    priority=rule.get('priority', 0),
                    enabled=rule.get('enabled', True),
                    process_pattern=rule.get('process_pattern'),
                    url_pattern=rule.get('url_pattern'),
                    window_title_pattern=rule.get('window_title_pattern'),
                    chrome_profile=rule.get('chrome_profile'),
                    process_path_pattern=rule.get('process_path_pattern')
                )
                stats['rules_imported'] += 1

            # 결과 메시지
            message_parts = []
            message_parts.append("Import 완료!")
            message_parts.append("")
            message_parts.append(f"태그:")
            message_parts.append(f"  - 새로 추가: {stats['tags_imported']}개")
            message_parts.append(f"  - 기존 사용: {stats['tags_existed']}개")
            message_parts.append("")
            message_parts.append(f"룰:")
            if stats['rules_deleted'] > 0:
                message_parts.append(f"  - 기존 삭제: {stats['rules_deleted']}개")
            message_parts.append(f"  - 새로 추가: {stats['rules_imported']}개")

            message = '\n'.join(message_parts)

            print(f"[ImportExport] 룰 Import 완료")
            print(f"  - 태그: 추가 {stats['tags_imported']}개, 기존 {stats['tags_existed']}개")
            print(f"  - 룰: 추가 {stats['rules_imported']}개, 삭제 {stats['rules_deleted']}개")

            return True, message, stats

        except Exception as e:
            print(f"[ImportExport] 룰 Import 실패: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Import 중 오류 발생:\n{str(e)}", {}

    def validate_rules_json(self, json_path: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        룰 JSON 파일의 유효성 검증

        Args:
            json_path: JSON 파일 경로

        Returns:
            (유효 여부, 메시지, 데이터 미리보기)
        """
        try:
            json_path = Path(json_path)

            if not json_path.exists():
                return False, "파일이 존재하지 않습니다.", None

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 필수 필드 체크
            if 'version' not in data:
                return False, "version 필드가 없습니다.", None

            if 'tags' not in data or 'rules' not in data:
                return False, "tags 또는 rules 필드가 없습니다.", None

            # 미리보기 정보
            preview = {
                'export_date': data.get('export_date', '알 수 없음'),
                'version': data.get('version'),
                'tags_count': len(data.get('tags', [])),
                'rules_count': len(data.get('rules', []))
            }

            return True, "유효한 룰 파일입니다.", preview

        except json.JSONDecodeError as e:
            return False, f"JSON 파싱 오류: {str(e)}", None
        except Exception as e:
            return False, f"파일 읽기 오류: {str(e)}", None
