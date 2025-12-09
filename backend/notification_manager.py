"""
데스크톱 알림 관리 - Windows 토스트 알림
"""
import time
import threading
from typing import Optional, Dict


class NotificationManager:
    """
    Windows 토스트 알림 관리

    - winotify 라이브러리 사용
    - 쿨다운 기능으로 반복 알림 방지
    """

    # 기본 쿨다운 시간 (초)
    DEFAULT_COOLDOWN = 30

    def __init__(self, app_name: str = "Activity Tracker", cooldown: int = None):
        """
        알림 매니저 초기화

        Args:
            app_name: 알림에 표시될 앱 이름
            cooldown: 같은 태그 알림 간 최소 간격 (초)
        """
        self.app_name = app_name
        self.cooldown = cooldown or self.DEFAULT_COOLDOWN

        # 태그별 마지막 알림 시간 기록 {tag_id: timestamp}
        self._last_notification: Dict[int, float] = {}
        self._lock = threading.Lock()

        # winotify import (설치 안 됐으면 graceful fallback)
        try:
            from winotify import Notification, audio
            self._Notification = Notification
            self._audio = audio
            self._available = True
            print("[NotificationManager] winotify 초기화 완료")
        except ImportError:
            self._available = False
            print("[NotificationManager] 경고: winotify 미설치 - 알림 비활성화")

    def is_available(self) -> bool:
        """알림 기능 사용 가능 여부"""
        return self._available

    def _can_notify(self, tag_id: int, cooldown: int = None) -> bool:
        """
        쿨다운 체크 - 알림 가능 여부

        Args:
            tag_id: 태그 ID
            cooldown: 태그별 쿨다운 (초), None이면 기본값 사용

        Returns:
            True: 알림 가능, False: 쿨다운 중
        """
        effective_cooldown = cooldown if cooldown is not None else self.cooldown

        with self._lock:
            now = time.time()
            last_time = self._last_notification.get(tag_id, 0)

            if now - last_time >= effective_cooldown:
                self._last_notification[tag_id] = now
                return True
            return False

    def show(self, tag_id: int, title: str, message: str,
             icon_path: Optional[str] = None, cooldown: int = None) -> bool:
        """
        토스트 알림 표시

        Args:
            tag_id: 태그 ID (쿨다운 추적용)
            title: 알림 제목
            message: 알림 내용
            icon_path: 아이콘 경로 (선택)
            cooldown: 태그별 쿨다운 (초), None이면 기본값 사용

        Returns:
            True: 알림 표시됨, False: 쿨다운 또는 비활성화
        """
        if not self._available:
            print(f"[NotificationManager] 알림 비활성화 상태 - {title}: {message}")
            return False

        if not self._can_notify(tag_id, cooldown):
            print(f"[NotificationManager] 쿨다운 중 (tag_id={tag_id})")
            return False

        try:
            # 별도 스레드에서 알림 표시 (블로킹 방지)
            threading.Thread(
                target=self._show_notification,
                args=(title, message, icon_path),
                daemon=True
            ).start()
            return True

        except Exception as e:
            print(f"[NotificationManager] 알림 오류: {e}")
            return False

    def _show_notification(self, title: str, message: str,
                          icon_path: Optional[str] = None):
        """실제 알림 표시 (별도 스레드)"""
        try:
            toast = self._Notification(
                app_id=self.app_name,
                title=title,
                msg=message,
                duration="short"  # short(5초) or long(25초)
            )

            # 아이콘 설정 (있으면)
            if icon_path:
                toast.set_audio(self._audio.Default, loop=False)

            toast.show()
            print(f"[NotificationManager] 알림 표시: {title} - {message}")

        except Exception as e:
            print(f"[NotificationManager] 알림 표시 실패: {e}")

    def set_cooldown(self, seconds: int):
        """쿨다운 시간 설정"""
        self.cooldown = max(0, seconds)
        print(f"[NotificationManager] 쿨다운 설정: {self.cooldown}초")

    def reset_cooldown(self, tag_id: Optional[int] = None):
        """
        쿨다운 초기화

        Args:
            tag_id: 특정 태그만 초기화 (None이면 전체)
        """
        with self._lock:
            if tag_id is None:
                self._last_notification.clear()
            elif tag_id in self._last_notification:
                del self._last_notification[tag_id]
