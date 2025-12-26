"""
설정 탭 - 일반 설정 및 데이터 관리
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QDialog, QCheckBox,
                            QMessageBox, QFileDialog, QDialogButtonBox,
                            QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt
from datetime import datetime

from backend.auto_start import AutoStartManager
from backend.import_export import ImportExportManager


class SettingsTab(QWidget):
    """
    설정 탭
    - 일반 설정 (자동 시작, 미분류 재분류)
    - 데이터 관리 (DB 백업/복원, 룰 Import/Export)
    """

    def __init__(self, db_manager, rule_engine, monitor_engine=None):
        super().__init__()

        self.db_manager = db_manager
        self.rule_engine = rule_engine
        self.monitor_engine = monitor_engine
        self.import_export_manager = ImportExportManager(db_manager)

        # UI 구성 (세로 레이아웃)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 일반 설정
        layout.addWidget(self.create_general_settings())

        # 데이터 관리 (Import/Export)
        layout.addWidget(self.create_data_management())

        # 나머지 공간 채우기
        layout.addStretch()

        self.setLayout(layout)

    def create_general_settings(self):
        """일반 설정 UI"""
        group = QGroupBox("일반 설정")
        layout = QVBoxLayout()

        # 자동 시작 체크박스
        self.auto_start_checkbox = QCheckBox("Windows 시작 시 자동 실행")
        self.auto_start_checkbox.setChecked(AutoStartManager.is_enabled())
        self.auto_start_checkbox.stateChanged.connect(self.on_auto_start_changed)
        layout.addWidget(self.auto_start_checkbox)

        # 로그 보관 일수
        log_layout = QHBoxLayout()
        log_label = QLabel("활동 로그 보관 일수:")
        self.log_days_spinbox = QSpinBox()
        self.log_days_spinbox.setRange(7, 90)
        self.log_days_spinbox.setSuffix("일")
        self.log_days_spinbox.setToolTip("recent.log에 포함할 일수 (LLM 분석용)")

        # DB에서 현재 값 로드
        current_days = self.db_manager.get_setting('log_retention_days')
        self.log_days_spinbox.setValue(int(current_days) if current_days else 30)
        self.log_days_spinbox.valueChanged.connect(self.on_log_days_changed)

        log_hint = QLabel("💡 activity_logs/recent.log")
        log_hint.setStyleSheet("color: #888; font-size: 9pt;")

        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_days_spinbox)
        log_layout.addWidget(log_hint)
        log_layout.addStretch()
        layout.addLayout(log_layout)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def on_log_days_changed(self, value):
        """로그 보관 일수 변경"""
        self.db_manager.set_setting('log_retention_days', str(value))

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

            # 모니터링 중단 콜백 (QThread는 재시작 불가하므로 stop만)
            def stop_monitoring():
                if self.monitor_engine:
                    self.monitor_engine.stop()
                    print("[SettingsTab] 모니터링 중단 (DB 복원용)")

            success, message = self.import_export_manager.import_database(
                file_path,
                pause_callback=stop_monitoring,
                resume_callback=None  # QThread 재시작 불가, 앱 재시작 필요
            )

            if success:
                QMessageBox.information(
                    self, "복원 완료",
                    message + "\n\n지금 앱을 종료합니다."
                )
                # 앱 종료 (재시작 필요)
                from PyQt6.QtWidgets import QApplication
                QApplication.quit()
            else:
                # 실패 시에도 모니터링이 중단된 상태이므로 재시작 안내
                QMessageBox.critical(
                    self, "복원 실패",
                    message + "\n\n모니터링이 중단되었습니다. 앱을 재시작해주세요."
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
