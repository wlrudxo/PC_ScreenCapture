"""
설정 탭 - 태그 및 룰 관리
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QListWidget, QTableWidget, QTableWidgetItem,
                            QGroupBox, QDialog, QLineEdit, QSpinBox, QCheckBox,
                            QComboBox, QColorDialog, QMessageBox, QHeaderView,
                            QDialogButtonBox, QFormLayout, QProgressDialog, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from datetime import datetime

from backend.auto_start import AutoStartManager
from backend.import_export import ImportExportManager


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
        self.import_export_manager = ImportExportManager(db_manager)

        # UI 구성 (세로 레이아웃)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 일반 설정
        layout.addWidget(self.create_general_settings())

        # 데이터 관리 (Import/Export)
        layout.addWidget(self.create_data_management())

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

        # 미분류 재분류 버튼
        reclassify_layout = QHBoxLayout()
        reclassify_btn = QPushButton("미분류 항목 재분류")
        reclassify_btn.setToolTip("현재 룰을 적용해 미분류 항목을 자동으로 분류합니다")
        reclassify_btn.clicked.connect(self.on_reclassify_untagged)

        reclassify_label = QLabel("현재 룰을 적용해 미분류 항목을 자동 분류")
        reclassify_label.setStyleSheet("color: #888;")

        reclassify_layout.addWidget(reclassify_btn)
        reclassify_layout.addWidget(reclassify_label)
        reclassify_layout.addStretch()

        layout.addWidget(self.auto_start_checkbox)
        layout.addLayout(reclassify_layout)
        layout.addStretch()

        group.setLayout(layout)
        group.setMaximumHeight(120)  # 높이 제한 증가
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

    def on_reclassify_untagged(self):
        """미분류 항목 재분류"""
        try:
            # 1. 미분류 활동 개수 확인
            unclassified_activities = self.db_manager.get_unclassified_activities()
            count = len(unclassified_activities)

            if count == 0:
                QMessageBox.information(self, "미분류 재분류", "재분류할 미분류 항목이 없습니다.")
                return

            # 2. 확인 다이얼로그
            reply = QMessageBox.question(
                self, "미분류 재분류",
                f"{count}개의 미분류 항목을 현재 룰에 따라 재분류하시겠습니까?\n\n"
                "※ 수동으로 태그를 변경한 항목은 영향을 받지 않습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 3. 진행률 다이얼로그
            progress = QProgressDialog("미분류 항목 재분류 중...", "취소", 0, count, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)

            # 4. 재분류 실행
            reclassified_count = 0
            for i, activity in enumerate(unclassified_activities):
                if progress.wasCanceled():
                    break

                # 활동 정보로 룰 매칭
                activity_info = {
                    'process_name': activity['process_name'],
                    'window_title': activity['window_title'],
                    'chrome_url': activity['chrome_url'],
                    'chrome_profile': activity['chrome_profile']
                }

                tag_id, rule_id = self.rule_engine.match(activity_info)

                # 미분류가 아닌 경우만 업데이트 (룰이 매치된 경우)
                unclassified_tag = self.db_manager.get_tag_by_name('미분류')
                if tag_id != unclassified_tag['id']:
                    self.db_manager.update_activity_classification(
                        activity['id'], tag_id, rule_id
                    )
                    reclassified_count += 1

                progress.setValue(i + 1)

            progress.close()

            # 5. 결과 표시
            still_unclassified = count - reclassified_count
            QMessageBox.information(
                self, "재분류 완료",
                f"재분류 완료!\n\n"
                f"- 재분류됨: {reclassified_count}개\n"
                f"- 여전히 미분류: {still_unclassified}개"
            )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"재분류 중 오류 발생:\n{str(e)}")

    def create_data_management(self):
        """데이터 관리 (Import/Export) UI"""
        group = QGroupBox("데이터 관리")
        layout = QVBoxLayout()

        # DB 백업/복원
        db_layout = QHBoxLayout()
        db_label = QLabel("데이터베이스:")
        db_label.setStyleSheet("font-weight: bold;")

        db_export_btn = QPushButton("전체 백업")
        db_export_btn.setToolTip("모든 데이터를 .db 파일로 백업합니다")
        db_export_btn.clicked.connect(self.on_export_database)

        db_import_btn = QPushButton("백업 복원")
        db_import_btn.setToolTip("백업 파일로 데이터베이스를 복원합니다 (앱 재시작 필요)")
        db_import_btn.clicked.connect(self.on_import_database)

        db_hint = QLabel("💡 활동 기록 포함")
        db_hint.setStyleSheet("color: #888; font-size: 9pt;")

        db_layout.addWidget(db_label)
        db_layout.addWidget(db_export_btn)
        db_layout.addWidget(db_import_btn)
        db_layout.addWidget(db_hint)
        db_layout.addStretch()

        # 룰 Import/Export
        rules_layout = QHBoxLayout()
        rules_label = QLabel("분류 룰:")
        rules_label.setStyleSheet("font-weight: bold;")

        rules_export_btn = QPushButton("룰 내보내기")
        rules_export_btn.setToolTip("태그와 룰을 JSON 파일로 내보냅니다")
        rules_export_btn.clicked.connect(self.on_export_rules)

        rules_import_btn = QPushButton("룰 가져오기")
        rules_import_btn.setToolTip("JSON 파일에서 태그와 룰을 가져옵니다")
        rules_import_btn.clicked.connect(self.on_import_rules)

        rules_hint = QLabel("💡 활동 기록 미포함")
        rules_hint.setStyleSheet("color: #888; font-size: 9pt;")

        rules_layout.addWidget(rules_label)
        rules_layout.addWidget(rules_export_btn)
        rules_layout.addWidget(rules_import_btn)
        rules_layout.addWidget(rules_hint)
        rules_layout.addStretch()

        layout.addLayout(db_layout)
        layout.addLayout(rules_layout)
        layout.addStretch()

        group.setLayout(layout)
        group.setMaximumHeight(120)
        return group

    # === 데이터 Import/Export ===
    def on_export_database(self):
        """DB 전체 백업"""
        try:
            # 기본 파일명
            default_name = f"activity_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "데이터베이스 백업",
                default_name,
                "Database Files (*.db);;All Files (*)"
            )

            if not file_path:
                return

            success = self.import_export_manager.export_database(file_path)

            if success:
                QMessageBox.information(
                    self, "백업 완료",
                    f"데이터베이스가 백업되었습니다:\n\n{file_path}"
                )
            else:
                QMessageBox.critical(
                    self, "백업 실패",
                    "데이터베이스 백업 중 오류가 발생했습니다."
                )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"백업 중 오류 발생:\n{str(e)}")

    def on_import_database(self):
        """DB 백업 복원"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "데이터베이스 복원",
                "",
                "Database Files (*.db);;All Files (*)"
            )

            if not file_path:
                return

            # 확인 다이얼로그
            reply = QMessageBox.warning(
                self, "데이터베이스 복원",
                "⚠️ 경고: 현재 데이터베이스의 모든 데이터가 백업 파일로 교체됩니다.\n\n"
                "계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            success, message = self.import_export_manager.import_database(file_path)

            if success:
                QMessageBox.information(
                    self, "복원 완료",
                    message
                )
            else:
                QMessageBox.critical(
                    self, "복원 실패",
                    message
                )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"복원 중 오류 발생:\n{str(e)}")

    def on_export_rules(self):
        """룰 Export (JSON)"""
        try:
            # 기본 파일명
            default_name = f"rules_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "룰 내보내기",
                default_name,
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                return

            success = self.import_export_manager.export_rules(file_path)

            if success:
                # 통계 조회
                tags = self.db_manager.get_all_tags()
                rules = self.db_manager.get_all_rules()

                QMessageBox.information(
                    self, "내보내기 완료",
                    f"룰이 내보내기되었습니다:\n\n"
                    f"{file_path}\n\n"
                    f"태그: {len(tags)}개\n"
                    f"룰: {len(rules)}개"
                )
            else:
                QMessageBox.critical(
                    self, "내보내기 실패",
                    "룰 내보내기 중 오류가 발생했습니다."
                )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 중 오류 발생:\n{str(e)}")

    def on_import_rules(self):
        """룰 Import (JSON)"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "룰 가져오기",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                return

            # 파일 유효성 검증
            valid, message, preview = self.import_export_manager.validate_rules_json(file_path)

            if not valid:
                QMessageBox.critical(
                    self, "유효하지 않은 파일",
                    f"룰 파일이 유효하지 않습니다:\n\n{message}"
                )
                return

            # Import 모드 선택
            dialog = RulesImportDialog(self, preview)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            merge_mode = dialog.get_merge_mode()

            # Import 실행
            success, result_message, stats = self.import_export_manager.import_rules(
                file_path, merge_mode
            )

            if success:
                # UI 갱신
                self.load_tags()
                self.load_rules()
                self.rule_engine.reload_rules()

                QMessageBox.information(
                    self, "가져오기 완료",
                    result_message
                )
            else:
                QMessageBox.critical(
                    self, "가져오기 실패",
                    result_message
                )

        except Exception as e:
            QMessageBox.critical(self, "오류", f"가져오기 중 오류 발생:\n{str(e)}")

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

        # 프로세스 경로 패턴
        self.process_path_edit = QLineEdit()
        if rule_data and rule_data.get('process_path_pattern'):
            self.process_path_edit.setText(rule_data['process_path_pattern'])
        self.process_path_edit.setPlaceholderText("예: *\\AnkiProgramFiles\\*, *\\Obsidian\\*")
        layout.addRow("프로세스 경로 패턴:", self.process_path_edit)

        # 프로세스 경로 힌트
        path_hint = QLabel("💡 프로그램 설치 경로로 식별 (pythonw.exe 등 동일 이름 구분)")
        path_hint.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addRow("", path_hint)

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
            'process_path_pattern': self.process_path_edit.text().strip() or None,
            'tag_id': self.tag_combo.currentData(),
        }


class RulesImportDialog(QDialog):
    """룰 Import 다이얼로그 - 병합 모드 선택"""

    def __init__(self, parent=None, preview=None):
        super().__init__(parent)

        self.setWindowTitle("룰 가져오기")
        self.setMinimumWidth(450)

        layout = QVBoxLayout()

        # 파일 정보
        if preview:
            info_group = QGroupBox("파일 정보")
            info_layout = QFormLayout()
            info_layout.addRow("내보낸 날짜:", QLabel(preview.get('export_date', '알 수 없음')))
            info_layout.addRow("버전:", QLabel(preview.get('version', '알 수 없음')))
            info_layout.addRow("태그 개수:", QLabel(str(preview.get('tags_count', 0))))
            info_layout.addRow("룰 개수:", QLabel(str(preview.get('rules_count', 0))))
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)

        # Import 모드 선택
        mode_group = QGroupBox("가져오기 모드")
        mode_layout = QVBoxLayout()

        self.merge_radio = QCheckBox("병합 모드 (기존 룰 유지 + 새 룰 추가)")
        self.merge_radio.setChecked(True)

        merge_hint = QLabel("💡 기존 룰은 그대로 유지되며, 파일의 룰이 추가됩니다.\n"
                           "   같은 이름의 태그는 기존 것을 사용합니다.")
        merge_hint.setStyleSheet("color: #888; font-size: 9pt; padding-left: 20px;")

        self.replace_radio = QCheckBox("교체 모드 (기존 룰 삭제 + 새 룰만 추가)")
        self.replace_radio.setChecked(False)

        replace_hint = QLabel("⚠️ 기존 룰이 모두 삭제되고 파일의 룰만 남습니다.\n"
                             "   태그는 유지됩니다.")
        replace_hint.setStyleSheet("color: #ff9800; font-size: 9pt; padding-left: 20px;")

        # 라디오 버튼처럼 동작하도록
        self.merge_radio.stateChanged.connect(
            lambda state: self.replace_radio.setChecked(False) if state else None
        )
        self.replace_radio.stateChanged.connect(
            lambda state: self.merge_radio.setChecked(False) if state else None
        )

        mode_layout.addWidget(self.merge_radio)
        mode_layout.addWidget(merge_hint)
        mode_layout.addSpacing(10)
        mode_layout.addWidget(self.replace_radio)
        mode_layout.addWidget(replace_hint)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_merge_mode(self):
        """병합 모드 여부 반환"""
        return self.merge_radio.isChecked()
