"""
대시보드 탭 - 일간/기간별 통계
"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                            QProgressBar, QTableWidget, QTableWidgetItem,
                            QDateEdit, QPushButton, QFrame, QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')  # PyQt6 백엔드 사용
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DashboardTab(QWidget):
    """
    대시보드 탭 (일간/기간별 하위탭 포함)
    """

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

        # 탭 위젯 생성
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(DailyStatsWidget(db_manager), "일간 통계")
        tabs.addTab(PeriodStatsWidget(db_manager), "기간별 통계")

        layout.addWidget(tabs)
        self.setLayout(layout)


class DailyStatsWidget(QWidget):
    """
    일간 통계 위젯
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

        # 이전/다음 날짜 버튼
        prev_day_btn = QPushButton("<")
        prev_day_btn.setMaximumWidth(40)
        prev_day_btn.clicked.connect(self.goto_previous_day)

        next_day_btn = QPushButton(">")
        next_day_btn.setMaximumWidth(40)
        next_day_btn.clicked.connect(self.goto_next_day)

        # 총 활동 시간 레이블
        self.total_time_label = QLabel("총 활동 시간: 0시간 0분")
        self.total_time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.total_time_label.setStyleSheet("color: #4CAF50;")

        layout.addWidget(QLabel("날짜:"))
        layout.addWidget(self.date_edit)
        layout.addWidget(today_btn)
        layout.addWidget(prev_day_btn)
        layout.addWidget(next_day_btn)
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

    def goto_previous_day(self):
        """이전 날짜로 이동"""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(-1))

    def goto_next_day(self):
        """다음 날짜로 이동"""
        current = self.date_edit.date()
        self.date_edit.setDate(current.addDays(1))

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


