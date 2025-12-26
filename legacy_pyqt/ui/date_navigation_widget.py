"""
날짜 선택 위젯 (재사용 가능한 컴포넌트)
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QDateEdit, QPushButton
from PyQt6.QtCore import Qt, QDate, pyqtSignal


class DateNavigationWidget(QWidget):
    """
    날짜 선택 + 네비게이션 버튼 위젯
    - QDateEdit (캘린더 팝업)
    - 오늘 버튼
    - 이전/다음 날짜 버튼 (<, >)

    시그널:
    - date_changed(QDate): 날짜가 변경될 때 발생
    """

    date_changed = pyqtSignal(QDate)

    def __init__(self, label_text: str = "날짜:", show_label: bool = True):
        """
        Args:
            label_text: 날짜 선택 앞에 표시할 레이블 텍스트
            show_label: 레이블 표시 여부
        """
        super().__init__()

        self.show_label = show_label
        self.label_text = label_text

        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 레이블 (선택적)
        if self.show_label:
            layout.addWidget(QLabel(self.label_text))

        # 날짜 선택
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumWidth(150)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        layout.addWidget(self.date_edit)

        # 오늘 버튼
        today_btn = QPushButton("오늘")
        today_btn.clicked.connect(self.goto_today)
        layout.addWidget(today_btn)

        # 이전 날짜 버튼
        prev_btn = QPushButton("<")
        prev_btn.setMaximumWidth(40)
        prev_btn.clicked.connect(self.goto_previous_day)
        layout.addWidget(prev_btn)

        # 다음 날짜 버튼
        next_btn = QPushButton(">")
        next_btn.setMaximumWidth(40)
        next_btn.clicked.connect(self.goto_next_day)
        layout.addWidget(next_btn)

        self.setLayout(layout)

    def _on_date_changed(self, date: QDate):
        """날짜 변경 시그널 발생"""
        self.date_changed.emit(date)

    def goto_today(self):
        """오늘로 이동"""
        self.date_edit.setDate(QDate.currentDate())

    def goto_previous_day(self):
        """이전 날짜로 이동"""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(-1))

    def goto_next_day(self):
        """다음 날짜로 이동"""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(1))

    def get_date(self) -> QDate:
        """현재 선택된 날짜 반환"""
        return self.date_edit.date()

    def set_date(self, date: QDate):
        """날짜 설정 (시그널 발생)"""
        self.date_edit.setDate(date)
