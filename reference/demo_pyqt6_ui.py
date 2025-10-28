"""
PyQt6 UI 데모 - 활동 추적 대시보드
QSS 스타일링으로 모던한 디자인
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QTableWidget,
                              QTableWidgetItem, QTabWidget, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import random

class ActivityDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("활동 추적 대시보드 - Demo")
        self.setGeometry(100, 100, 1000, 700)

        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 메인 레이아웃
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 헤더
        header = self.create_header()
        layout.addWidget(header)

        # 통계 카드
        stats_layout = self.create_stats_cards()
        layout.addLayout(stats_layout)

        # 탭 위젯
        tabs = self.create_tabs()
        layout.addWidget(tabs)

        main_widget.setLayout(layout)

        # 스타일 적용
        self.apply_styles()

        # 데모용 타이머 (실시간 업데이트 시뮬레이션)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_demo_data)
        self.timer.start(2000)

    def create_header(self):
        """헤더 영역"""
        header = QFrame()
        header.setObjectName("header")

        layout = QHBoxLayout()

        title = QLabel("🔍 활동 추적 시스템")
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))

        status = QLabel("● 실행 중")
        status.setObjectName("status")
        status.setFont(QFont("Segoe UI", 12))

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(status)

        header.setLayout(layout)
        return header

    def create_stats_cards(self):
        """통계 카드 영역"""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        # 업무 시간
        work_card = self.create_stat_card("💼 업무", "3시간 42분", "62%", "#4CAF50")

        # 딴짓 시간
        slack_card = self.create_stat_card("🎮 딴짓", "1시간 28분", "25%", "#FF5722")

        # 자리비움
        idle_card = self.create_stat_card("☕ 자리비움", "47분", "13%", "#9E9E9E")

        layout.addWidget(work_card)
        layout.addWidget(slack_card)
        layout.addWidget(idle_card)

        self.work_progress = work_card.findChild(QProgressBar)
        self.slack_progress = slack_card.findChild(QProgressBar)
        self.idle_progress = idle_card.findChild(QProgressBar)

        return layout

    def create_stat_card(self, title, time, percent, color):
        """개별 통계 카드"""
        card = QFrame()
        card.setObjectName("statCard")

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 제목
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setFont(QFont("Segoe UI", 14))

        # 시간
        time_label = QLabel(time)
        time_label.setObjectName("cardValue")
        time_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))

        # 진행률 바
        progress = QProgressBar()
        progress.setObjectName("statProgress")
        progress.setValue(int(percent.replace('%', '')))
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

        # 퍼센트
        percent_label = QLabel(percent)
        percent_label.setObjectName("cardPercent")
        percent_label.setFont(QFont("Segoe UI", 12))

        layout.addWidget(title_label)
        layout.addWidget(time_label)
        layout.addWidget(progress)
        layout.addWidget(percent_label)
        layout.addStretch()

        card.setLayout(layout)
        return card

    def create_tabs(self):
        """탭 위젯 (타임라인, 앱별 통계)"""
        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")

        # 타임라인 탭
        timeline = self.create_timeline_tab()
        tabs.addTab(timeline, "📊 타임라인")

        # 앱별 통계 탭
        apps = self.create_apps_tab()
        tabs.addTab(apps, "💻 앱별 통계")

        return tabs

    def create_timeline_tab(self):
        """타임라인 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 테이블
        table = QTableWidget(5, 4)
        table.setObjectName("dataTable")
        table.setHorizontalHeaderLabels(["시간", "앱", "제목/URL", "카테고리"])

        # 샘플 데이터
        sample_data = [
            ["16:30", "Chrome", "https://github.com/...", "업무"],
            ["16:25", "PyCharm", "activity_tracker.py", "업무"],
            ["16:20", "Chrome", "https://youtube.com/...", "딴짓"],
            ["16:15", "PowerShell", "H:\\GitProject\\...", "업무"],
            ["16:10", "잠금 화면", "-", "자리비움"],
        ]

        for i, row_data in enumerate(sample_data):
            for j, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                table.setItem(i, j, item)

        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 150)
        table.setColumnWidth(2, 400)

        self.timeline_table = table

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

    def create_apps_tab(self):
        """앱별 통계 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 테이블
        table = QTableWidget(4, 3)
        table.setObjectName("dataTable")
        table.setHorizontalHeaderLabels(["앱", "사용 시간", "비율"])

        # 샘플 데이터
        sample_data = [
            ["Chrome (업무용)", "2시간 15분", "38%"],
            ["PyCharm", "1시간 30분", "25%"],
            ["Chrome (딴짓용)", "1시간 10분", "19%"],
            ["PowerShell", "45분", "13%"],
        ]

        for i, row_data in enumerate(sample_data):
            for j, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                table.setItem(i, j, item)

        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 250)
        table.setColumnWidth(1, 150)

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

    def update_demo_data(self):
        """데모용 실시간 업데이트"""
        # 진행률 랜덤 변경
        self.work_progress.setValue(random.randint(55, 65))
        self.slack_progress.setValue(random.randint(20, 30))
        self.idle_progress.setValue(random.randint(10, 15))

    def apply_styles(self):
        """QSS 스타일 적용"""
        self.setStyleSheet("""
            /* 전역 설정 */
            QMainWindow {
                background-color: #0d1117;
            }

            QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', sans-serif;
            }

            /* 헤더 */
            #header {
                background-color: #161b22;
                border-radius: 10px;
                padding: 15px;
            }

            #title {
                color: #ffffff;
            }

            #status {
                color: #3fb950;
            }

            /* 통계 카드 */
            #statCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 20px;
                min-width: 200px;
            }

            #statCard:hover {
                border: 1px solid #58a6ff;
            }

            #cardTitle {
                color: #8b949e;
            }

            #cardValue {
                color: #ffffff;
            }

            #cardPercent {
                color: #8b949e;
            }

            /* 진행률 바 */
            #statProgress {
                background-color: #21262d;
                border: none;
                border-radius: 3px;
                height: 6px;
            }

            /* 탭 */
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 10px;
                background-color: #161b22;
                padding: 10px;
            }

            QTabBar::tab {
                background-color: #21262d;
                color: #8b949e;
                padding: 10px 20px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background-color: #161b22;
                color: #ffffff;
                border-bottom: 2px solid #58a6ff;
            }

            QTabBar::tab:hover {
                background-color: #30363d;
            }

            /* 테이블 */
            #dataTable {
                background-color: #0d1117;
                border: none;
                gridline-color: #21262d;
                color: #c9d1d9;
            }

            #dataTable::item {
                padding: 8px;
                border-bottom: 1px solid #21262d;
            }

            #dataTable::item:selected {
                background-color: #1f6feb;
            }

            QHeaderView::section {
                background-color: #161b22;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #21262d;
                font-weight: bold;
            }

            /* 스크롤바 */
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #30363d;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #484f58;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

def main():
    app = QApplication(sys.argv)

    # 폰트 설정
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = ActivityDashboard()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
