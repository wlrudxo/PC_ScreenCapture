"""
데이터베이스 관리 모듈
SQLite를 사용하여 캡처 이미지, 태그, 카테고리 정보를 관리합니다.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class Database:
    def __init__(self, db_path: str):
        """
        데이터베이스 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path

        # 데이터베이스 디렉토리 생성
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 테이블 생성
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 객체 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn

    def _create_tables(self):
        """데이터베이스 테이블 생성"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # captures 테이블: 캡처된 스크린샷 정보
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                monitor_num INTEGER NOT NULL,
                filepath TEXT,
                deleted_at DATETIME
            )
        """)

        # tags 테이블: 활동 태그 정보
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                category TEXT NOT NULL,
                activity TEXT NOT NULL,
                duration_min INTEGER NOT NULL,
                capture_id INTEGER
            )
        """)

        # categories 테이블: 카테고리 정보
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                activities TEXT NOT NULL
            )
        """)

        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_timestamp ON captures(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_deleted_at ON captures(deleted_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_timestamp ON tags(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_capture_id ON tags(capture_id)")

        conn.commit()
        conn.close()

    # ========== Captures 관련 메서드 ==========

    def add_capture(self, timestamp: datetime, monitor_num: int, filepath: str):
        """
        캡처 정보 추가

        Args:
            timestamp: 캡처 시간
            monitor_num: 모니터 번호 (1, 2, ...)
            filepath: 이미지 파일 경로
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO captures (timestamp, monitor_num, filepath)
            VALUES (?, ?, ?)
        """, (timestamp, monitor_num, filepath))

        conn.commit()
        conn.close()

    def get_captures_by_date(self, date: str) -> List[Dict]:
        """
        특정 날짜의 모든 캡처 조회

        Args:
            date: 날짜 문자열 (YYYY-MM-DD)

        Returns:
            캡처 정보 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM captures
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp, monitor_num
        """, (date,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_captures_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        시간 범위 내의 모든 캡처 조회

        Args:
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            캡처 정보 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM captures
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp, monitor_num
        """, (start_time, end_time))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_captures_by_time_range(self, start_time: datetime, end_time: datetime) -> int:
        """
        시간 범위 내의 캡처 삭제

        Args:
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            삭제된 레코드 수
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM captures
            WHERE timestamp >= ? AND timestamp <= ?
        """, (start_time, end_time))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count

    def get_capture_by_id(self, capture_id: int) -> Optional[Dict]:
        """
        ID로 캡처 조회

        Args:
            capture_id: 조회할 캡처 ID

        Returns:
            캡처 정보 dict 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM captures WHERE id = ?", (capture_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def mark_capture_deleted(self, capture_id: int):
        """
        Soft delete: 같은 timestamp의 모든 모니터 삭제 처리
        filepath = NULL, deleted_at = now()

        Args:
            capture_id: 삭제할 캡처 ID (어느 모니터든 가능)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 해당 캡처의 timestamp 조회
        cursor.execute("SELECT timestamp FROM captures WHERE id = ?", (capture_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return

        timestamp = row['timestamp']

        # 같은 timestamp의 모든 모니터 삭제 처리
        cursor.execute("""
            UPDATE captures
            SET filepath = NULL, deleted_at = CURRENT_TIMESTAMP
            WHERE datetime(timestamp) = datetime(?)
        """, (timestamp,))

        conn.commit()
        conn.close()

    def delete_capture_by_id(self, capture_id: int) -> Optional[str]:
        """
        특정 ID의 캡처 삭제 (Hard delete - 실제 DB에서 삭제)

        주의: 이 메서드는 레거시 코드입니다.
        새 코드에서는 mark_capture_deleted()를 사용하세요.

        Args:
            capture_id: 삭제할 캡처 ID

        Returns:
            삭제된 캡처의 파일 경로 (삭제할 파일용), 없으면 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 먼저 파일 경로 조회
        cursor.execute("SELECT filepath FROM captures WHERE id = ?", (capture_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        filepath = row['filepath']

        # 삭제
        cursor.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
        conn.commit()
        conn.close()

        return filepath

    # ========== Tags 관련 메서드 ==========

    def add_tag(self, timestamp: datetime, category: str, activity: str, duration_min: int, capture_id: int = None):
        """
        활동 태그 추가

        Args:
            timestamp: 활동 시작 시간
            category: 카테고리 (연구, 행정, 개인, 기타)
            activity: 활동 (코딩, 메일, 인터넷 등)
            duration_min: 지속 시간 (분)
            capture_id: 연결된 캡처 ID (선택)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tags (timestamp, category, activity, duration_min, capture_id)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, category, activity, duration_min, capture_id))

        conn.commit()
        conn.close()

    def get_tags_by_date(self, date: str) -> List[Dict]:
        """
        특정 날짜의 모든 태그 조회

        Args:
            date: 날짜 문자열 (YYYY-MM-DD)

        Returns:
            태그 정보 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tags
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp
        """, (date,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_tags_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        날짜 범위 내의 모든 태그 조회

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            태그 정보 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tags
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp
        """, (start_date, end_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_category_stats(self, start_date: str, end_date: str) -> List[Dict]:
        """
        기간별 카테고리 통계 조회

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            카테고리별 총 시간 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, SUM(duration_min) as total_minutes
            FROM tags
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total_minutes DESC
        """, (start_date, end_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_activity_stats(self, start_date: str, end_date: str) -> List[Dict]:
        """
        기간별 활동 통계 조회

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            활동별 총 시간 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, activity, SUM(duration_min) as total_minutes
            FROM tags
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY category, activity
            ORDER BY total_minutes DESC
        """, (start_date, end_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========== Categories 관련 메서드 ==========

    def init_categories(self, categories: List[Dict]):
        """
        카테고리 초기화 (config.json에서 불러온 데이터)

        Args:
            categories: 카테고리 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 기존 카테고리 삭제
        cursor.execute("DELETE FROM categories")

        # 새 카테고리 추가
        for cat in categories:
            cursor.execute("""
                INSERT INTO categories (name, color, activities)
                VALUES (?, ?, ?)
            """, (cat['name'], cat['color'], json.dumps(cat['activities'], ensure_ascii=False)))

        conn.commit()
        conn.close()

    def get_categories(self) -> List[Dict]:
        """
        모든 카테고리 조회

        Returns:
            카테고리 정보 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM categories ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            cat = dict(row)
            cat['activities'] = json.loads(cat['activities'])
            result.append(cat)

        return result


if __name__ == "__main__":
    # 테스트 코드
    db = Database("./data/activity.db")

    # 테스트 데이터 추가
    from datetime import datetime

    # 캡처 추가
    db.add_capture(datetime.now(), 1, "./data/screenshots/2025-10-23/14-30-00_m1.jpg")
    db.add_capture(datetime.now(), 2, "./data/screenshots/2025-10-23/14-30-00_m2.jpg")

    # 태그 추가
    db.add_tag(datetime.now(), "연구", "코딩", 60)

    print("데이터베이스 테스트 완료!")
