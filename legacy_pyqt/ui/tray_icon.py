"""
시스템 트레이 아이콘
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


class SystemTrayIcon(QObject):
    """
    시스템 트레이 아이콘
    - 트레이 아이콘 표시
    - 컨텍스트 메뉴 (열기/종료)
    - 더블클릭으로 창 복원
    """

    # 시그널
    show_window_requested = pyqtSignal()  # 창 열기 요청
    quit_requested = pyqtSignal()  # 종료 요청

    def __init__(self, parent=None):
        super().__init__(parent)

        # 시스템 트레이 아이콘 생성
        self.tray_icon = QSystemTrayIcon(parent)

        # 아이콘 설정 (기본 아이콘 사용)
        # TODO: 나중에 커스텀 아이콘으로 교체
        from PyQt6.QtWidgets import QApplication, QStyle
        style = QApplication.style()
        if style:
            icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            self.tray_icon.setIcon(icon)

        # 툴팁 설정
        self.tray_icon.setToolTip("활동 추적 시스템 V2")

        # 컨텍스트 메뉴 생성
        self.create_menu()

        # 더블클릭 이벤트 연결
        self.tray_icon.activated.connect(self.on_activated)

        print("[SystemTrayIcon] 초기화 완료")

    def create_menu(self):
        """컨텍스트 메뉴 생성"""
        menu = QMenu()

        # 열기 액션
        show_action = QAction("열기", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(show_action)

        # 구분선
        menu.addSeparator()

        # 종료 액션
        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def on_activated(self, reason):
        """
        트레이 아이콘 클릭 이벤트

        Args:
            reason: QSystemTrayIcon.ActivationReason
        """
        # 더블클릭 또는 트리거(싱글클릭, Linux/macOS)
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick,
                     QSystemTrayIcon.ActivationReason.Trigger):
            self.show_window_requested.emit()

    def show(self):
        """트레이 아이콘 표시"""
        self.tray_icon.show()
        print("[SystemTrayIcon] 트레이 아이콘 표시")

    def hide(self):
        """트레이 아이콘 숨김"""
        self.tray_icon.hide()

    def show_message(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information, duration=3000):
        """
        트레이 알림 메시지 표시

        Args:
            title: 알림 제목
            message: 알림 내용
            icon: 알림 아이콘 (Information, Warning, Critical)
            duration: 표시 시간 (밀리초)
        """
        self.tray_icon.showMessage(title, message, icon, duration)
