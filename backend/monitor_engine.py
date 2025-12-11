"""
모니터링 엔진 - 백그라운드 스레드
"""
import time
from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from backend.window_tracker import WindowTracker
from backend.screen_detector import ScreenDetector
from backend.chrome_receiver import ChromeURLReceiver
from backend.notification_manager import NotificationManager


class MonitorEngine(QThread):
    """
    백그라운드 스레드로 실행
    - 활성 창 감지
    - 화면 잠금/idle 감지
    - Chrome URL 수신
    - 룰 엔진으로 분류 → DB 저장
    """

    # UI 업데이트용 시그널
    activity_detected = pyqtSignal(dict)

    # Idle 임계값 (초) - 5분
    IDLE_THRESHOLD = 300

    def __init__(self, db_manager, rule_engine):
        """
        모니터링 엔진 초기화

        Args:
            db_manager: DatabaseManager 인스턴스
            rule_engine: RuleEngine 인스턴스
        """
        super().__init__()

        self.db_manager = db_manager
        self.rule_engine = rule_engine

        # 모듈 초기화
        self.window_tracker = WindowTracker()
        self.screen_detector = ScreenDetector()
        self.chrome_receiver = ChromeURLReceiver(port=8766)
        self.notification_manager = NotificationManager(
            get_sound_settings=self._get_sound_settings,
            get_toast_enabled=self._get_toast_enabled
        )

        # 상태 변수
        self.current_activity_id: Optional[int] = None
        self.current_tag_id: Optional[int] = None  # 현재 활동의 태그 ID (알림용)
        self.last_activity_info: Optional[Dict[str, Any]] = None
        self.running = False
        self._last_played_sound_id: Optional[int] = None  # 직전 재생된 사운드 ID

        # 프로그램 시작 시 종료되지 않은 활동 정리
        self.db_manager.cleanup_unfinished_activities()

    def run(self):
        """스레드 메인 루프 (2초마다 체크)"""
        self.running = True
        print("[MonitorEngine] 모니터링 시작")

        while self.running:
            try:
                # 현재 활동 정보 수집
                activity_info = self.collect_activity_info()

                # 활동이 변경되었으면 이전 활동 종료 + 새 활동 시작
                if self._is_activity_changed(activity_info):
                    self.end_current_activity()
                    self.start_new_activity(activity_info)
                    self.last_activity_info = activity_info
                elif self.current_tag_id is not None:
                    # 동일 활동이어도 알림 체크 (쿨다운이 중복 알림 방지)
                    self._check_tag_alert(self.current_tag_id)

                time.sleep(2)

            except Exception as e:
                print(f"[MonitorEngine] 오류 발생: {e}")
                time.sleep(2)

    def stop(self):
        """모니터링 종료"""
        print("[MonitorEngine] 종료 요청됨")
        self.running = False

        # 스레드가 완전히 종료될 때까지 대기 (최대 5초)
        if self.isRunning():
            self.wait(5000)  # 5초 타임아웃

        if self.isRunning():
            print("[MonitorEngine] 경고: 스레드가 5초 내에 종료되지 않음")
            self.terminate()  # 강제 종료 (최후의 수단)

        # WebSocket 서버 종료
        self.chrome_receiver.stop()

        self.end_current_activity()
        print("[MonitorEngine] 모니터링 종료 완료")

    def collect_activity_info(self) -> Dict[str, Any]:
        """
        현재 활동 정보 수집

        중요: 화면 잠금/idle 상태를 먼저 판단하여 process_name으로 설정

        Returns:
            dict: {
                'process_name': str,
                'window_title': str,
                'chrome_url': Optional[str],
                'chrome_profile': Optional[str]
            }
        """
        # 1. 최우선: 화면 잠금 상태
        if self.screen_detector.is_locked():
            return {
                'process_name': '__LOCKED__',
                'window_title': 'Screen Locked',
                'chrome_url': None,
                'chrome_profile': None,
            }

        # 2. 유휴(idle) 상태 체크
        idle_seconds = self.screen_detector.get_idle_duration()
        if idle_seconds > self.IDLE_THRESHOLD:
            return {
                'process_name': '__IDLE__',
                'window_title': 'Idle',  # 고정값 (시간 정보 제거)
                'chrome_url': None,
                'chrome_profile': None,
            }

        # 3. 일반 활동
        window_info = self.window_tracker.get_active_window()
        if not window_info:
            # 창 정보 가져오기 실패
            return {
                'process_name': '__UNKNOWN__',
                'window_title': 'Unknown',
                'chrome_url': None,
                'chrome_profile': None,
            }

        # Chrome URL 데이터 가져오기 (Chrome 프로세스일 때만)
        chrome_data = None
        process_name_lower = window_info['process_name'].lower()
        if 'chrome' in process_name_lower:
            chrome_data = self.chrome_receiver.get_latest_url()
            if chrome_data:
                profile = chrome_data.get('profile', 'N/A')
                url = chrome_data.get('url', 'N/A')
                print(f"[MonitorEngine] Chrome 감지 - 프로필: [{profile}] URL: {url}")

        return {
            'process_name': window_info['process_name'],
            'window_title': window_info['window_title'],
            'chrome_url': chrome_data.get('url') if chrome_data else None,
            'chrome_profile': chrome_data.get('profile') if chrome_data else None,
            'process_path': window_info.get('process_path'),
        }

    def _is_activity_changed(self, new_info: Dict[str, Any]) -> bool:
        """
        활동이 변경되었는지 체크

        Args:
            new_info: 새로운 활동 정보

        Returns:
            True: 활동이 변경됨
            False: 활동이 동일함
        """
        if self.last_activity_info is None:
            return True  # 첫 활동

        # process_name이 다르면 활동 변경
        if new_info['process_name'] != self.last_activity_info['process_name']:
            return True

        # 특수 상태(__IDLE__, __LOCKED__)는 process_name만 비교
        # (window_title에 시간 정보가 포함되어 계속 바뀌므로)
        if new_info['process_name'] in ('__IDLE__', '__LOCKED__'):
            return False

        # 일반 활동은 window_title과 chrome_url도 비교
        return (
            new_info['window_title'] != self.last_activity_info['window_title'] or
            new_info['chrome_url'] != self.last_activity_info['chrome_url']
        )

    def start_new_activity(self, info: Dict[str, Any]):
        """
        새 활동 시작 → DB 저장 → 알림 체크

        Args:
            info: 활동 정보
        """
        try:
            # 룰 엔진으로 태그 분류
            tag_id, rule_id = self.rule_engine.match(info)
            self.current_tag_id = tag_id  # 알림용 태그 ID 저장

            # DB에 새 활동 저장
            self.current_activity_id = self.db_manager.create_activity(
                process_name=info['process_name'],
                window_title=info['window_title'],
                chrome_url=info['chrome_url'],
                chrome_profile=info['chrome_profile'],
                tag_id=tag_id,
                rule_id=rule_id
            )

            # UI 업데이트 시그널 발생
            self.activity_detected.emit(info)

            print(f"[MonitorEngine] 새 활동 시작: {info['process_name']} - {info['window_title'][:50]}")

            # 태그 알림 체크
            self._check_tag_alert(tag_id)

        except Exception as e:
            print(f"[MonitorEngine] 활동 저장 오류: {e}")

    def _check_tag_alert(self, tag_id: int):
        """
        태그 알림 설정 확인 및 알림 표시

        Args:
            tag_id: 태그 ID
        """
        try:
            tag = self.db_manager.get_tag_by_id(tag_id)
            if tag and tag.get('alert_enabled'):
                # 커스텀 메시지 또는 기본 메시지
                message = tag.get('alert_message') or f"'{tag['name']}' 활동이 감지되었습니다!"
                # 태그별 쿨다운 (없으면 기본값 30초)
                cooldown = tag.get('alert_cooldown') or 30
                self.notification_manager.show(
                    tag_id=tag_id,
                    title="",
                    message=message,
                    cooldown=cooldown
                )
        except Exception as e:
            print(f"[MonitorEngine] 알림 체크 오류: {e}")

    def _get_toast_enabled(self) -> bool:
        """
        윈도우 토스트 활성화 여부 조회

        Returns:
            bool: 활성화 여부 (기본값: True)
        """
        try:
            return self.db_manager.get_setting('alert_toast_enabled', '1') == '1'
        except Exception as e:
            print(f"[MonitorEngine] 토스트 설정 조회 오류: {e}")
            return True

    def _get_sound_settings(self) -> tuple:
        """
        알림음 설정 조회

        Returns:
            (enabled: bool, file_path: str or None)
        """
        import random

        try:
            enabled = self.db_manager.get_setting('alert_sound_enabled', '0') == '1'
            if not enabled:
                return (False, None)

            # 재생 모드 확인 (single/random)
            play_mode = self.db_manager.get_setting('alert_sound_mode', 'single')
            sounds = self.db_manager.get_all_alert_sounds()

            if not sounds:
                # 사운드 목록이 비어있으면 시스템 기본음
                return (True, None)

            if play_mode == 'random':
                # 랜덤 선택 (2개 이상이면 직전과 다른 사운드 선택)
                if len(sounds) >= 2 and self._last_played_sound_id is not None:
                    candidates = [s for s in sounds if s['id'] != self._last_played_sound_id]
                    selected = random.choice(candidates) if candidates else random.choice(sounds)
                else:
                    selected = random.choice(sounds)
                self._last_played_sound_id = selected['id']
                return (True, selected['file_path'])
            else:
                # 단일 선택 모드
                selected_id = self.db_manager.get_setting('alert_sound_selected', None)
                if selected_id:
                    sound = self.db_manager.get_alert_sound_by_id(int(selected_id))
                    if sound:
                        return (True, sound['file_path'])
                # 선택된 사운드가 없으면 첫 번째 사운드
                return (True, sounds[0]['file_path'])

        except Exception as e:
            print(f"[MonitorEngine] 사운드 설정 조회 오류: {e}")
            return (False, None)

    def end_current_activity(self):
        """현재 활동 종료"""
        if self.current_activity_id is not None:
            try:
                self.db_manager.end_activity(self.current_activity_id)
                print(f"[MonitorEngine] 활동 종료: ID {self.current_activity_id}")
                self.current_activity_id = None
                self.current_tag_id = None
            except Exception as e:
                print(f"[MonitorEngine] 활동 종료 오류: {e}")
