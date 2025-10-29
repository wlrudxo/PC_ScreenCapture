"""
대시보드 탭 - 오늘의 통계
"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                            QProgressBar, QTableWidget, QTableWidgetItem,
                            QDateEdit, QPushButton, QFrame, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')  # PyQt6 백엔드 사용
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


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

        # matplotlib 한글 폰트 설정 (한 번만)
        import matplotlib.pyplot as plt
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False

        # UI 구성
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 날짜 선택
        layout.addWidget(self.create_date_selector())

        # 통계 카드와 차트를 가로로 배치
        stats_and_chart = QHBoxLayout()
        stats_and_chart.setSpacing(20)

        # 통계 카드 (왼쪽) - 3열 그리드
        stats_group = QGroupBox("태그별 사용 시간")
        stats_group.setMaximumHeight(300)  # 높이 제한
        self.stats_layout = QGridLayout()
        self.stats_layout.setSpacing(15)
        stats_group.setLayout(self.stats_layout)
        stats_and_chart.addWidget(stats_group, stretch=2)

        # 파이 차트 (오른쪽)
        chart_group = QGroupBox("태그별 비율")
        chart_group.setMaximumHeight(300)  # 높이 제한
        chart_layout = QVBoxLayout()
        self.chart_canvas = self.create_pie_chart()
        chart_layout.addWidget(self.chart_canvas)
        chart_group.setLayout(chart_layout)
        stats_and_chart.addWidget(chart_group, stretch=1)

        layout.addLayout(stats_and_chart, stretch=1)

        # 프로세스별 TOP 5
        layout.addWidget(self.create_process_table(), stretch=2)

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
        self.date_edit.setMinimumWidth(150)  # 너비 확장
        self.date_edit.dateChanged.connect(self.on_date_changed)

        # 오늘 버튼
        today_btn = QPushButton("오늘")
        today_btn.clicked.connect(self.goto_today)

        # 총 활동 시간 레이블
        self.total_time_label = QLabel("총 활동 시간: 0시간 0분")
        self.total_time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.total_time_label.setStyleSheet("color: #4CAF50;")

        layout.addWidget(QLabel("날짜:"))
        layout.addWidget(self.date_edit)
        layout.addWidget(today_btn)
        layout.addStretch()
        layout.addWidget(self.total_time_label)

        group.setLayout(layout)
        return group

    def create_pie_chart(self):
        """파이 차트 위젯 생성"""
        # Figure 생성 (크기 조정)
        self.figure = Figure(figsize=(5, 5))
        self.ax = self.figure.add_subplot(111)

        # 캔버스 생성
        canvas = FigureCanvasQTAgg(self.figure)
        canvas.setMinimumSize(300, 300)

        # 초기 빈 차트
        self.ax.text(0.5, 0.5, '데이터 없음',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=self.ax.transAxes,
                    fontsize=14)
        self.ax.axis('off')

        return canvas

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
            self.update_pie_chart(tag_stats)

            # 총 활동 시간 업데이트 (자리비움 제외)
            total_seconds = sum(s['total_seconds'] or 0 for s in tag_stats if s['tag_name'] != '자리비움')
            self.update_total_time(total_seconds)

            # 프로세스별 통계
            process_stats = self.db_manager.get_stats_by_process(start, end, limit=5)
            self.update_process_table(process_stats)

        except Exception as e:
            print(f"[DashboardTab] 통계 갱신 오류: {e}")

    def update_stat_cards(self, stats):
        """태그별 통계 카드 업데이트 (3열 그리드)"""
        # 기존 카드 제거
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 총 시간 계산 (자리비움 제외)
        total_seconds = sum(s['total_seconds'] or 0 for s in stats if s['tag_name'] != '자리비움')

        # 카드 생성 (3열 그리드)
        row = 0
        col = 0
        for stat in stats:
            percentage = 0
            if total_seconds > 0 and stat['tag_name'] != '자리비움':
                percentage = (stat['total_seconds'] or 0) / total_seconds * 100

            card = self.create_stat_card(
                stat['tag_name'],
                stat['tag_color'],
                stat['total_seconds'] or 0,
                percentage
            )
            self.stats_layout.addWidget(card, row, col)

            # 다음 위치 계산 (3열)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def create_stat_card(self, tag_name, tag_color, seconds, percentage):
        """개별 통계 카드 생성"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMaximumWidth(300)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 태그 이름
        name_label = QLabel(tag_name)
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        # 사용 시간 + 퍼센트
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if percentage > 0:
            time_label = QLabel(f"{hours}시간 {minutes}분 ({percentage:.1f}%)")
        else:
            time_label = QLabel(f"{hours}시간 {minutes}분")
        time_label.setFont(QFont("Arial", 11))

        # 진행률 바
        progress = QProgressBar()
        progress.setValue(int(percentage))

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

    def update_pie_chart(self, stats):
        """파이 차트 업데이트"""
        # 차트 초기화
        self.ax.clear()

        # 데이터가 없으면 빈 메시지
        if not stats or sum(s['total_seconds'] or 0 for s in stats) == 0:
            self.ax.text(0.5, 0.5, '데이터 없음',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax.transAxes,
                        fontsize=14)
            self.ax.axis('off')
            self.chart_canvas.draw()
            return

        # 데이터 준비 (자리비움 제외)
        labels = []
        sizes = []
        colors = []

        for stat in stats:
            # 자리비움 태그는 차트에서 제외
            if stat['tag_name'] == '자리비움':
                continue

            seconds = stat['total_seconds'] or 0
            if seconds > 0:  # 0초 이상만 표시
                labels.append(stat['tag_name'])
                sizes.append(seconds)
                colors.append(stat['tag_color'])

        # 파이 차트 그리기
        if sizes:
            self.ax.pie(sizes, labels=labels, colors=colors,
                       autopct='%1.1f%%', startangle=90)
            self.ax.axis('equal')  # 원형 유지

        # 캔버스 다시 그리기
        self.chart_canvas.draw()

    def update_total_time(self, total_seconds):
        """총 활동 시간 레이블 업데이트"""
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        self.total_time_label.setText(f"총 활동 시간: {hours}시간 {minutes}분")

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

    def closeEvent(self, event):
        """위젯 닫기 전 리소스 정리"""
        # 타이머 정지
        if hasattr(self, 'timer'):
            self.timer.stop()

        # matplotlib 리소스 정리
        if hasattr(self, 'figure'):
            import matplotlib.pyplot as plt
            self.figure.clear()
            plt.close(self.figure)

        super().closeEvent(event)
