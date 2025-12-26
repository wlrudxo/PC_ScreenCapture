"""
집중 모드 - 태그 기반 창 차단 유틸리티
"""
from ctypes import windll
from typing import Optional, Set


class FocusBlocker:
    """
    태그 기반 창 차단 (최소화) 관리

    - 차단 대상 태그 관리
    - 창 최소화 실행
    - 향후 확장: 시간대 제한, 일일 허용량 등
    """

    SW_MINIMIZE = 6

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._blocked_tags: Set[int] = set()
        self._load_blocked_tags()

    def _load_blocked_tags(self):
        """DB에서 차단 설정된 태그 ID 로드"""
        try:
            tags = self.db_manager.get_all_tags()
            self._blocked_tags = {
                t['id'] for t in tags
                if t.get('block_enabled')
            }
        except Exception as e:
            print(f"[FocusBlocker] 차단 태그 로드 오류: {e}")
            self._blocked_tags = set()

    def reload(self):
        """차단 태그 목록 다시 로드 (설정 변경 시 호출)"""
        self._load_blocked_tags()

    def is_blocked(self, tag_id: int) -> bool:
        """해당 태그가 차단 대상인지 확인"""
        return tag_id in self._blocked_tags

    def minimize_foreground_window(self) -> bool:
        """
        현재 포그라운드 창 최소화

        Returns:
            True: 최소화 성공
            False: 실패
        """
        try:
            hwnd = windll.user32.GetForegroundWindow()
            if hwnd:
                result = windll.user32.ShowWindow(hwnd, self.SW_MINIMIZE)
                print(f"[FocusBlocker] 창 최소화 실행 (hwnd={hwnd}, result={result})")
                return bool(result)
            return False
        except Exception as e:
            print(f"[FocusBlocker] 창 최소화 오류: {e}")
            return False

    def check_and_block(self, tag_id: int) -> bool:
        """
        태그 확인 후 차단 대상이면 창 최소화

        Args:
            tag_id: 현재 활동의 태그 ID

        Returns:
            True: 차단 실행됨
            False: 차단 대상 아님
        """
        if self.is_blocked(tag_id):
            self.minimize_foreground_window()
            return True
        return False
