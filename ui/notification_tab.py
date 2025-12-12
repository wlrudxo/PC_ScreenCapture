"""
알림 설정 탭 - 토스트, 사운드, 이미지 설정
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QCheckBox, QFileDialog,
                            QListWidget, QListWidgetItem, QInputDialog,
                            QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt
import winsound
import uuid
import shutil
from pathlib import Path

from backend.config import AppConfig


class NotificationTab(QWidget):
    """
    알림 설정 탭
    - 윈도우 토스트 설정
    - 알림음 설정
    - 알림 이미지 설정
    """

    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager

        # UI 구성
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 토스트 설정
        layout.addWidget(self._create_toast_settings())

        # 사운드 설정
        layout.addWidget(self._create_sound_settings())

        # 이미지 설정
        layout.addWidget(self._create_image_settings())

        # 나머지 공간 채우기
        layout.addStretch()

        self.setLayout(layout)

    def _create_toast_settings(self):
        """토스트 설정 UI"""
        group = QGroupBox("토스트 알림")
        layout = QVBoxLayout()

        # 윈도우 토스트 사용 체크박스
        self.toast_checkbox = QCheckBox("윈도우 토스트 사용")
        self.toast_checkbox.setChecked(
            self.db_manager.get_setting('alert_toast_enabled', '1') == '1'
        )
        self.toast_checkbox.stateChanged.connect(self._on_toast_enabled_changed)

        hint_label = QLabel("태그별 알림 설정은 '태그 관리' 탭에서 할 수 있습니다.")
        hint_label.setStyleSheet("color: #888; font-size: 9pt;")

        layout.addWidget(self.toast_checkbox)
        layout.addWidget(hint_label)

        group.setLayout(layout)
        return group

    def _create_sound_settings(self):
        """사운드 설정 UI"""
        group = QGroupBox("알림음")
        layout = QVBoxLayout()

        # 알림음 사용 체크박스
        self.sound_checkbox = QCheckBox("알림음 사용")
        self.sound_checkbox.setChecked(
            self.db_manager.get_setting('alert_sound_enabled', '0') == '1'
        )
        self.sound_checkbox.stateChanged.connect(self._on_sound_enabled_changed)

        # 랜덤 재생 체크박스
        self.random_checkbox = QCheckBox("랜덤 재생 (체크 해제 시 선택한 사운드 재생)")
        current_mode = self.db_manager.get_setting('alert_sound_mode', 'single')
        self.random_checkbox.setChecked(current_mode == 'random')
        self.random_checkbox.stateChanged.connect(self._on_sound_mode_changed)

        # 사운드 목록
        self.sound_list = QListWidget()
        self.sound_list.setMaximumHeight(150)
        self._load_sound_list()
        self.sound_list.itemSelectionChanged.connect(self._on_sound_selection_changed)

        # 버튼들
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self._on_add_sound)

        delete_btn = QPushButton("삭제")
        delete_btn.clicked.connect(self._on_delete_sound)

        test_btn = QPushButton("테스트")
        test_btn.clicked.connect(self._on_test_sound)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()

        # 안내 문구
        hint_label = QLabel("MP3, WAV, OGG, FLAC 지원 (WAV로 자동 변환). 사운드가 없으면 시스템 기본음 재생.")
        hint_label.setStyleSheet("color: #888; font-size: 9pt;")

        layout.addWidget(self.sound_checkbox)
        layout.addWidget(self.random_checkbox)
        layout.addWidget(self.sound_list)
        layout.addLayout(btn_layout)
        layout.addWidget(hint_label)

        group.setLayout(layout)
        return group

    def _create_image_settings(self):
        """이미지 설정 UI"""
        group = QGroupBox("알림 이미지")
        layout = QVBoxLayout()

        # 이미지 사용 체크박스
        self.image_checkbox = QCheckBox("토스트에 이미지 표시")
        self.image_checkbox.setChecked(
            self.db_manager.get_setting('alert_image_enabled', '0') == '1'
        )
        self.image_checkbox.stateChanged.connect(self._on_image_enabled_changed)

        # 랜덤 표시 체크박스
        self.image_random_checkbox = QCheckBox("랜덤 표시 (체크 해제 시 선택한 이미지 표시)")
        current_mode = self.db_manager.get_setting('alert_image_mode', 'single')
        self.image_random_checkbox.setChecked(current_mode == 'random')
        self.image_random_checkbox.stateChanged.connect(self._on_image_mode_changed)

        # 이미지 목록
        self.image_list = QListWidget()
        self.image_list.setMaximumHeight(150)
        self._load_image_list()
        self.image_list.itemSelectionChanged.connect(self._on_image_selection_changed)

        # 버튼들
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self._on_add_image)

        delete_btn = QPushButton("삭제")
        delete_btn.clicked.connect(self._on_delete_image)

        test_btn = QPushButton("테스트")
        test_btn.clicked.connect(self._on_test_toast)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()

        # 안내 문구
        hint_label = QLabel("PNG, JPG 지원. 2:1 비율로 크롭됩니다. 이미지가 없으면 토스트에 이미지 없이 표시.")
        hint_label.setStyleSheet("color: #888; font-size: 9pt;")

        layout.addWidget(self.image_checkbox)
        layout.addWidget(self.image_random_checkbox)
        layout.addWidget(self.image_list)
        layout.addLayout(btn_layout)
        layout.addWidget(hint_label)

        group.setLayout(layout)
        return group

    # === 토스트 설정 ===
    def _on_toast_enabled_changed(self, state):
        """토스트 사용 설정 변경"""
        enabled = state == Qt.CheckState.Checked.value
        self.db_manager.set_setting('alert_toast_enabled', '1' if enabled else '0')
        print(f"[NotificationTab] 토스트 {'활성화' if enabled else '비활성화'}")

    # === 사운드 설정 ===
    def _load_sound_list(self):
        """사운드 목록 로드"""
        self.sound_list.clear()
        sounds = self.db_manager.get_all_alert_sounds()
        selected_id = self.db_manager.get_setting('alert_sound_selected', None)

        for sound in sounds:
            item = QListWidgetItem(f"{sound['name']}  ({Path(sound['file_path']).name})")
            item.setData(Qt.ItemDataRole.UserRole, sound['id'])
            self.sound_list.addItem(item)

            if selected_id and int(selected_id) == sound['id']:
                item.setSelected(True)

    def _on_sound_enabled_changed(self, state):
        """알림음 사용 설정 변경"""
        enabled = state == Qt.CheckState.Checked.value
        self.db_manager.set_setting('alert_sound_enabled', '1' if enabled else '0')
        print(f"[NotificationTab] 알림음 {'활성화' if enabled else '비활성화'}")

    def _on_sound_mode_changed(self, state):
        """재생 모드 변경"""
        mode = 'random' if state == Qt.CheckState.Checked.value else 'single'
        self.db_manager.set_setting('alert_sound_mode', mode)
        print(f"[NotificationTab] 알림음 재생 모드: {mode}")

    def _on_sound_selection_changed(self):
        """사운드 선택 변경"""
        items = self.sound_list.selectedItems()
        if items:
            sound_id = items[0].data(Qt.ItemDataRole.UserRole)
            self.db_manager.set_setting('alert_sound_selected', str(sound_id))
            print(f"[NotificationTab] 선택된 사운드 ID: {sound_id}")

    def _on_add_sound(self):
        """사운드 추가"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "알림음 파일 선택",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*)"
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
            self._load_sound_list()
            print(f"[NotificationTab] 사운드 추가: {name}")

    def _convert_to_wav(self, source_path: str) -> str:
        """오디오 파일을 WAV로 변환"""
        try:
            import subprocess
            import imageio_ffmpeg

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            sounds_dir = AppConfig.get_sounds_dir()
            output_name = f"{uuid.uuid4().hex}.wav"
            output_path = sounds_dir / output_name

            cmd = [
                ffmpeg_path,
                '-y',
                '-i', source_path,
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode != 0:
                raise Exception(f"ffmpeg 변환 실패: {result.stderr[:200]}")

            return str(output_path)

        except ImportError:
            QMessageBox.warning(
                self, "라이브러리 필요",
                "MP3 변환을 위해 imageio-ffmpeg가 필요합니다.\npip install imageio-ffmpeg"
            )
            return None

    def _copy_to_sounds_dir(self, source_path: str) -> str:
        """WAV 파일을 sounds 폴더로 복사"""
        sounds_dir = AppConfig.get_sounds_dir()
        output_name = f"{uuid.uuid4().hex}.wav"
        output_path = sounds_dir / output_name
        shutil.copy2(source_path, output_path)
        return str(output_path)

    def _on_delete_sound(self):
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
            self._load_sound_list()

    def _on_test_sound(self):
        """선택된 사운드 테스트"""
        items = self.sound_list.selectedItems()

        if not items:
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

    # === 이미지 설정 ===
    def _load_image_list(self):
        """이미지 목록 로드"""
        self.image_list.clear()
        images = self.db_manager.get_all_alert_images()
        selected_id = self.db_manager.get_setting('alert_image_selected', None)

        for image in images:
            item = QListWidgetItem(f"{image['name']}  ({Path(image['file_path']).name})")
            item.setData(Qt.ItemDataRole.UserRole, image['id'])
            self.image_list.addItem(item)

            if selected_id and int(selected_id) == image['id']:
                item.setSelected(True)

    def _on_image_enabled_changed(self, state):
        """이미지 사용 설정 변경"""
        enabled = state == Qt.CheckState.Checked.value
        self.db_manager.set_setting('alert_image_enabled', '1' if enabled else '0')
        print(f"[NotificationTab] 알림 이미지 {'활성화' if enabled else '비활성화'}")

    def _on_image_mode_changed(self, state):
        """이미지 표시 모드 변경"""
        mode = 'random' if state == Qt.CheckState.Checked.value else 'single'
        self.db_manager.set_setting('alert_image_mode', mode)
        print(f"[NotificationTab] 알림 이미지 표시 모드: {mode}")

    def _on_image_selection_changed(self):
        """이미지 선택 변경"""
        items = self.image_list.selectedItems()
        if items:
            image_id = items[0].data(Qt.ItemDataRole.UserRole)
            self.db_manager.set_setting('alert_image_selected', str(image_id))
            print(f"[NotificationTab] 선택된 이미지 ID: {image_id}")

    def _on_add_image(self):
        """이미지 추가"""
        from ui.image_crop_dialog import ImageCropDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "알림 이미지 선택",
            "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*)"
        )

        if not file_path:
            return

        source_path = Path(file_path)

        # 크롭 다이얼로그 표시
        dialog = ImageCropDialog(file_path, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        cropped_image = dialog.get_cropped_image()
        if cropped_image is None:
            return

        # images 폴더에 저장
        images_dir = AppConfig.get_app_dir() / "images"
        images_dir.mkdir(exist_ok=True)

        output_name = f"{uuid.uuid4().hex}.png"
        output_path = images_dir / output_name
        cropped_image.save(str(output_path), "PNG")

        # 이름 입력
        default_name = source_path.stem
        name, ok = QInputDialog.getText(
            self, "이미지 이름",
            "이미지 이름을 입력하세요:",
            QLineEdit.EchoMode.Normal,
            default_name
        )

        if ok and name:
            self.db_manager.add_alert_image(name, str(output_path))
            self._load_image_list()
            print(f"[NotificationTab] 이미지 추가: {name}")

    def _on_delete_image(self):
        """이미지 삭제"""
        items = self.image_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "삭제", "삭제할 이미지를 선택하세요.")
            return

        image_id = items[0].data(Qt.ItemDataRole.UserRole)
        image_name = items[0].text().split('  (')[0]

        reply = QMessageBox.question(
            self, "이미지 삭제",
            f"'{image_name}' 이미지를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_alert_image(image_id)
            self._load_image_list()

    def _on_test_toast(self):
        """토스트 테스트 - 선택된 이미지 사용"""
        try:
            from windows_toasts import Toast, InteractableWindowsToaster, ToastDisplayImage, ToastImagePosition, ToastDuration, ToastAudio

            toaster = InteractableWindowsToaster(
                applicationText="Activity Tracker",
                notifierAUMID="ActivityTracker"
            )
            toast = Toast()
            toast.text_fields = ['테스트 알림입니다!']
            toast.duration = ToastDuration.Short
            toast.audio = ToastAudio(silent=True)

            # 이미지 추가 (선택된 이미지 또는 첫 번째 이미지)
            if self.image_checkbox.isChecked():
                image_path = None

                # 선택된 이미지 확인
                items = self.image_list.selectedItems()
                if items:
                    image_id = items[0].data(Qt.ItemDataRole.UserRole)
                    image = self.db_manager.get_alert_image_by_id(image_id)
                    if image:
                        image_path = image['file_path']

                # 선택 안됐으면 첫 번째 이미지 사용
                if not image_path:
                    images = self.db_manager.get_all_alert_images()
                    if images:
                        image_path = images[0]['file_path']

                if image_path and Path(image_path).exists():
                    toast.AddImage(ToastDisplayImage.fromPath(image_path, position=ToastImagePosition.Hero))
                    print(f"[NotificationTab] 테스트 이미지: {image_path}")

            toaster.show_toast(toast)
            print("[NotificationTab] 테스트 토스트 전송")

        except ImportError:
            QMessageBox.warning(
                self, "라이브러리 필요",
                "windows-toasts 라이브러리가 필요합니다.\npip install windows-toasts"
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"토스트 표시 실패:\n{e}")
