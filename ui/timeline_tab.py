"""
타임라인 탭 - 활동 목록
"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QTableWidget, QTableWidgetItem, QDateEdit,
                            QPushButton, QComboBox, QGroupBox, QHeaderView)
from PyQt6.QtCore import Qt, QDate, pyqtSlot

from ui.date_navigation_widget import DateNavigationWidget


class TimelineTab(QWidget):
    """
    활동 타임라인 (테이블)
    - 날짜 필터
    - 태그 필터
    - 활동 목록 표시
    - 실시간 업데이트
    - 수동 태그 변경 (Phase 3에서 구현 예정)
    """

    def __init__(self, db_manager, monitor_engine=None):
        super().__init__()

        self.db_manager = db_manager
        self.monitor_engine = monitor_engine
        self.selected_date = datetime.now().date()
        self.selected_tag = None  # None = 전체

        # UI 구성
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 필터
        layout.addWidget(self.create_filters())

        # 테이블
        layout.addWidget(self.create_table())

        self.setLayout(layout)

        # 초기 데이터 로드
        self.load_timeline()

        # 실시간 업데이트 연결
        if self.monitor_engine:
            self.monitor_engine.activity_detected.connect(self.on_new_activity)

    def create_filters(self):
        """필터 위젯"""
        group = QGroupBox("필터")
        layout = QHBoxLayout()

        # 날짜 선택 위젯
        self.date_nav = DateNavigationWidget(label_text="날짜:", show_label=True)
        self.date_nav.date_changed.connect(self.on_filter_changed)

        # 태그 필터
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("전체 태그", None)
        self.load_tag_filter()
        self.tag_combo.currentIndexChanged.connect(self.on_filter_changed)

        # 새로고침 버튼
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.load_timeline)

        layout.addWidget(self.date_nav)
        layout.addSpacing(20)
        layout.addWidget(QLabel("태그:"))
        layout.addWidget(self.tag_combo)
        layout.addWidget(refresh_btn)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_table(self):
        """활동 테이블"""
        group = QGroupBox("활동 내역")
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "시작 시간", "종료 시간", "프로세스", "제목/URL", "태그", "시간"
        ])

        # 컬럼 너비 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 제목/URL은 늘어남
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)
        group.setLayout(layout)
        return group

    def load_tag_filter(self):
        """태그 필터 콤보박스 로드"""
        tags = self.db_manager.get_all_tags()
        for tag in tags:
            self.tag_combo.addItem(tag['name'], tag['id'])

    def on_filter_changed(self):
        """필터 변경 이벤트"""
        self.selected_date = self.date_nav.get_date().toPyDate()
        self.selected_tag = self.tag_combo.currentData()
        self.load_timeline()

    def load_timeline(self):
        """타임라인 데이터 로드"""
        try:
            # 선택된 날짜의 활동 조회
            start = datetime.combine(self.selected_date, datetime.min.time())
            end = start + timedelta(days=1)

            if self.selected_tag:
                activities = self.db_manager.get_activities(start, end, tag_id=self.selected_tag)
            else:
                activities = self.db_manager.get_activities(start, end)

            self.populate_table(activities)

        except Exception as e:
            print(f"[TimelineTab] 타임라인 로드 오류: {e}")

    def populate_table(self, activities):
        """테이블에 활동 데이터 채우기"""
        self.table.setRowCount(len(activities))

        for row, activity in enumerate(activities):
            # 시작 시간
            start_time = datetime.fromisoformat(activity['start_time'])
            self.table.setItem(row, 0, QTableWidgetItem(start_time.strftime("%H:%M:%S")))

            # 종료 시간
            if activity['end_time']:
                end_time = datetime.fromisoformat(activity['end_time'])
                self.table.setItem(row, 1, QTableWidgetItem(end_time.strftime("%H:%M:%S")))
            else:
                self.table.setItem(row, 1, QTableWidgetItem("진행 중"))

            # 프로세스
            process_name = activity['process_name'] or "N/A"
            self.table.setItem(row, 2, QTableWidgetItem(process_name))

            # 제목/URL (Chrome URL이 있으면 표시, 아니면 window_title)
            if activity['chrome_url']:
                title = activity['chrome_url']
            else:
                title = activity['window_title'] or "N/A"

            # 제목이 너무 길면 자르기
            if len(title) > 100:
                title = title[:97] + "..."

            self.table.setItem(row, 3, QTableWidgetItem(title))

            # 태그
            tag_name = activity.get('tag_name', '미분류')
            tag_item = QTableWidgetItem(tag_name)

            # 태그 색상 적용
            if activity.get('tag_color'):
                from PyQt6.QtGui import QColor, QBrush
                color = QColor(activity['tag_color'])
                # 배경색으로 적용 (연한 색상)
                color.setAlpha(80)  # 투명도 설정
                tag_item.setBackground(QBrush(color))
            self.table.setItem(row, 4, tag_item)

            # 시간
            if activity['end_time']:
                duration = end_time - start_time
                seconds = duration.total_seconds()
                minutes = int(seconds // 60)
                seconds = int(seconds % 60)
                time_str = f"{minutes}분 {seconds}초"
            else:
                time_str = "-"

            self.table.setItem(row, 5, QTableWidgetItem(time_str))

        # 통계 표시 (총 활동 수)
        print(f"[TimelineTab] {len(activities)}개 활동 로드됨")

    @pyqtSlot(dict)
    def on_new_activity(self, activity_info):
        """
        새 활동 추가 시 호출 (실시간 업데이트)

        Args:
            activity_info: 활동 정보 딕셔너리
        """
        # 현재 날짜가 오늘이면 자동 갱신
        if self.selected_date == datetime.now().date():
            self.load_timeline()