class PeriodStatsWidget(QWidget):
    """
    기간별 통계 위젯
    - 날짜 범위 선택 (기본: 최근 7일)
    - 날짜별 태그 사용 시간 스택 바 차트
    - 날짜 x 태그 통계 테이블
    """

    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager

        # 기본값: 최근 7일
        today = datetime.now().date()
        self.start_date = today - timedelta(days=6)  # 오늘 포함 7일
        self.end_date = today

        # matplotlib 한글 폰트 설정
        import matplotlib.pyplot as plt
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False

        # UI 구성
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 날짜 범위 선택
        layout.addWidget(self.create_date_range_selector())

        # 스택 바 차트
        layout.addWidget(self.create_stacked_chart(), stretch=2)

        # 통계 테이블
        layout.addWidget(self.create_stats_table(), stretch=1)

        self.setLayout(layout)

        # 초기 데이터 로드
        self.refresh_stats()

    def create_date_range_selector(self):
        """날짜 범위 선택 위젯"""
        group = QGroupBox("기간 선택")
        layout = QHBoxLayout()

        # 시작 날짜
        layout.addWidget(QLabel("시작:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate(self.start_date.year, self.start_date.month, self.start_date.day))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMinimumWidth(150)
        self.start_date_edit.dateChanged.connect(self.on_date_range_changed)
        layout.addWidget(self.start_date_edit)

        # 종료 날짜
        layout.addWidget(QLabel("종료:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate(self.end_date.year, self.end_date.month, self.end_date.day))
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMinimumWidth(150)
        self.end_date_edit.dateChanged.connect(self.on_date_range_changed)
        layout.addWidget(self.end_date_edit)

        # 빠른 선택 버튼
        layout.addSpacing(20)

        last7_btn = QPushButton("최근 7일")
        last7_btn.clicked.connect(lambda: self.set_quick_range(7))
        layout.addWidget(last7_btn)

        last30_btn = QPushButton("최근 30일")
        last30_btn.clicked.connect(lambda: self.set_quick_range(30))
        layout.addWidget(last30_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_stacked_chart(self):
        """스택 바 차트 위젯 생성"""
        group = QGroupBox("날짜별 태그 사용 시간")
        layout = QVBoxLayout()

        # Figure 생성
        self.figure = Figure(figsize=(12, 4))
        self.ax = self.figure.add_subplot(111)

        # 캔버스 생성
        self.chart_canvas = FigureCanvasQTAgg(self.figure)
        self.chart_canvas.setMinimumHeight(250)
        self.chart_canvas.setMaximumHeight(300)

        # 초기 빈 차트
        self.ax.text(0.5, 0.5, '데이터 없음',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=self.ax.transAxes,
                    fontsize=14)
        self.ax.axis('off')

        layout.addWidget(self.chart_canvas)
        group.setLayout(layout)
        return group

    def create_stats_table(self):
        """통계 테이블 생성"""
        group = QGroupBox("상세 통계 (날짜 x 태그)")
        layout = QVBoxLayout()

        self.stats_table = QTableWidget()
        self.stats_table.setAlternatingRowColors(True)

        layout.addWidget(self.stats_table)
        group.setLayout(layout)
        return group

    def set_quick_range(self, days: int):
        """빠른 기간 선택"""
        today = datetime.now().date()
        self.end_date = today
        self.start_date = today - timedelta(days=days - 1)  # 오늘 포함

        # UI 업데이트
        self.start_date_edit.setDate(QDate(self.start_date.year, self.start_date.month, self.start_date.day))
        self.end_date_edit.setDate(QDate(self.end_date.year, self.end_date.month, self.end_date.day))

    def on_date_range_changed(self):
        """날짜 범위 변경 이벤트"""
        self.start_date = self.start_date_edit.date().toPyDate()
        self.end_date = self.end_date_edit.date().toPyDate()
        self.refresh_stats()

    def refresh_stats(self):
        """통계 데이터 갱신"""
        try:
            # 날짜 범위 검증
            if self.start_date > self.end_date:
                return

            # 날짜 범위 순회하며 데이터 수집
            date_range = []
            current_date = self.start_date
            while current_date <= self.end_date:
                date_range.append(current_date)
                current_date += timedelta(days=1)

            # 각 날짜별로 태그 통계 수집
            all_data = {}  # {date: {tag_name: seconds}}
            all_tags = set()

            for date in date_range:
                start = datetime.combine(date, datetime.min.time())
                end = start + timedelta(days=1)

                tag_stats = self.db_manager.get_stats_by_tag(start, end)

                day_data = {}
                for stat in tag_stats:
                    tag_name = stat['tag_name']
                    # 자리비움 제외
                    if tag_name != '자리비움':
                        seconds = stat['total_seconds'] or 0
                        day_data[tag_name] = seconds
                        all_tags.add(tag_name)

                all_data[date] = day_data

            # 차트 및 테이블 업데이트
            self.update_stacked_chart(date_range, all_data, all_tags)
            self.update_stats_table(date_range, all_data, all_tags)

        except Exception as e:
            print(f"[PeriodStatsWidget] 통계 갱신 오류: {e}")

    def update_stacked_chart(self, date_range, all_data, all_tags):
        """스택 바 차트 업데이트"""
        self.ax.clear()

        if not all_tags or not date_range:
            self.ax.text(0.5, 0.5, '데이터 없음',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax.transAxes,
                        fontsize=14)
            self.ax.axis('off')
            self.chart_canvas.draw()
            return

        # 태그 정렬 (알파벳순)
        sorted_tags = sorted(all_tags)

        # 데이터 준비 (요일 포함)
        weekdays_kr = ['월', '화', '수', '목', '금', '토', '일']
        x_labels = [f"{d.strftime('%m/%d')}\n({weekdays_kr[d.weekday()]})" for d in date_range]
        x_pos = range(len(date_range))

        # 각 태그별로 바 그리기 (스택)
        bottom = [0] * len(date_range)

        # 태그별 색상 가져오기
        tag_colors = {}
        for date in date_range:
            start = datetime.combine(date, datetime.min.time())
            end = start + timedelta(days=1)
            tag_stats = self.db_manager.get_stats_by_tag(start, end)
            for stat in tag_stats:
                if stat['tag_name'] not in tag_colors:
                    tag_colors[stat['tag_name']] = stat['tag_color']

        for tag in sorted_tags:
            values = []
            for date in date_range:
                seconds = all_data[date].get(tag, 0)
                hours = seconds / 3600  # 시간 단위로 변환
                values.append(hours)

            color = tag_colors.get(tag, '#999999')
            self.ax.bar(x_pos, values, bottom=bottom, label=tag, color=color, width=0.6)

            # 다음 태그를 위한 bottom 업데이트
            bottom = [b + v for b, v in zip(bottom, values)]

        # 차트 스타일링
        self.ax.set_ylabel('시간')
        self.ax.set_xticks(x_pos)
        self.ax.set_xticklabels(x_labels, rotation=45, ha='right')
        self.ax.legend(loc='upper left')
        self.ax.grid(axis='y', alpha=0.3)

        self.figure.tight_layout()
        self.chart_canvas.draw()

    def update_stats_table(self, date_range, all_data, all_tags):
        """통계 테이블 업데이트"""
        if not all_tags or not date_range:
            self.stats_table.setRowCount(0)
            self.stats_table.setColumnCount(0)
            return

        sorted_tags = sorted(all_tags)

        # 테이블 구조: 날짜(행) x 태그(열) + 총계
        self.stats_table.setRowCount(len(date_range) + 1)  # +1 for total row
        self.stats_table.setColumnCount(len(sorted_tags) + 2)  # +2 for 날짜, 총계

        # 헤더 설정
        headers = ["날짜"] + sorted_tags + ["총계"]
        self.stats_table.setHorizontalHeaderLabels(headers)

        # 데이터 채우기
        total_by_tag = {tag: 0 for tag in sorted_tags}
        weekdays_kr = ['월', '화', '수', '목', '금', '토', '일']

        for row, date in enumerate(date_range):
            # 날짜 열 (요일 포함)
            date_str = f"{date.strftime('%Y-%m-%d')} ({weekdays_kr[date.weekday()]})"
            self.stats_table.setItem(row, 0, QTableWidgetItem(date_str))

            # 각 태그 열
            row_total = 0
            for col, tag in enumerate(sorted_tags):
                seconds = all_data[date].get(tag, 0)
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)

                time_str = f"{hours}h {minutes}m" if seconds > 0 else "-"
                self.stats_table.setItem(row, col + 1, QTableWidgetItem(time_str))

                row_total += seconds
                total_by_tag[tag] += seconds

            # 총계 열
            hours = int(row_total // 3600)
            minutes = int((row_total % 3600) // 60)
            total_str = f"{hours}h {minutes}m"
            self.stats_table.setItem(row, len(sorted_tags) + 1, QTableWidgetItem(total_str))

        # 마지막 행: 총계
        last_row = len(date_range)
        self.stats_table.setItem(last_row, 0, QTableWidgetItem("총계"))

        grand_total = 0
        for col, tag in enumerate(sorted_tags):
            seconds = total_by_tag[tag]
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)

            time_str = f"{hours}h {minutes}m" if seconds > 0 else "-"
            item = QTableWidgetItem(time_str)
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.stats_table.setItem(last_row, col + 1, item)

            grand_total += seconds

        # 전체 총계
        hours = int(grand_total // 3600)
        minutes = int((grand_total % 3600) // 60)
        total_item = QTableWidgetItem(f"{hours}h {minutes}m")
        total_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.stats_table.setItem(last_row, len(sorted_tags) + 1, total_item)

        # 열 너비 자동 조정
        self.stats_table.resizeColumnsToContents()

    def closeEvent(self, event):
        """위젯 닫기 전 리소스 정리"""
        # matplotlib 리소스 정리
        if hasattr(self, 'figure'):
            import matplotlib.pyplot as plt
            self.figure.clear()
            plt.close(self.figure)

        super().closeEvent(event)
