"""
집중 모드 - 태그 기반 창 차단 유틸리티
"""
from ctypes import windll
from datetime import datetime
from typing import Optional, Dict, Any


class FocusBlocker:
    """
    태그 기반 창 차단 (최소화) 관리

    - 차단 대상 태그 관리
    - 시간대별 차단
    - 창 최소화 실행
    """

    SW_MINIMIZE = 6

    # 절대 차단하지 않는 프로세스 목록 (앱 자체 + 시스템 필수 프로세스)
    NEVER_BLOCK_PROCESSES = frozenset([
        "activitytracker.exe",  # 빌드된 앱
        "pythonw.exe",          # 개발 모드 (pyw)
        "python.exe",           # 개발 모드 (py)
    ])

    def __init__(self, db_manager):
        self.db_manager = db_manager
        # tag_id -> {start_time: "HH:MM", end_time: "HH:MM"} or None (항상 차단)
        self._blocked_tags: Dict[int, Optional[Dict[str, str]]] = {}
        self._load_blocked_tags()

    def _load_blocked_tags(self):
        """DB에서 차단 설정된 태그 로드 (시간대 포함)"""
        try:
            tags = self.db_manager.get_all_tags()
            self._blocked_tags = {}
            for t in tags:
                if t.get('block_enabled'):
                    start = t.get('block_start_time')
                    end = t.get('block_end_time')
                    if start and end:
                        self._blocked_tags[t['id']] = {
                            'start_time': start,
                            'end_time': end
                        }
                    else:
                        self._blocked_tags[t['id']] = None  # 항상 차단
        except Exception as e:
            print(f"[FocusBlocker] 차단 태그 로드 오류: {e}")
            self._blocked_tags = {}

    def reload(self):
        """차단 태그 목록 다시 로드 (설정 변경 시 호출)"""
        self._load_blocked_tags()

    def _is_in_time_range(self, start_time: str, end_time: str) -> bool:
        """현재 시간이 차단 시간대 내인지 확인"""
        try:
            now = datetime.now().time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()

            if start <= end:
                # 일반 케이스: 10:00 ~ 18:00 (18:00 미만)
                return start <= now < end
            else:
                # 자정 넘는 케이스: 22:00 ~ 06:00
                return now >= start or now < end
        except Exception as e:
            print(f"[FocusBlocker] 시간 파싱 오류: {e}")
            return True  # 파싱 실패 시 차단

    def is_blocked(self, tag_id: int) -> bool:
        """해당 태그가 현재 시간에 차단 대상인지 확인"""
        if tag_id not in self._blocked_tags:
            return False

        time_range = self._blocked_tags[tag_id]
        if time_range is None:
            return False  # 시간대 미설정 = 차단 안 함 (설정 잠금 방지)

        return self._is_in_time_range(time_range['start_time'], time_range['end_time'])

    def minimize_window(self, hwnd: int) -> bool:
        """
        지정된 창 최소화

        Args:
            hwnd: 최소화할 창 핸들

        Returns:
            True: 최소화 성공
            False: 실패
        """
        try:
            if hwnd:
                result = windll.user32.ShowWindow(hwnd, self.SW_MINIMIZE)
                print(f"[FocusBlocker] 창 최소화 실행 (hwnd={hwnd}, result={result})")
                return bool(result)
            return False
        except Exception as e:
            print(f"[FocusBlocker] 창 최소화 오류: {e}")
            return False

    def check_and_block(self, tag_id: int, hwnd: int, process_name: str = "") -> bool:
        """
        태그 확인 후 차단 대상이면 창 최소화

        Args:
            tag_id: 현재 활동의 태그 ID
            hwnd: 감지 시점의 창 핸들
            process_name: 프로세스 이름 (ActivityTracker 자체는 차단 안 함)

        Returns:
            True: 차단 실행됨
            False: 차단 대상 아님 또는 예외 프로세스
        """
        # ActivityTracker 자체는 절대 차단하지 않음 (데드락 방지)
        if process_name and process_name.lower() in self.NEVER_BLOCK_PROCESSES:
            return False

        if self.is_blocked(tag_id):
            self.minimize_window(hwnd)
            return True
        return False
