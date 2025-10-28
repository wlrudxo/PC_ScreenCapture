"""
설정 탭 - 태그 및 룰 관리
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QListWidget, QTableWidget, QTableWidgetItem,
                            QGroupBox, QDialog, QLineEdit, QSpinBox, QCheckBox,
                            QComboBox, QColorDialog, QMessageBox, QHeaderView,
                            QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from backend.auto_start import AutoStartManager


class SettingsTab(QWidget):
    """
    설정 탭
    - 태그 관리 (추가/수정/삭제)
    - 룰 관리 (추가/수정/삭제/우선순위)
    """

    def __init__(self, db_manager, rule_engine):
        super().__init__()

        self.db_manager = db_manager
        self.rule_engine = rule_engine

        # UI 구성 (세로 레이아웃)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 일반 설정
        layout.addWidget(self.create_general_settings())

        # 태그와 룰 관리 (가로로 배치)
        managers_layout = QHBoxLayout()
        managers_layout.setSpacing(20)

        # 왼쪽: 태그 관리
        managers_layout.addWidget(self.create_tag_manager())

        # 오른쪽: 룰 관리
        managers_layout.addWidget(self.create_rule_manager())

        layout.addLayout(managers_layout)

        self.setLayout(layout)

        # 초기 데이터 로드
        self.load_tags()
        self.load_rules()

    def create_general_settings(self):
        """일반 설정 UI"""
        group = QGroupBox("일반 설정")
        layout = QVBoxLayout()

        # 자동 시작 체크박스
        self.auto_start_checkbox = QCheckBox("Windows 시작 시 자동 실행")
        self.auto_start_checkbox.setChecked(AutoStartManager.is_enabled())
        self.auto_start_checkbox.stateChanged.connect(self.on_auto_start_changed)

        layout.addWidget(self.auto_start_checkbox)
        layout.addStretch()

        group.setLayout(layout)
        group.setMaximumHeight(100)  # 높이 제한
        return group

    def on_auto_start_changed(self, state):
        """자동 시작 설정 변경"""
        if state == Qt.CheckState.Checked.value:
            success = AutoStartManager.enable()
            if not success:
                QMessageBox.warning(self, "오류", "자동 시작 설정에 실패했습니다.")
                self.auto_start_checkbox.setChecked(False)
        else:
            success = AutoStartManager.disable()
            if not success:
                QMessageBox.warning(self, "오류", "자동 시작 해제에 실패했습니다.")
                self.auto_start_checkbox.setChecked(True)

    def create_tag_manager(self):
        """태그 관리 UI"""
        group = QGroupBox("태그 관리")
        layout = QVBoxLayout()

        # 태그 리스트
        self.tag_list = QListWidget()
        self.tag_list.itemDoubleClicked.connect(self.edit_tag)
        layout.addWidget(self.tag_list)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("추가")
        btn_add.clicked.connect(self.add_tag)
        btn_edit = QPushButton("수정")
        btn_edit.clicked.connect(self.edit_tag)
        btn_delete = QPushButton("삭제")
        btn_delete.clicked.connect(self.delete_tag)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group

    def create_rule_manager(self):
        """룰 관리 UI"""
        group = QGroupBox("분류 룰 관리")
        layout = QVBoxLayout()

        # 룰 테이블
        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(5)
        self.rule_table.setHorizontalHeaderLabels([
            "우선순위", "이름", "조건", "태그", "활성화"
        ])

        # 컬럼 너비 설정
        header = self.rule_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.rule_table.setAlternatingRowColors(True)
        self.rule_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rule_table.itemDoubleClicked.connect(self.edit_rule)

        layout.addWidget(self.rule_table)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("추가")
        btn_add.clicked.connect(self.add_rule)
        btn_edit = QPushButton("수정")
        btn_edit.clicked.connect(self.edit_rule)
        btn_delete = QPushButton("삭제")
        btn_delete.clicked.connect(self.delete_rule)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group

    # === 태그 관리 ===
    def load_tags(self):
        """태그 목록 로드"""
        self.tag_list.clear()
        try:
            tags = self.db_manager.get_all_tags()
            for tag in tags:
                item_text = f"{tag['name']} ({tag['color']})"
                self.tag_list.addItem(item_text)
                # 태그 ID를 아이템 데이터로 저장
                self.tag_list.item(self.tag_list.count() - 1).setData(Qt.ItemDataRole.UserRole, tag)
        except Exception as e:
            print(f"[SettingsTab] 태그 로드 오류: {e}")

    def add_tag(self):
        """태그 추가"""
        dialog = TagEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, color = dialog.get_tag_data()
            try:
                self.db_manager.create_tag(name, color)
                self.load_tags()
                print(f"[SettingsTab] 태그 추가됨: {name}")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"태그 추가 실패: {e}")

    def edit_tag(self):
        """태그 수정"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "알림", "수정할 태그를 선택하세요.")
            return

        tag_data = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = TagEditDialog(self, tag_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, color = dialog.get_tag_data()
            try:
                self.db_manager.update_tag(tag_data['id'], name, color)
                self.load_tags()
                print(f"[SettingsTab] 태그 수정됨: {name}")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"태그 수정 실패: {e}")

    def delete_tag(self):
        """태그 삭제"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "알림", "삭제할 태그를 선택하세요.")
            return

        tag_data = current_item.data(Qt.ItemDataRole.UserRole)

        # 이 태그를 사용하는 룰 확인
        try:
            all_rules = self.db_manager.get_all_rules()
            using_rules = [r for r in all_rules if r['tag_id'] == tag_data['id']]

            if using_rules:
                rule_names = ', '.join(r['name'] for r in using_rules[:3])
                if len(using_rules) > 3:
                    rule_names += f" 외 {len(using_rules)-3}개"

                reply = QMessageBox.question(
                    self, "확인",
                    f"'{tag_data['name']}' 태그를 사용하는 {len(using_rules)}개 룰도 함께 삭제됩니다:\n{rule_names}\n\n계속하시겠습니까?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            else:
                # 룰 없으면 일반 확인만
                reply = QMessageBox.question(
                    self, "확인",
                    f"'{tag_data['name']}' 태그를 삭제하시겠습니까?\n(기존 활동 기록의 태그는 NULL로 변경됩니다)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

            if reply == QMessageBox.StandardButton.Yes:
                self.db_manager.delete_tag(tag_data['id'])
                self.load_tags()
                self.load_rules()
                print(f"[SettingsTab] 태그 삭제됨: {tag_data['name']}")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"태그 삭제 실패: {e}")

    # === 룰 관리 ===
    def load_rules(self):
        """룰 목록 로드"""
        self.rule_table.setRowCount(0)
        try:
            rules = self.db_manager.get_all_rules(order_by='priority DESC')
            self.rule_table.setRowCount(len(rules))

            for row, rule in enumerate(rules):
                # 우선순위
                self.rule_table.setItem(row, 0, QTableWidgetItem(str(rule['priority'])))

                # 이름
                self.rule_table.setItem(row, 1, QTableWidgetItem(rule['name']))

                # 조건 (간단히 표시)
                conditions = []
                if rule.get('process_pattern'):
                    conditions.append(f"프로세스: {rule['process_pattern']}")
                if rule.get('url_pattern'):
                    conditions.append(f"URL: {rule['url_pattern']}")
                if rule.get('window_title_pattern'):
                    conditions.append(f"제목: {rule['window_title_pattern']}")
                if rule.get('chrome_profile'):
                    conditions.append(f"Chrome: {rule['chrome_profile']}")
                condition_text = " | ".join(conditions) if conditions else "조건 없음"
                self.rule_table.setItem(row, 2, QTableWidgetItem(condition_text))

                # 태그
                self.rule_table.setItem(row, 3, QTableWidgetItem(rule['tag_name']))

                # 활성화
                enabled_text = "✓" if rule['enabled'] else "✗"
                self.rule_table.setItem(row, 4, QTableWidgetItem(enabled_text))

                # 룰 데이터 저장
                for col in range(5):
                    item = self.rule_table.item(row, col)
                    if item:
                        item.setData(Qt.ItemDataRole.UserRole, rule)

        except Exception as e:
            print(f"[SettingsTab] 룰 로드 오류: {e}")

    def add_rule(self):
        """룰 추가"""
        dialog = RuleEditDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule_data = dialog.get_rule_data()
            try:
                self.db_manager.create_rule(**rule_data)
                self.rule_engine.reload_rules()  # 룰 엔진 갱신!
                self.load_rules()
                print(f"[SettingsTab] 룰 추가됨: {rule_data['name']}")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"룰 추가 실패: {e}")

    def edit_rule(self):
        """룰 수정"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "알림", "수정할 룰을 선택하세요.")
            return

        rule_data = self.rule_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        dialog = RuleEditDialog(self.db_manager, self, rule_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_rule_data()
            try:
                self.db_manager.update_rule(rule_data['id'], **updated_data)
                self.rule_engine.reload_rules()  # 룰 엔진 갱신!
                self.load_rules()
                print(f"[SettingsTab] 룰 수정됨: {updated_data['name']}")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"룰 수정 실패: {e}")

    def delete_rule(self):
        """룰 삭제"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "알림", "삭제할 룰을 선택하세요.")
            return

        rule_data = self.rule_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        # 확인 다이얼로그
        reply = QMessageBox.question(
            self, "확인",
            f"'{rule_data['name']}' 룰을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_rule(rule_data['id'])
                self.rule_engine.reload_rules()  # 룰 엔진 갱신!
                self.load_rules()
                print(f"[SettingsTab] 룰 삭제됨: {rule_data['name']}")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"룰 삭제 실패: {e}")


class TagEditDialog(QDialog):
    """태그 추가/수정 다이얼로그"""

    def __init__(self, parent=None, tag_data=None):
        super().__init__(parent)

        self.tag_data = tag_data
        self.selected_color = tag_data['color'] if tag_data else "#4CAF50"

        self.setWindowTitle("태그 편집" if tag_data else "태그 추가")
        self.setMinimumWidth(400)

        layout = QFormLayout()

        # 이름
        self.name_edit = QLineEdit()
        if tag_data:
            self.name_edit.setText(tag_data['name'])
        layout.addRow("이름:", self.name_edit)

        # 색상
        color_layout = QHBoxLayout()
        self.color_label = QLabel(self.selected_color)
        self.color_label.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px; border: 1px solid black;")
        self.color_label.setMinimumWidth(100)

        color_btn = QPushButton("색상 선택")
        color_btn.clicked.connect(self.choose_color)

        color_layout.addWidget(self.color_label)
        color_layout.addWidget(color_btn)
        color_layout.addStretch()

        layout.addRow("색상:", color_layout)

        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def choose_color(self):
        """색상 선택"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, "색상 선택")
        if color.isValid():
            self.selected_color = color.name()
            self.color_label.setText(self.selected_color)
            self.color_label.setStyleSheet(f"background-color: {self.selected_color}; padding: 5px; border: 1px solid black;")

    def accept(self):
        """다이얼로그 수락 전 검증"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "오류", "태그 이름을 입력하세요.")
            return
        if len(name) > 50:
            QMessageBox.warning(self, "오류", "태그 이름은 50자 이내여야 합니다.")
            return
        super().accept()

    def get_tag_data(self):
        """태그 데이터 반환"""
        return self.name_edit.text().strip(), self.selected_color


class RuleEditDialog(QDialog):
    """룰 추가/수정 다이얼로그"""

    def __init__(self, db_manager, parent=None, rule_data=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.rule_data = rule_data

        self.setWindowTitle("룰 편집" if rule_data else "룰 추가")
        self.setMinimumWidth(500)

        layout = QFormLayout()

        # 이름
        self.name_edit = QLineEdit()
        if rule_data:
            self.name_edit.setText(rule_data['name'])
        layout.addRow("룰 이름:", self.name_edit)

        # 우선순위
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 1000)
        self.priority_spin.setValue(rule_data['priority'] if rule_data else 50)
        layout.addRow("우선순위:", self.priority_spin)

        # 활성화
        self.enabled_check = QCheckBox("활성화")
        self.enabled_check.setChecked(rule_data['enabled'] if rule_data else True)
        layout.addRow("", self.enabled_check)

        # 구분선
        layout.addRow(QLabel("<hr>"))

        # 조건 설명
        condition_info = QLabel("📋 조건 (OR 관계 - 하나라도 일치하면 매칭)")
        condition_info.setStyleSheet("font-weight: bold; color: #007acc;")
        layout.addRow("", condition_info)

        # 프로세스 패턴
        self.process_edit = QLineEdit()
        if rule_data and rule_data.get('process_pattern'):
            self.process_edit.setText(rule_data['process_pattern'])
        self.process_edit.setPlaceholderText("예: chrome.exe, __LOCKED__, __IDLE__")
        layout.addRow("프로세스 패턴:", self.process_edit)

        # URL 패턴
        self.url_edit = QLineEdit()
        if rule_data and rule_data.get('url_pattern'):
            self.url_edit.setText(rule_data['url_pattern'])
        self.url_edit.setPlaceholderText("예: *youtube.com*, *github.com*")
        layout.addRow("URL 패턴:", self.url_edit)

        # URL 패턴 힌트
        url_hint = QLabel("💡 *를 사용하여 부분 매칭 (예: *dcinside* = dcinside가 포함된 모든 URL)")
        url_hint.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addRow("", url_hint)

        # 창 제목 패턴
        self.title_edit = QLineEdit()
        if rule_data and rule_data.get('window_title_pattern'):
            self.title_edit.setText(rule_data['window_title_pattern'])
        self.title_edit.setPlaceholderText("예: *YouTube*, *Visual Studio*")
        layout.addRow("창 제목 패턴:", self.title_edit)

        # Chrome 프로필
        self.profile_edit = QLineEdit()
        if rule_data and rule_data.get('chrome_profile'):
            self.profile_edit.setText(rule_data['chrome_profile'])
        self.profile_edit.setPlaceholderText("예: 업무용, 딴짓용")
        layout.addRow("Chrome 프로필:", self.profile_edit)

        # 구분선
        layout.addRow(QLabel("<hr>"))

        # 태그 선택
        self.tag_combo = QComboBox()
        self.load_tags()
        if rule_data:
            # 현재 태그 선택
            for i in range(self.tag_combo.count()):
                if self.tag_combo.itemData(i) == rule_data['tag_id']:
                    self.tag_combo.setCurrentIndex(i)
                    break
        layout.addRow("적용할 태그:", self.tag_combo)

        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_tags(self):
        """태그 목록 로드"""
        try:
            tags = self.db_manager.get_all_tags()
            for tag in tags:
                self.tag_combo.addItem(tag['name'], tag['id'])
        except Exception as e:
            print(f"[RuleEditDialog] 태그 로드 오류: {e}")

    def accept(self):
        """다이얼로그 수락 전 검증"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "오류", "룰 이름을 입력하세요.")
            return

        # 최소 하나의 조건 필요
        if not any([
            self.process_edit.text(),
            self.url_edit.text(),
            self.title_edit.text(),
            self.profile_edit.text()
        ]):
            QMessageBox.warning(self, "오류", "최소 하나의 조건을 입력하세요.")
            return

        # 태그 선택 확인
        if self.tag_combo.currentData() is None:
            QMessageBox.warning(self, "오류", "태그를 선택하세요.")
            return

        super().accept()

    def get_rule_data(self):
        """룰 데이터 반환"""
        return {
            'name': self.name_edit.text().strip(),
            'priority': self.priority_spin.value(),
            'enabled': self.enabled_check.isChecked(),
            'process_pattern': self.process_edit.text().strip() or None,
            'url_pattern': self.url_edit.text().strip() or None,
            'window_title_pattern': self.title_edit.text().strip() or None,
            'chrome_profile': self.profile_edit.text().strip() or None,
            'tag_id': self.tag_combo.currentData(),
        }
