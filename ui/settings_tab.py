"""
설정 탭 - 일반 설정 및 데이터 관리
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QDialog, QCheckBox,
                            QMessageBox, QProgressDialog, QFileDialog,
                            QDialogButtonBox, QFormLayout, QLineEdit,
                            QListWidget, QListWidgetItem, QInputDialog)
from PyQt6.QtCore import Qt
import winsound
import uuid
from pathlib import Path
from datetime import datetime

from backend.auto_start import AutoStartManager
from backend.import_export import ImportExportManager
from backend.config import AppConfig


class SettingsTab(QWidget):
    """
    설정 탭
    - 일반 설정 (자동 시작, 미분류 재분류)
    - 데이터 관리 (DB 백업/복원, 룰 Import/Export)
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

        # 알림음 설정
        layout.addWidget(self.create_sound_settings())

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
        return group

    def create_sound_settings(self):
        """알림음 설정 UI"""
        group = QGroupBox("알림음 설정")
        layout = QVBoxLayout()

        # 알림음 사용 체크박스
        self.sound_checkbox = QCheckBox("알림음 사용")
        self.sound_checkbox.setChecked(
            self.db_manager.get_setting('alert_sound_enabled', '0') == '1'
        )
        self.sound_checkbox.stateChanged.connect(self.on_sound_enabled_changed)

        # 랜덤 재생 체크박스
        self.random_checkbox = QCheckBox("랜덤 재생 (체크 해제 시 선택한 사운드 재생)")
        current_mode = self.db_manager.get_setting('alert_sound_mode', 'single')
        self.random_checkbox.setChecked(current_mode == 'random')
        self.random_checkbox.stateChanged.connect(self.on_sound_mode_changed)

        # 사운드 목록
        self.sound_list = QListWidget()
        self.sound_list.setMaximumHeight(150)
        self.load_sound_list()
        self.sound_list.itemSelectionChanged.connect(self.on_sound_selection_changed)

        # 버튼들
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 추가")
        add_btn.clicked.connect(self.on_add_sound)

        delete_btn = QPushButton("🗑️ 삭제")
        delete_btn.clicked.connect(self.on_delete_sound)

        test_btn = QPushButton("▶ 테스트")
        test_btn.clicked.connect(self.on_test_sound)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()

        # 안내 문구
        hint_label = QLabel("💡 MP3, WAV, OGG, FLAC 지원 (WAV로 자동 변환). 사운드가 없으면 시스템 기본음 재생.")
        hint_label.setStyleSheet("color: #888; font-size: 9pt;")

        layout.addWidget(self.sound_checkbox)
        layout.addWidget(self.random_checkbox)
        layout.addWidget(self.sound_list)
        layout.addLayout(btn_layout)
        layout.addWidget(hint_label)

        group.setLayout(layout)
        return group

    def load_sound_list(self):
        """사운드 목록 로드"""
        self.sound_list.clear()
        sounds = self.db_manager.get_all_alert_sounds()
        selected_id = self.db_manager.get_setting('alert_sound_selected', None)

        for sound in sounds:
            item = QListWidgetItem(f"{sound['name']}  ({Path(sound['file_path']).name})")
            item.setData(Qt.ItemDataRole.UserRole, sound['id'])
            self.sound_list.addItem(item)

            # 선택된 사운드 표시
            if selected_id and int(selected_id) == sound['id']:
                item.setSelected(True)

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

    def on_sound_enabled_changed(self, state):
        """알림음 사용 설정 변경"""
        enabled = state == Qt.CheckState.Checked.value
        self.db_manager.set_setting('alert_sound_enabled', '1' if enabled else '0')
        print(f"[SettingsTab] 알림음 {'활성화' if enabled else '비활성화'}")

    def on_sound_mode_changed(self, state):
        """재생 모드 변경"""
        if state == Qt.CheckState.Checked.value:
            mode = 'random'
        else:
            mode = 'single'
        self.db_manager.set_setting('alert_sound_mode', mode)
        print(f"[SettingsTab] 알림음 재생 모드: {mode}")

    def on_sound_selection_changed(self):
        """사운드 선택 변경"""
        items = self.sound_list.selectedItems()
        if items:
            sound_id = items[0].data(Qt.ItemDataRole.UserRole)
            self.db_manager.set_setting('alert_sound_selected', str(sound_id))
            print(f"[SettingsTab] 선택된 사운드 ID: {sound_id}")

    def on_add_sound(self):
        """사운드 추가 (MP3는 WAV로 자동 변환)"""
        # 파일 선택
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "알림음 파일 선택",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;WAV Files (*.wav);;MP3 Files (*.mp3);;All Files (*)"
        )

        if not file_path:
            return

        source_path = Path(file_path)

        # WAV가 아니면 변환
        if source_path.suffix.lower() != '.wav':
            try:
                converted_path = self._convert_to_wav(file_path)
                if not converted_path:
                    return
                final_path = converted_path
            except Exception as e:
                QMessageBox.critical(self, "변환 실패", f"오디오 변환 중 오류:\n{e}")
                return
        else:
            # WAV는 sounds 폴더로 복사
            final_path = self._copy_to_sounds_dir(file_path)

        # 이름 입력
        default_name = source_path.stem
        name, ok = QInputDialog.getText(
            self, "사운드 이름",
            "사운드 이름을 입력하세요:",
            QLineEdit.EchoMode.Normal,
            default_name
        )

        if ok and name:
            self.db_manager.add_alert_sound(name, str(final_path))
            self.load_sound_list()
            print(f"[SettingsTab] 사운드 추가: {name} - {final_path}")

    def _convert_to_wav(self, source_path: str) -> str:
        """오디오 파일을 WAV로 변환 (ffmpeg 직접 호출)"""
        try:
            import subprocess
            import imageio_ffmpeg

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            # 저장 경로 생성
            sounds_dir = AppConfig.get_sounds_dir()
            output_name = f"{uuid.uuid4().hex}.wav"
            output_path = sounds_dir / output_name

            # ffmpeg로 변환 (덮어쓰기, 오류 시 stderr 출력)
            cmd = [
                ffmpeg_path,
                '-y',  # 덮어쓰기
                '-i', source_path,
                '-acodec', 'pcm_s16le',  # WAV 코덱
                '-ar', '44100',  # 샘플레이트
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Windows에서 콘솔 창 숨김
            )

            if result.returncode != 0:
                print(f"[SettingsTab] ffmpeg 오류: {result.stderr}")
                raise Exception(f"ffmpeg 변환 실패: {result.stderr[:200]}")

            print(f"[SettingsTab] 오디오 변환 완료: {source_path} -> {output_path}")
            return str(output_path)

        except ImportError as e:
            QMessageBox.warning(
                self, "라이브러리 필요",
                "MP3 변환을 위해 imageio-ffmpeg가 필요합니다.\n"
                "pip install imageio-ffmpeg"
            )
            return None
        except Exception as e:
            print(f"[SettingsTab] 오디오 변환 오류: {e}")
            raise

    def _copy_to_sounds_dir(self, source_path: str) -> str:
        """WAV 파일을 sounds 폴더로 복사"""
        import shutil

        sounds_dir = AppConfig.get_sounds_dir()
        output_name = f"{uuid.uuid4().hex}.wav"
        output_path = sounds_dir / output_name

        shutil.copy2(source_path, output_path)
        print(f"[SettingsTab] 파일 복사: {source_path} -> {output_path}")

        return str(output_path)

    def on_delete_sound(self):
        """사운드 삭제"""
        items = self.sound_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "삭제", "삭제할 사운드를 선택하세요.")
            return

        sound_id = items[0].data(Qt.ItemDataRole.UserRole)
        sound_name = items[0].text().split('  (')[0]

        reply = QMessageBox.question(
            self, "사운드 삭제",
            f"'{sound_name}' 사운드를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_alert_sound(sound_id)
            self.load_sound_list()
            print(f"[SettingsTab] 사운드 삭제: {sound_name}")

    def on_test_sound(self):
        """선택된 사운드 테스트"""
        items = self.sound_list.selectedItems()

        if not items:
            # 선택된 사운드 없으면 시스템 기본음
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return

        sound_id = items[0].data(Qt.ItemDataRole.UserRole)
        sound = self.db_manager.get_alert_sound_by_id(sound_id)

        if sound:
            sound_path = Path(sound['file_path'])
            if sound_path.exists() and sound_path.suffix.lower() == '.wav':
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                QMessageBox.warning(self, "오류", "파일이 없거나 지원되지 않는 형식입니다.")

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
