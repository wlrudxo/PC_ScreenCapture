"""
집중 모드 탭 - 태그 기반 창 차단 설정
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QCheckBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class FocusTab(QWidget):
    """
    집중 모드 설정 탭

    - 태그별 차단(최소화) 설정
    - 향후 확장: 시간대 제한, 일일 허용량 등
    """

    def __init__(self, db_manager, focus_blocker=None):
        super().__init__()
        self.db_manager = db_manager
        self.focus_blocker = focus_blocker

        self._init_ui()
        self._load_tags()

    def _init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 설명
        desc_label = QLabel(
            "차단할 태그를 선택하세요. 해당 태그의 활동이 감지되면 창이 자동으로 최소화됩니다."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)

        # 태그 차단 설정 그룹
        self.tag_group = QGroupBox("태그별 차단 설정")
        self.tag_layout = QVBoxLayout()
        self.tag_layout.setSpacing(8)

        # 스크롤 영역
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.tag_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMinimumHeight(300)

        group_layout = QVBoxLayout()
        group_layout.addWidget(scroll_area)
        self.tag_group.setLayout(group_layout)

        main_layout.addWidget(self.tag_group)

        # 향후 확장 영역 (placeholder)
        future_group = QGroupBox("추가 설정 (예정)")
        future_layout = QVBoxLayout()

        placeholder = QLabel("- 시간대별 차단 (예: 14:00~17:00)\n- 일일 허용 시간 (예: 30분)\n- 차단 강도 선택")
        placeholder.setStyleSheet("color: #999;")
        future_layout.addWidget(placeholder)

        future_group.setLayout(future_layout)
        main_layout.addWidget(future_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _load_tags(self):
        """태그 목록 로드 및 체크박스 생성"""
        # 기존 위젯 제거
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.db_manager.get_all_tags()

        for tag in tags:
            # 자리비움, 미분류는 차단 대상에서 제외
            if tag['name'] in ('자리비움', '미분류'):
                continue

            row = QHBoxLayout()

            # 색상 표시
            color_label = QLabel("●")
            color_label.setStyleSheet(f"color: {tag['color']}; font-size: 16px;")
            color_label.setFixedWidth(25)
            row.addWidget(color_label)

            # 태그명
            name_label = QLabel(tag['name'])
            name_label.setFont(QFont("Arial", 11))
            name_label.setMinimumWidth(100)
            row.addWidget(name_label)

            # 차단 체크박스
            block_cb = QCheckBox("창 최소화")
            block_cb.setChecked(bool(tag.get('block_enabled')))
            block_cb.stateChanged.connect(
                lambda state, tid=tag['id']: self._on_block_changed(tid, state)
            )
            row.addWidget(block_cb)

            row.addStretch()

            # 컨테이너 위젯
            row_widget = QWidget()
            row_widget.setLayout(row)
            self.tag_layout.addWidget(row_widget)

        self.tag_layout.addStretch()

    def _on_block_changed(self, tag_id: int, state: int):
        """차단 설정 변경"""
        enabled = state == Qt.CheckState.Checked.value
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute(
                "UPDATE tags SET block_enabled = ? WHERE id = ?",
                (1 if enabled else 0, tag_id)
            )
            self.db_manager.conn.commit()

            # FocusBlocker 리로드
            if self.focus_blocker:
                self.focus_blocker.reload()

            tag = self.db_manager.get_tag_by_id(tag_id)
            status = "활성화" if enabled else "비활성화"
            print(f"[FocusTab] '{tag['name']}' 차단 {status}")

        except Exception as e:
            print(f"[FocusTab] 차단 설정 저장 오류: {e}")

    def showEvent(self, event):
        """탭 표시 시 데이터 갱신"""
        super().showEvent(event)
        self._load_tags()
