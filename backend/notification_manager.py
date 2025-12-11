"""
데스크톱 알림 관리 - Windows 토스트 알림
"""
import time
import threading
import winsound
from pathlib import Path
from typing import Optional, Dict, Callable


class NotificationManager:
    """
    Windows 토스트 알림 관리

    - winotify 라이브러리 사용
    - 쿨다운 기능으로 반복 알림 방지
    - 커스텀 알림음 지원 (wav 파일)
    """

    # 기본 쿨다운 시간 (초)
    DEFAULT_COOLDOWN = 30

    def __init__(self, app_name: str = "Activity Tracker", cooldown: int = None,
                 get_sound_settings: Optional[Callable[[], tuple]] = None,
                 get_toast_enabled: Optional[Callable[[], bool]] = None):
        """
        알림 매니저 초기화

        Args:
            app_name: 알림에 표시될 앱 이름
            cooldown: 같은 태그 알림 간 최소 간격 (초)
            get_sound_settings: 사운드 설정 조회 콜백 -> (enabled: bool, file_path: str)
            get_toast_enabled: 토스트 활성화 여부 조회 콜백 -> bool
        """
        self.app_name = app_name
        self.cooldown = cooldown or self.DEFAULT_COOLDOWN
        self.get_sound_settings = get_sound_settings
        self.get_toast_enabled = get_toast_enabled

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
        # 토스트/사운드 설정 확인 (한 번만 조회하여 재사용)
        toast_enabled = self._is_toast_enabled()
        sound_settings = self._get_sound_settings_once()
        sound_enabled = sound_settings[0] if sound_settings else False

        # 둘 다 off면 알림 없음
        if not toast_enabled and not sound_enabled:
            print(f"[NotificationManager] 토스트/사운드 모두 비활성화 - 알림 없음")
            return False

        if not self._available and toast_enabled:
            print(f"[NotificationManager] winotify 미설치 - 토스트 불가")
            # 사운드만 가능하면 계속 진행

        if not self._can_notify(tag_id, cooldown):
            print(f"[NotificationManager] 쿨다운 중 (tag_id={tag_id})")
            return False

        try:
            # 별도 스레드에서 알림 표시 (블로킹 방지)
            threading.Thread(
                target=self._show_notification,
                args=(title, message, icon_path, toast_enabled, sound_settings),
                daemon=True
            ).start()
            return True

        except Exception as e:
            print(f"[NotificationManager] 알림 오류: {e}")
            return False

    def _is_toast_enabled(self) -> bool:
        """토스트 활성화 여부"""
        if self.get_toast_enabled:
            try:
                return self.get_toast_enabled()
            except Exception:
                pass
        return True  # 기본값: 활성화

    def _get_sound_settings_once(self) -> Optional[tuple]:
        """사운드 설정을 한 번만 조회 (랜덤 선택 시 중복 호출 방지)"""
        if self.get_sound_settings:
            try:
                return self.get_sound_settings()
            except Exception:
                pass
        return None

    def _show_notification(self, title: str, message: str,
                          icon_path: Optional[str] = None,
                          toast_enabled: bool = True,
                          sound_settings: Optional[tuple] = None):
        """실제 알림 표시 (별도 스레드)"""
        try:
            # 토스트 표시 (활성화된 경우에만)
            if toast_enabled and self._available:
                toast = self._Notification(
                    app_id=self.app_name,
                    title=title,
                    msg=message,
                    duration="short"  # short(5초) or long(25초)
                )

                # winotify 기본 사운드 비활성화
                # set_audio(Silent, loop=False)는 토스트를 막는 버그가 있어서
                # loop 파라미터 없이 시도
                try:
                    toast.set_audio(self._audio.Silent)
                except Exception:
                    pass

                toast.show()
                print(f"[NotificationManager] 토스트 표시: {title} - {message}")
            else:
                print(f"[NotificationManager] 토스트 비활성화 - 사운드만 재생")

            # 커스텀 사운드 재생 (미리 조회된 설정 사용)
            self._play_custom_sound(sound_settings)

        except Exception as e:
            print(f"[NotificationManager] 알림 표시 실패: {e}")

    def _play_custom_sound(self, sound_settings: Optional[tuple] = None):
        """커스텀 알림음 재생"""
        if sound_settings is None:
            return

        try:
            enabled, file_path = sound_settings

            if not enabled:
                return

            if not file_path:
                # 파일 미지정 시 시스템 기본음
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                return

            # wav 파일 재생
            sound_path = Path(file_path)
            if sound_path.exists() and sound_path.suffix.lower() == '.wav':
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                print(f"[NotificationManager] 사운드 재생: {file_path}")
            else:
                print(f"[NotificationManager] 사운드 파일 없음 또는 지원되지 않는 형식: {file_path}")
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

        except Exception as e:
            print(f"[NotificationManager] 사운드 재생 실패: {e}")

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
