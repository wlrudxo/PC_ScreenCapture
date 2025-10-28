"""
메인 윈도우
"""
from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtCore import pyqtSlot

from backend.database import DatabaseManager
from backend.rule_engine import RuleEngine
from backend.monitor_engine import MonitorEngine


class MainWindow(QMainWindow):
    """
    메인 윈도우
    - 탭 구조 (Dashboard, Timeline)
    - 백그라운드 모니터링 시작
    """

    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setWindowTitle("활동 추적 시스템 V2")
        self.setGeometry(100, 100, 1200, 800)

        # 백엔드 초기화
        self.db_manager = DatabaseManager()
        self.rule_engine = RuleEngine(self.db_manager)
        self.monitor_engine = MonitorEngine(self.db_manager, self.rule_engine)

        # UI 구성
        self.create_tabs()

        # 모니터링 시작
        self.monitor_engine.activity_detected.connect(self.on_activity_update)
        self.monitor_engine.start()

        print("[MainWindow] 초기화 완료")

    def create_tabs(self):
        """탭 위젯 생성"""
        # Phase 2에서는 일단 간단한 탭만 생성
        # Dashboard와 Timeline은 별도 파일로 구현 예정
        from ui.dashboard_tab import DashboardTab
        from ui.timeline_tab import TimelineTab

        self.tabs = QTabWidget()
        self.tabs.addTab(DashboardTab(self.db_manager), "📊 대시보드")
        self.tabs.addTab(TimelineTab(self.db_manager, self.monitor_engine), "⏱️ 타임라인")

        self.setCentralWidget(self.tabs)

    @pyqtSlot(dict)
    def on_activity_update(self, activity_info):
        """
        활동 변경 시그널 수신

        Args:
            activity_info: 활동 정보 딕셔너리
        """
        print(f"[MainWindow] 활동 업데이트: {activity_info['process_name']}")
        # 현재 탭이 대시보드면 갱신 (나중에 구현)

    def closeEvent(self, event):
        """
        윈도우 닫기 이벤트
        나중에 시스템 트레이로 최소화할 예정
        """
        print("[MainWindow] 종료 중...")

        # 모니터링 종료
        self.monitor_engine.stop()

        # DB 연결 종료
        self.db_manager.close()

        event.accept()
