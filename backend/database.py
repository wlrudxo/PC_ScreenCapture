"""
SQLite 데이터베이스 관리
"""
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from backend.config import AppConfig


class DatabaseManager:
    """
    SQLite 데이터베이스 관리 클래스

    스레드 안전성: 각 스레드마다 별도 connection을 사용
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        DB 매니저 초기화

        Args:
            db_path: DB 파일 경로 (None이면 AppConfig에서 자동 설정)
        """
        if db_path is None:
            db_path = AppConfig.get_db_path()

        self.db_path = str(db_path)
        self._local = threading.local()  # 스레드별 connection 저장
        self.init_database()

    @property
    def conn(self):
        """
        스레드별 connection 반환
        각 스레드가 처음 접근할 때 자동으로 connection 생성
        """
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            # WAL 모드로 동시성 향상
            self._local.conn.execute('PRAGMA journal_mode=WAL')
        return self._local.conn

    def init_database(self):
        """테이블 생성 및 기본 데이터 삽입"""
        cursor = self.conn.cursor()

        # tags 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # activities 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,

                process_name TEXT,
                window_title TEXT,
                chrome_profile TEXT,
                chrome_url TEXT,

                tag_id INTEGER,
                rule_id INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL,
                FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE SET NULL
            )
        """)

        # activities 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activities_time
            ON activities(start_time, end_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activities_tag
            ON activities(tag_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activities_process
            ON activities(process_name)
        """)

        # rules 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,

                process_pattern TEXT,
                url_pattern TEXT,
                window_title_pattern TEXT,
                chrome_profile TEXT,
                process_path_pattern TEXT,

                tag_id INTEGER NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # 기존 테이블에 process_path_pattern 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE rules ADD COLUMN process_path_pattern TEXT")
            self.conn.commit()
        except Exception:
            # 이미 컬럼이 존재하면 무시
            pass

        # 태그 알림 기능 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN alert_enabled BOOLEAN DEFAULT 0")
            self.conn.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN alert_message TEXT")
            self.conn.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN alert_cooldown INTEGER DEFAULT 30")
            self.conn.commit()
        except Exception:
            pass

        # 태그 차단(집중 모드) 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN block_enabled BOOLEAN DEFAULT 0")
            self.conn.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN block_start_time TEXT")
            self.conn.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE tags ADD COLUMN block_end_time TEXT")
            self.conn.commit()
        except Exception:
            pass

        # settings 테이블 (전역 설정)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # alert_sounds 테이블 (알림음 목록)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_sounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # alert_images 테이블 (알림 이미지 목록)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 기본 태그 삽입 (이미 존재하면 무시)
        default_tags = [
            ('업무', '#4CAF50'),
            ('딴짓', '#FF5722'),
            ('자리비움', '#9E9E9E'),
            ('미분류', '#607D8B'),
        ]
        for name, color in default_tags:
            cursor.execute("""
                INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)
            """, (name, color))

        # 기본 룰 삽입 (이미 존재하면 무시)
        # 먼저 태그 ID 조회
        cursor.execute("SELECT id FROM tags WHERE name='자리비움'")
        away_tag_id = cursor.fetchone()
        if away_tag_id:
            away_tag_id = away_tag_id[0]

            # 화면 잠금 룰 (이미 존재하면 무시)
            cursor.execute("SELECT COUNT(*) FROM rules WHERE name='화면 잠금'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO rules (name, priority, process_pattern, tag_id)
                    VALUES ('화면 잠금', 100, '__LOCKED__', ?)
                """, (away_tag_id,))

            # Idle 룰 (이미 존재하면 무시)
            cursor.execute("SELECT COUNT(*) FROM rules WHERE name='Idle 상태'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO rules (name, priority, process_pattern, tag_id)
                    VALUES ('Idle 상태', 90, '__IDLE__', ?)
                """, (away_tag_id,))

        self.conn.commit()

    # === 태그 관리 ===
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """모든 태그 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tags ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 태그 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """ID로 태그 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_tag(self, name: str, color: str) -> int:
        """태그 생성"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tags (name, color) VALUES (?, ?)
        """, (name, color))
        self.conn.commit()
        return cursor.lastrowid

    def update_tag(self, tag_id: int, name: Optional[str] = None,
                   color: Optional[str] = None,
                   alert_enabled: Optional[bool] = None,
                   alert_message: Optional[str] = None,
                   alert_cooldown: Optional[int] = None,
                   block_enabled: Optional[bool] = None,
                   block_start_time: Optional[str] = None,
                   block_end_time: Optional[str] = None):
        """태그 수정"""
        cursor = self.conn.cursor()
        updates = []
        values = []

        if name:
            updates.append("name = ?")
            values.append(name)
        if color:
            updates.append("color = ?")
            values.append(color)
        if alert_enabled is not None:
            updates.append("alert_enabled = ?")
            values.append(1 if alert_enabled else 0)
        if alert_message is not None:
            updates.append("alert_message = ?")
            values.append(alert_message if alert_message else None)
        if alert_cooldown is not None:
            updates.append("alert_cooldown = ?")
            values.append(max(1, alert_cooldown))  # 최소 1초
        if block_enabled is not None:
            updates.append("block_enabled = ?")
            values.append(1 if block_enabled else 0)
        if block_start_time is not None:
            updates.append("block_start_time = ?")
            values.append(block_start_time if block_start_time else None)
        if block_end_time is not None:
            updates.append("block_end_time = ?")
            values.append(block_end_time if block_end_time else None)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE tags SET {', '.join(updates)} WHERE id = ?"
            values.append(tag_id)
            cursor.execute(query, values)
            self.conn.commit()

    def delete_tag(self, tag_id: int):
        """태그 삭제 (activities.tag_id는 NULL로)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self.conn.commit()

    # === 활동 기록 ===
    def create_activity(self, process_name: Optional[str] = None,
                       window_title: Optional[str] = None,
                       chrome_url: Optional[str] = None,
                       chrome_profile: Optional[str] = None,
                       tag_id: Optional[int] = None,
                       rule_id: Optional[int] = None) -> int:
        """새 활동 시작 (start_time=now, end_time=NULL)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activities
            (start_time, process_name, window_title, chrome_url, chrome_profile,
             tag_id, rule_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now(), process_name, window_title, chrome_url,
              chrome_profile, tag_id, rule_id))
        self.conn.commit()
        return cursor.lastrowid

    def end_activity(self, activity_id: int):
        """활동 종료 (end_time=now)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE activities SET end_time = ? WHERE id = ?
        """, (datetime.now(), activity_id))
        self.conn.commit()

    def cleanup_unfinished_activities(self):
        """
        종료되지 않은 활동들을 정리 (프로그램 시작 시 호출)

        end_time이 NULL인 활동들을 start_time으로부터 1분 후로 종료 처리
        (프로그램이 비정상 종료된 경우를 대비)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE activities
            SET end_time = datetime(start_time, '+1 minute')
            WHERE end_time IS NULL
        """)
        affected_rows = cursor.rowcount
        self.conn.commit()

        if affected_rows > 0:
            print(f"[DatabaseManager] {affected_rows}개의 종료되지 않은 활동 정리 완료")

        return affected_rows

    def get_activities(self, start_date: datetime, end_date: datetime,
                       tag_id: Optional[int] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """기간별 활동 조회"""
        cursor = self.conn.cursor()

        if tag_id:
            query = """
                SELECT a.*, t.name as tag_name, t.color as tag_color
                FROM activities a
                LEFT JOIN tags t ON a.tag_id = t.id
                WHERE a.start_time >= ? AND a.start_time < ? AND a.tag_id = ?
                ORDER BY a.start_time DESC
            """
            params = [start_date, end_date, tag_id]
        else:
            query = """
                SELECT a.*, t.name as tag_name, t.color as tag_color
                FROM activities a
                LEFT JOIN tags t ON a.tag_id = t.id
                WHERE a.start_time >= ? AND a.start_time < ?
                ORDER BY a.start_time DESC
            """
            params = [start_date, end_date]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]

    def get_latest_activity(self) -> Optional[Dict[str, Any]]:
        """가장 최근 활동 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM activities ORDER BY start_time DESC LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_activity_tag(self, activity_id: int, tag_id: int):
        """활동의 태그 수동 변경"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE activities SET tag_id = ?, rule_id = NULL WHERE id = ?
        """, (tag_id, activity_id))
        self.conn.commit()

    # === 통계 ===
    def get_stats_by_tag(self, start_date: datetime,
                        end_date: datetime) -> List[Dict[str, Any]]:
        """태그별 사용 시간 통계"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                t.id AS tag_id,
                t.name AS tag_name,
                t.color AS tag_color,
                SUM((julianday(COALESCE(a.end_time, datetime('now', 'localtime'))) -
                     julianday(a.start_time)) * 86400) AS total_seconds
            FROM activities a
            JOIN tags t ON a.tag_id = t.id
            WHERE a.start_time >= ? AND a.start_time < ?
            GROUP BY t.id
            ORDER BY total_seconds DESC
        """, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]

    def get_stats_by_process(self, start_date: datetime,
                            end_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """프로세스별 사용 시간 통계 (__IDLE__, __LOCKED__, LockApp.exe 제외)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                process_name,
                SUM((julianday(COALESCE(end_time, datetime('now', 'localtime'))) -
                     julianday(start_time)) * 86400) AS total_seconds,
                COUNT(*) AS activity_count
            FROM activities
            WHERE start_time >= ? AND start_time < ?
                  AND process_name IS NOT NULL
                  AND process_name NOT IN ('__IDLE__', '__LOCKED__', 'LockApp.exe')
            GROUP BY process_name
            ORDER BY total_seconds DESC
            LIMIT ?
        """, (start_date, end_date, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_timeline(self, date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """특정 날짜의 타임라인"""
        start = datetime.combine(date.date(), datetime.min.time())
        end = start + timedelta(days=1)
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.*, t.name as tag_name, t.color as tag_color
            FROM activities a
            LEFT JOIN tags t ON a.tag_id = t.id
            WHERE a.start_time >= ? AND a.start_time < ?
            ORDER BY a.start_time DESC
            LIMIT ?
        """, (start, end, limit))
        return [dict(row) for row in cursor.fetchall()]

    # === 룰 관리 ===
    def get_all_rules(self, enabled_only: bool = False,
                     order_by: str = 'priority DESC') -> List[Dict[str, Any]]:
        """모든 룰 조회"""
        cursor = self.conn.cursor()

        query = "SELECT r.*, t.name as tag_name FROM rules r JOIN tags t ON r.tag_id = t.id"
        if enabled_only:
            query += " WHERE r.enabled = 1"
        query += f" ORDER BY {order_by}"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_rule_by_id(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """ID로 룰 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.*, t.name as tag_name
            FROM rules r
            JOIN tags t ON r.tag_id = t.id
            WHERE r.id = ?
        """, (rule_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_rule(self, name: str, tag_id: int, priority: int = 0,
                   enabled: bool = True, process_pattern: Optional[str] = None,
                   url_pattern: Optional[str] = None,
                   window_title_pattern: Optional[str] = None,
                   chrome_profile: Optional[str] = None,
                   process_path_pattern: Optional[str] = None) -> int:
        """룰 생성"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO rules
            (name, priority, enabled, process_pattern, url_pattern,
             window_title_pattern, chrome_profile, process_path_pattern, tag_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, priority, enabled, process_pattern, url_pattern,
              window_title_pattern, chrome_profile, process_path_pattern, tag_id))
        self.conn.commit()
        return cursor.lastrowid

    def update_rule(self, rule_id: int, **kwargs):
        """룰 수정"""
        allowed_fields = ['name', 'priority', 'enabled', 'process_pattern',
                         'url_pattern', 'window_title_pattern',
                         'chrome_profile', 'process_path_pattern', 'tag_id']

        updates = []
        values = []
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if updates:
            cursor = self.conn.cursor()
            query = f"UPDATE rules SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            values.append(rule_id)
            cursor.execute(query, values)
            self.conn.commit()

    def delete_rule(self, rule_id: int):
        """룰 삭제"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()

    # === 미분류 재분류 ===
    def get_all_activities_for_reclassify(self) -> List[Dict[str, Any]]:
        """모든 활동 조회 (전체 재분류용)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, process_name, window_title, chrome_url, chrome_profile
            FROM activities
            ORDER BY start_time DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_activities_count(self) -> int:
        """전체 활동 개수 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM activities")
        return cursor.fetchone()[0]

    def get_unclassified_activities(self) -> List[Dict[str, Any]]:
        """미분류 태그를 가진 모든 활동 조회"""
        cursor = self.conn.cursor()

        # 미분류 태그 ID 조회
        unclassified_tag = self.get_tag_by_name('미분류')
        if not unclassified_tag:
            return []

        cursor.execute("""
            SELECT id, process_name, window_title, chrome_url, chrome_profile
            FROM activities
            WHERE tag_id = ?
            ORDER BY start_time DESC
        """, (unclassified_tag['id'],))
        return [dict(row) for row in cursor.fetchall()]

    def update_activity_classification(self, activity_id: int, tag_id: int, rule_id: Optional[int] = None):
        """활동의 분류 정보 업데이트"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE activities
            SET tag_id = ?, rule_id = ?
            WHERE id = ?
        """, (tag_id, rule_id, activity_id))
        self.conn.commit()

    def delete_activities(self, activity_ids: List[int]):
        """활동 기록 삭제"""
        if not activity_ids:
            return
        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(activity_ids))
        cursor.execute(f"DELETE FROM activities WHERE id IN ({placeholders})", activity_ids)
        self.conn.commit()

    # === 전역 설정 ===
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """설정 값 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        """설정 값 저장"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))
        self.conn.commit()

    # === 알림음 관리 ===
    def get_all_alert_sounds(self) -> List[Dict[str, Any]]:
        """모든 알림음 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alert_sounds ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_alert_sound_by_id(self, sound_id: int) -> Optional[Dict[str, Any]]:
        """ID로 알림음 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alert_sounds WHERE id = ?", (sound_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_alert_sound(self, name: str, file_path: str) -> int:
        """알림음 추가"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO alert_sounds (name, file_path) VALUES (?, ?)
        """, (name, file_path))
        self.conn.commit()
        return cursor.lastrowid

    def delete_alert_sound(self, sound_id: int):
        """알림음 삭제"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM alert_sounds WHERE id = ?", (sound_id,))
        self.conn.commit()

    # === 알림 이미지 관리 ===
    def get_all_alert_images(self) -> List[Dict[str, Any]]:
        """모든 알림 이미지 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alert_images ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_alert_image_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        """ID로 알림 이미지 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alert_images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_alert_image(self, name: str, file_path: str) -> int:
        """알림 이미지 추가"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO alert_images (name, file_path) VALUES (?, ?)
        """, (name, file_path))
        self.conn.commit()
        return cursor.lastrowid

    def delete_alert_image(self, image_id: int):
        """알림 이미지 삭제"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM alert_images WHERE id = ?", (image_id,))
        self.conn.commit()

    def close(self):
        """DB 연결 종료"""
        self.conn.close()

    def __del__(self):
        """소멸자"""
        if hasattr(self, 'conn'):
            self.conn.close()
