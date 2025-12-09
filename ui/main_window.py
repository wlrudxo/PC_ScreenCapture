"""
메인 윈도우
"""
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PyQt6.QtCore import pyqtSlot

from backend.database import DatabaseManager
from backend.rule_engine import RuleEngine
from backend.monitor_engine import MonitorEngine
from ui.tray_icon import SystemTrayIcon


class MainWindow(QMainWindow):
    """
    메인 윈도우
    - 탭 구조 (Dashboard, Timeline, Settings)
    - 백그라운드 모니터링 시작
    """

    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setWindowTitle("활동 추적 시스템 V2")
        self.setGeometry(100, 100, 1200, 800)

        # 백엔드 초기화
        try:
            self.db_manager = DatabaseManager()
            self.rule_engine = RuleEngine(self.db_manager)
            self.monitor_engine = MonitorEngine(self.db_manager, self.rule_engine)
        except Exception as e:
            QMessageBox.critical(
                None, "초기화 실패",
                f"데이터베이스 초기화에 실패했습니다:\n{e}\n\n프로그램을 종료합니다."
            )
            raise  # 예외를 다시 발생시켜 main.py에서 처리

        # UI 구성
        self.create_tabs()

        # 모니터링 시작
        self.monitor_engine.activity_detected.connect(self.on_activity_update)
        self.monitor_engine.start()

        # 시스템 트레이 아이콘
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show_window_requested.connect(self.show_window)
        self.tray_icon.quit_requested.connect(self.quit_application)
        self.tray_icon.show()

        print("[MainWindow] 초기화 완료")

    def create_tabs(self):
        """탭 위젯 생성"""
        from ui.dashboard_tab import DashboardTab
        from ui.timeline_tab import TimelineTab
        from ui.tag_management_tab import TagManagementTab
        from ui.settings_tab import SettingsTab

        self.tabs = QTabWidget()
        self.tabs.addTab(DashboardTab(self.db_manager), "📊 대시보드")
        self.tabs.addTab(TimelineTab(self.db_manager, self.monitor_engine), "⏱️ 타임라인")
        self.tabs.addTab(TagManagementTab(self.db_manager, self.rule_engine), "🏷️ 태그 관리")
        self.tabs.addTab(SettingsTab(self.db_manager, self.rule_engine), "⚙️ 설정")

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

    def show_window(self):
        """창 복원 및 표시"""
        self.show()
        self.activateWindow()
        print("[MainWindow] 창 복원")

    def quit_application(self):
        """애플리케이션 종료"""
        print("[MainWindow] 종료 요청됨")

        # 모니터링 종료
        self.monitor_engine.stop()

        # DB 연결 종료
        self.db_manager.close()

        # 트레이 아이콘 숨김
        self.tray_icon.hide()

        # 애플리케이션 종료
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        """
        윈도우 닫기 이벤트
        - Shift 키를 누른 채로 닫으면 완전 종료
        - 그냥 닫으면 트레이로 최소화
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication

        # Shift 키를 누른 상태면 완전 종료
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            print("[MainWindow] Shift+Close 감지 - 완전 종료")
            self.quit_application()
            event.accept()
        else:
            # 트레이로 최소화
            print("[MainWindow] 트레이로 최소화")
            self.hide()

            # 트레이 알림 (첫 번째만)
            if not hasattr(self, '_tray_notified'):
                self.tray_icon.show_message(
                    "활동 추적 시스템 V2",
                    "백그라운드에서 실행 중입니다.\nShift를 누른 채로 닫으면 완전히 종료됩니다."
                )
                self._tray_notified = True

            # 이벤트 무시 (종료하지 않음)
            event.ignore()
