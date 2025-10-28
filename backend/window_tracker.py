"""
활성 창 추적 모듈
"""
import psutil
from ctypes import windll, create_unicode_buffer, wintypes, byref
from typing import Dict, Any, Optional


class WindowTracker:
    """활성 창 정보 추적 클래스"""

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """
        현재 활성화된 창의 정보 가져오기

        Returns:
            dict: {
                'window_title': str,
                'process_name': str,
                'process_path': str,
                'pid': int,
                'chrome_profile': Optional[str]
            }
            None: 정보 가져오기 실패 시
        """
        try:
            # 활성 창 핸들 가져오기
            hwnd = windll.user32.GetForegroundWindow()

            # 창 제목 가져오기
            length = windll.user32.GetWindowTextLengthW(hwnd)
            buffer = create_unicode_buffer(length + 1)
            windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
            window_title = buffer.value

            # 프로세스 ID 가져오기
            pid = wintypes.DWORD()
            windll.user32.GetWindowThreadProcessId(hwnd, byref(pid))

            # 프로세스 정보 가져오기
            process = psutil.Process(pid.value)
            process_name = process.name()
            process_path = process.exe()

            # Chrome 프로필 감지
            chrome_profile = self._detect_chrome_profile(process)

            return {
                'window_title': window_title,
                'process_name': process_name,
                'process_path': process_path,
                'pid': pid.value,
                'chrome_profile': chrome_profile,
            }

        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return None

    def _detect_chrome_profile(self, process: psutil.Process) -> Optional[str]:
        """
        Chrome 프로세스에서 프로필명 추출

        Args:
            process: psutil.Process 객체

        Returns:
            프로필명 (예: "Default", "Profile 1") 또는 None
        """
        if 'chrome.exe' not in process.name().lower():
            return None

        try:
            # 현재 프로세스의 커맨드라인에서 프로필 찾기
            cmdline = process.cmdline()
            for arg in cmdline:
                if '--profile-directory=' in arg:
                    return arg.split('=')[1]

            # 현재 프로세스에 없으면 부모 프로세스 확인
            try:
                parent = process.parent()
                if parent and 'chrome.exe' in parent.name().lower():
                    parent_cmdline = parent.cmdline()
                    for arg in parent_cmdline:
                        if '--profile-directory=' in arg:
                            return arg.split('=')[1]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # 프로필 정보 없으면 기본 프로필
            return "Default"

        except Exception:
            return None
