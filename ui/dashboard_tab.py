"""
대시보드 탭 - 오늘의 통계
"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QProgressBar, QTableWidget, QTableWidgetItem,
                            QDateEdit, QPushButton, QFrame, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QFont


class DashboardTab(QWidget):
    """
    오늘의 통계 대시보드
    - 날짜 선택
    - 태그별 사용 시간 (카드 + 진행률 바)
    - 프로세스별 TOP 5
    """

    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.selected_date = datetime.now().date()

        # UI 구성
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 날짜 선택
        layout.addWidget(self.create_date_selector())

        # 통계 카드
        self.stats_layout = self.create_stat_cards()
        layout.addLayout(self.stats_layout)

        # 프로세스별 TOP 5
        layout.addWidget(self.create_process_table())

        self.setLayout(layout)

        # 초기 데이터 로드
        self.refresh_stats()

        # 10초마다 자동 갱신
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(10000)

    def create_date_selector(self):
        """날짜 선택 위젯"""
        group = QGroupBox("날짜 선택")
        layout = QHBoxLayout()

        # 날짜 선택
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.on_date_changed)

        # 오늘 버튼
        today_btn = QPushButton("오늘")
        today_btn.clicked.connect(self.goto_today)

        layout.addWidget(QLabel("날짜:"))
        layout.addWidget(self.date_edit)
        layout.addWidget(today_btn)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_stat_cards(self):
        """태그별 통계 카드"""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        # 카드 컨테이너 (나중에 동적으로 생성할 예정)
        self.cards_container = layout

        return layout

    def create_process_table(self):
        """프로세스별 TOP 5 테이블"""
        group = QGroupBox("프로세스별 사용 시간 TOP 5")
        layout = QVBoxLayout()

        self.process_table = QTableWidget()
        self.process_table.setColumnCount(3)
        self.process_table.setHorizontalHeaderLabels(["프로세스", "사용 시간", "활동 수"])
        self.process_table.horizontalHeader().setStretchLastSection(True)
        self.process_table.setAlternatingRowColors(True)

        layout.addWidget(self.process_table)
        group.setLayout(layout)
        return group

    def on_date_changed(self, qdate):
        """날짜 변경 이벤트"""
        self.selected_date = qdate.toPyDate()
        self.refresh_stats()

    def goto_today(self):
        """오늘로 이동"""
        self.date_edit.setDate(QDate.currentDate())

    def refresh_stats(self):
        """통계 데이터 갱신"""
        try:
            # 선택된 날짜의 시작과 끝
            start = datetime.combine(self.selected_date, datetime.min.time())
            end = start + timedelta(days=1)

            # 태그별 통계
            tag_stats = self.db_manager.get_stats_by_tag(start, end)
            self.update_stat_cards(tag_stats)

            # 프로세스별 통계
            process_stats = self.db_manager.get_stats_by_process(start, end, limit=5)
            self.update_process_table(process_stats)

        except Exception as e:
            print(f"[DashboardTab] 통계 갱신 오류: {e}")

    def update_stat_cards(self, stats):
        """태그별 통계 카드 업데이트"""
        # 기존 카드 제거
        while self.cards_container.count():
            child = self.cards_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 총 시간 계산
        total_seconds = sum(s['total_seconds'] or 0 for s in stats)

        # 카드 생성
        for stat in stats:
            card = self.create_stat_card(
                stat['tag_name'],
                stat['tag_color'],
                stat['total_seconds'] or 0,
                total_seconds
            )
            self.cards_container.addWidget(card)

        self.cards_container.addStretch()

    def create_stat_card(self, tag_name, tag_color, seconds, total_seconds):
        """개별 통계 카드 생성"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMaximumWidth(250)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 태그 이름
        name_label = QLabel(tag_name)
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        # 사용 시간
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        time_label = QLabel(f"{hours}시간 {minutes}분")
        time_label.setFont(QFont("Arial", 12))

        # 진행률 바
        progress = QProgressBar()
        if total_seconds > 0:
            percentage = int((seconds / total_seconds) * 100)
            progress.setValue(percentage)
        else:
            progress.setValue(0)

        # 색상 적용
        progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {tag_color};
            }}
        """)

        layout.addWidget(name_label)
        layout.addWidget(time_label)
        layout.addWidget(progress)

        card.setLayout(layout)
        return card

    def update_process_table(self, stats):
        """프로세스별 테이블 업데이트"""
        self.process_table.setRowCount(len(stats))

        for row, stat in enumerate(stats):
            # 프로세스 이름
            self.process_table.setItem(row, 0, QTableWidgetItem(stat['process_name']))

            # 사용 시간
            seconds = stat['total_seconds'] or 0
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            time_str = f"{hours}시간 {minutes}분"
            self.process_table.setItem(row, 1, QTableWidgetItem(time_str))

            # 활동 수
            self.process_table.setItem(row, 2, QTableWidgetItem(str(stat['activity_count'])))

        # 열 너비 자동 조정
        self.process_table.resizeColumnsToContents()

    def __del__(self):
        """소멸자 - 타이머 정리"""
        if hasattr(self, 'timer'):
            self.timer.stop()
