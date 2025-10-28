"""
다크 테마 스타일시트 (QSS)
"""


DARK_THEME = """
/* 기본 색상 */
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}

/* 메인 윈도우 */
QMainWindow {
    background-color: #1e1e1e;
}

/* 탭 위젯 */
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #252526;
}

QTabBar::tab {
    background-color: #2d2d30;
    color: #d4d4d4;
    padding: 8px 20px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #252526;
    border-bottom: 2px solid #007acc;
}

QTabBar::tab:hover {
    background-color: #3c3c3c;
}

/* 그룹 박스 */
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 10px;
    background-color: #252526;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #d4d4d4;
    font-weight: bold;
}

/* 버튼 */
QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 16px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #808080;
}

/* 입력 필드 */
QLineEdit, QTextEdit, QSpinBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px;
    color: #d4d4d4;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border: 1px solid #007acc;
}

/* 콤보박스 */
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px;
    color: #d4d4d4;
}

QComboBox:hover {
    border: 1px solid #007acc;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #d4d4d4;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    selection-background-color: #007acc;
    color: #d4d4d4;
}

/* 체크박스 */
QCheckBox {
    spacing: 8px;
    color: #d4d4d4;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #3c3c3c;
}

QCheckBox::indicator:checked {
    background-color: #007acc;
    border: 1px solid #007acc;
}

QCheckBox::indicator:hover {
    border: 1px solid #007acc;
}

/* 리스트 위젯 */
QListWidget, QTableWidget {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    color: #d4d4d4;
    alternate-background-color: #2d2d30;
}

QListWidget::item, QTableWidget::item {
    padding: 4px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #007acc;
    color: white;
}

QListWidget::item:hover, QTableWidget::item:hover {
    background-color: #3c3c3c;
}

/* 테이블 헤더 */
QHeaderView::section {
    background-color: #2d2d30;
    color: #d4d4d4;
    padding: 6px;
    border: none;
    border-right: 1px solid #3c3c3c;
    border-bottom: 1px solid #3c3c3c;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #3c3c3c;
}

/* 스크롤바 */
QScrollBar:vertical {
    background-color: #252526;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6e6e6e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #252526;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #555555;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #6e6e6e;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* 프로그레스 바 */
QProgressBar {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    text-align: center;
    color: #d4d4d4;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 3px;
}

/* 날짜 선택 */
QDateEdit {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px;
    color: #d4d4d4;
}

QDateEdit:hover {
    border: 1px solid #007acc;
}

QDateEdit::drop-down {
    border: none;
    width: 20px;
}

QDateEdit::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #d4d4d4;
    margin-right: 5px;
}

QCalendarWidget {
    background-color: #252526;
    color: #d4d4d4;
}

QCalendarWidget QToolButton {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: none;
    border-radius: 3px;
    padding: 4px;
}

QCalendarWidget QToolButton:hover {
    background-color: #007acc;
}

QCalendarWidget QMenu {
    background-color: #3c3c3c;
    color: #d4d4d4;
}

QCalendarWidget QSpinBox {
    background-color: #3c3c3c;
    color: #d4d4d4;
}

QCalendarWidget QAbstractItemView {
    background-color: #252526;
    color: #d4d4d4;
    selection-background-color: #007acc;
}

/* 프레임 (대시보드 카드) */
QFrame {
    background-color: #2d2d30;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

/* 다이얼로그 */
QDialog {
    background-color: #1e1e1e;
}

/* 라벨 */
QLabel {
    color: #d4d4d4;
    background-color: transparent;
}

/* 메시지 박스 */
QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #d4d4d4;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* 다이얼로그 버튼 박스 */
QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* 메뉴 */
QMenu {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    color: #d4d4d4;
}

QMenu::item {
    padding: 5px 20px;
}

QMenu::item:selected {
    background-color: #007acc;
}

QMenu::separator {
    height: 1px;
    background-color: #3c3c3c;
    margin: 4px 0;
}
"""


def apply_dark_theme(app):
    """
    애플리케이션에 다크 테마 적용

    Args:
        app: QApplication 인스턴스
    """
    app.setStyleSheet(DARK_THEME)
    print("[Styles] 다크 테마 적용 완료")
