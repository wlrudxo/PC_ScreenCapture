"""
타임라인 탭 - 활동 목록
"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QTableWidget, QTableWidgetItem, QDateEdit,
                            QPushButton, QComboBox, QGroupBox, QHeaderView)
from PyQt6.QtCore import Qt, QDate, pyqtSlot, QRect, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

from ui.date_navigation_widget import DateNavigationWidget
from ui.utils import format_duration


class TimelineBarWidget(QWidget):
    """
    24시간 세로 타임라인 바
    - 0시~24시 세로 표시
    - 활동을 태그별 색상 세그먼트로 시각화
    - 연속된 같은 태그 활동은 하나로 병합
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []  # {start_seconds, end_seconds, tag_color, tag_name}
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)

    def set_activities(self, activities):
        """
        활동 데이터를 받아 세그먼트로 변환
        연속된 같은 태그는 하나로 병합
        """
        if not activities:
            self.segments = []
            self.update()
            return

        # 시간 순 정렬
        sorted_activities = sorted(activities, key=lambda x: x['start_time'])

        segments = []
        current_segment = None

        for activity in sorted_activities:
            if not activity['end_time']:
                continue  # 진행 중인 활동은 스킵

            start = datetime.fromisoformat(activity['start_time'])
            end = datetime.fromisoformat(activity['end_time'])

            # 하루 기준 초 단위 (0~86400)
            start_seconds = start.hour * 3600 + start.minute * 60 + start.second
            end_seconds = end.hour * 3600 + end.minute * 60 + end.second

            tag_name = activity.get('tag_name', '미분류')
            tag_color = activity.get('tag_color', '#CCCCCC')

            # 같은 태그면 병합, 아니면 새 세그먼트
            if current_segment and current_segment['tag_name'] == tag_name:
                # 연속된 활동이면 end_seconds만 업데이트
                current_segment['end_seconds'] = end_seconds
            else:
                # 새 세그먼트 시작
                if current_segment:
                    segments.append(current_segment)

                current_segment = {
                    'start_seconds': start_seconds,
                    'end_seconds': end_seconds,
                    'tag_name': tag_name,
                    'tag_color': tag_color
                }

        # 마지막 세그먼트 추가
        if current_segment:
            segments.append(current_segment)

        self.segments = segments
        self.update()

    def paintEvent(self, event):
        """세로 타임라인 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 배경
        painter.fillRect(0, 0, width, height, QColor(240, 240, 240))

        # 시간 눈금 (3시간 간격)
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        for hour in range(0, 25, 3):
            y = int(hour / 24 * height)
            # 눈금선
            painter.drawLine(0, y, width, y)
            # 시간 레이블
            if hour < 24:
                painter.drawText(5, y + 15, f"{hour:02d}:00")

        # 세그먼트 그리기
        bar_left = 60  # 시간 레이블 60px
        bar_width = width - bar_left  # 나머지 전부 색상 바

        for segment in self.segments:
            start_ratio = segment['start_seconds'] / 86400  # 0~1
            end_ratio = segment['end_seconds'] / 86400

            y_start = int(start_ratio * height)
            y_end = int(end_ratio * height)
            segment_height = max(y_end - y_start, 1)  # 최소 1px

            # 세그먼트 색상
            color = QColor(segment['tag_color'])
            painter.fillRect(bar_left, y_start, bar_width, segment_height, color)

        # 바 테두리
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(bar_left, 0, bar_width, height)


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

        self.MAX_TABLE_ROWS = 2000
        self.REALTIME_REFRESH_DEBOUNCE_MS = 750

        self.db_manager = db_manager
        self.monitor_engine = monitor_engine
        self.selected_date = datetime.now().date()
        self.selected_tag = None  # None = 전체

        self._monitor_connected = False
        self._realtime_refresh_scheduled = False
        self._has_loaded_once = False

        # UI 구성
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 필터
        main_layout.addWidget(self.create_filters())

        # 타임라인 바 + 테이블 (수평 분할)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        # 활동 테이블 (좌측)
        content_layout.addWidget(self.create_table())

        # 24시간 타임라인 바 (우측)
        self.timeline_bar = TimelineBarWidget()
        content_layout.addWidget(self.timeline_bar)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # 초기 데이터 로드는 실제로 보일 때(탭 선택 시) 수행
        # (숨겨진 탭에서도 대량 렌더링이 발생해 앱이 멈추는 문제 방지)

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

        # 총 활동 시간 레이블
        self.total_time_label = QLabel("총 활동 시간: 0시간 0분")
        self.total_time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.total_time_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.total_time_label)

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 제목/URL은 늘어남
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 90)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)

        self.table_limit_label = QLabel("")
        self.table_limit_label.setStyleSheet("color: #888;")
        layout.addWidget(self.table_limit_label)

        group.setLayout(layout)
        return group

    def load_tag_filter(self):
        """태그 필터 콤보박스 로드"""
        tags = self.db_manager.get_all_tags()
        for tag in tags:
            self.tag_combo.addItem(tag['name'], tag['id'])

    def reload_tag_filter(self):
        """태그 필터 콤보박스 갱신 (태그 추가/수정 반영)"""
        current_tag_id = self.tag_combo.currentData()
        self.tag_combo.blockSignals(True)
        try:
            self.tag_combo.clear()
            self.tag_combo.addItem("전체 태그", None)
            tags = self.db_manager.get_all_tags()
            for tag in tags:
                self.tag_combo.addItem(tag['name'], tag['id'])

            idx = self.tag_combo.findData(current_tag_id)
            if idx >= 0:
                self.tag_combo.setCurrentIndex(idx)
        finally:
            self.tag_combo.blockSignals(False)

    def on_filter_changed(self):
        """필터 변경 이벤트"""
        self.selected_date = self.date_nav.get_date().toPyDate()
        self.selected_tag = self.tag_combo.currentData()
        self.load_timeline()

    def load_timeline(self, *, realtime: bool = False):
        """타임라인 데이터 로드"""
        try:
            # 선택된 날짜의 활동 조회
            start = datetime.combine(self.selected_date, datetime.min.time())
            end = start + timedelta(days=1)

            if realtime:
                limit = self.MAX_TABLE_ROWS
            else:
                limit = None

            if self.selected_tag:
                activities = self.db_manager.get_activities(start, end, tag_id=self.selected_tag, limit=limit)
            else:
                activities = self.db_manager.get_activities(start, end, limit=limit)

            self.populate_table(activities, update_bar=not realtime)

            if not realtime:
                # 총 활동 시간 계산 및 업데이트 (자리비움 제외)
                tag_stats = self.db_manager.get_stats_by_tag(start, end)
                total_seconds = sum(s['total_seconds'] or 0 for s in tag_stats if s['tag_name'] != '자리비움')
                self.total_time_label.setText(f"총 활동 시간: {format_duration(total_seconds)}")

        except Exception as e:
            print(f"[TimelineTab] 타임라인 로드 오류: {e}")

    def populate_table(self, activities, *, update_bar: bool = True):
        """테이블에 활동 데이터 채우기"""
        # 타임라인 바 업데이트
        if update_bar:
            self.timeline_bar.set_activities(activities)

        display_activities = activities[:self.MAX_TABLE_ROWS]
        if len(activities) > len(display_activities):
            self.table_limit_label.setText(
                f"※ 최신 {len(display_activities):,}개만 표시 중 (총 {len(activities):,}개)"
            )
        else:
            self.table_limit_label.setText("")

        # 테이블 업데이트
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(display_activities))

            for row, activity in enumerate(display_activities):
                # 시작 시간
                start_time = datetime.fromisoformat(activity['start_time'])
                self.table.setItem(row, 0, QTableWidgetItem(start_time.strftime("%H:%M:%S")))

                # 종료 시간
                if activity['end_time']:
                    end_time = datetime.fromisoformat(activity['end_time'])
                    self.table.setItem(row, 1, QTableWidgetItem(end_time.strftime("%H:%M:%S")))
                else:
                    end_time = None
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
                if end_time is not None:
                    duration = end_time - start_time
                    seconds = duration.total_seconds()
                    minutes = int(seconds // 60)
                    seconds = int(seconds % 60)
                    time_str = f"{minutes}분 {seconds}초"
                else:
                    time_str = "-"

                self.table.setItem(row, 5, QTableWidgetItem(time_str))
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

        # 통계 표시 (총 활동 수)
        print(f"[TimelineTab] {len(display_activities)}개 활동 표시됨 (총 {len(activities)}개 조회됨)")

    def _schedule_realtime_refresh(self):
        if self._realtime_refresh_scheduled:
            return
        self._realtime_refresh_scheduled = True
        QTimer.singleShot(self.REALTIME_REFRESH_DEBOUNCE_MS, self._run_realtime_refresh)

    def _run_realtime_refresh(self):
        self._realtime_refresh_scheduled = False
        if not self.isVisible():
            return
        if self.selected_date == datetime.now().date():
            self.load_timeline(realtime=True)

    def _connect_monitor(self):
        if self.monitor_engine and not self._monitor_connected:
            self.monitor_engine.activity_detected.connect(self.on_new_activity)
            self._monitor_connected = True

    def _disconnect_monitor(self):
        if self.monitor_engine and self._monitor_connected:
            try:
                self.monitor_engine.activity_detected.disconnect(self.on_new_activity)
            except Exception:
                pass
            self._monitor_connected = False

    def showEvent(self, event):
        super().showEvent(event)
        self._connect_monitor()
        self.reload_tag_filter()
        if not self._has_loaded_once:
            self._has_loaded_once = True
            QTimer.singleShot(0, self.load_timeline)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._disconnect_monitor()

    @pyqtSlot(dict)
    def on_new_activity(self, activity_info):
        """
        새 활동 추가 시 호출 (실시간 업데이트)

        Args:
            activity_info: 활동 정보 딕셔너리
        """
        if not self.isVisible():
            return
        # 현재 날짜가 오늘이면 자동 갱신 (전체 리로드는 무거워서 디바운스 + 라이트 갱신)
        self._schedule_realtime_refresh()
