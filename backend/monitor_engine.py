"""
모니터링 엔진 - 백그라운드 스레드
"""
import time
from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from backend.window_tracker import WindowTracker
from backend.screen_detector import ScreenDetector
from backend.chrome_receiver import ChromeURLReceiver


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

        # 상태 변수
        self.current_activity_id: Optional[int] = None
        self.last_activity_info: Optional[Dict[str, Any]] = None
        self.running = False

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

        # 프로세스 경로 로그 출력
        if window_info.get('process_path'):
            print(f"[ProcessPath] {window_info['process_name']} -> {window_info['process_path']}")

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
        새 활동 시작 → DB 저장

        Args:
            info: 활동 정보
        """
        try:
            # 룰 엔진으로 태그 분류
            tag_id, rule_id = self.rule_engine.match(info)

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

        except Exception as e:
            print(f"[MonitorEngine] 활동 저장 오류: {e}")

    def end_current_activity(self):
        """현재 활동 종료"""
        if self.current_activity_id is not None:
            try:
                self.db_manager.end_activity(self.current_activity_id)
                print(f"[MonitorEngine] 활동 종료: ID {self.current_activity_id}")
                self.current_activity_id = None
            except Exception as e:
                print(f"[MonitorEngine] 활동 종료 오류: {e}")
