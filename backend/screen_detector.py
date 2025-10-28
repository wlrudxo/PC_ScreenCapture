"""
화면 잠금 및 유휴 상태 감지 모듈
"""
import ctypes
from ctypes import Structure, windll, byref, sizeof


class LASTINPUTINFO(Structure):
    """Windows API용 구조체"""
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('dwTime', ctypes.c_uint),
    ]


class ScreenDetector:
    """화면 잠금 및 유휴 상태 감지 클래스"""

    def is_locked(self) -> bool:
        """
        화면 잠금 상태 확인

        Returns:
            True: 화면이 잠긴 상태
            False: 화면이 잠기지 않은 상태
        """
        try:
            hDesktop = windll.user32.OpenInputDesktop(0, False, 0)
            if hDesktop == 0:
                return True  # 잠금 상태
            windll.user32.CloseDesktop(hDesktop)
            return False
        except Exception:
            return False

    def get_idle_duration(self) -> float:
        """
        마지막 키보드/마우스 입력 이후 경과 시간

        Returns:
            경과 시간(초)
        """
        try:
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = sizeof(lastInputInfo)
            windll.user32.GetLastInputInfo(byref(lastInputInfo))
            millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
        except Exception:
            return 0.0
