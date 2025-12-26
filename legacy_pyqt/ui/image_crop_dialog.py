"""
이미지 크롭 다이얼로그 - 토스트 Hero 이미지용 (2:1 비율)
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from pathlib import Path


class ImageCropDialog(QDialog):
    """
    이미지 크롭 다이얼로그

    - 2:1 비율 (364x180) 영역 선택
    - 드래그로 영역 이동
    - 확인 시 크롭된 이미지 저장
    """

    # Hero 이미지 비율 (가로:세로 = 2:1)
    CROP_RATIO = 2.0
    TARGET_WIDTH = 364
    TARGET_HEIGHT = 180

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)

        self.image_path = image_path
        self.original_pixmap = QPixmap(image_path)
        self.cropped_image: QImage = None

        self.setWindowTitle("이미지 영역 선택")
        self.setModal(True)

        self._setup_ui()
        self._init_crop_area()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 안내 문구
        hint = QLabel("드래그하여 영역을 이동하세요. 2:1 비율로 크롭됩니다.")
        hint.setStyleSheet("color: #666; font-size: 10pt;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # 이미지 영역
        self.crop_widget = CropWidget(self.original_pixmap)
        self.crop_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.crop_widget, 1)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("확인")
        confirm_btn.clicked.connect(self._on_confirm)
        confirm_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 창 크기 설정 (이미지 크기에 맞게)
        self._set_dialog_size()

    def _set_dialog_size(self):
        """다이얼로그 크기 설정"""
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()

        # 최대 크기 제한
        max_w, max_h = 800, 600

        if img_w > max_w or img_h > max_h:
            scale = min(max_w / img_w, max_h / img_h)
            img_w = int(img_w * scale)
            img_h = int(img_h * scale)

        # 여백 추가
        self.resize(img_w + 40, img_h + 100)

    def _init_crop_area(self):
        """초기 크롭 영역 설정"""
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()

        # 2:1 비율로 최대 크기 계산
        if img_w / img_h > self.CROP_RATIO:
            # 이미지가 더 넓음 -> 높이에 맞춤
            crop_h = img_h
            crop_w = int(crop_h * self.CROP_RATIO)
        else:
            # 이미지가 더 높음 -> 너비에 맞춤
            crop_w = img_w
            crop_h = int(crop_w / self.CROP_RATIO)

        # 중앙에 배치
        x = (img_w - crop_w) // 2
        y = (img_h - crop_h) // 2

        self.crop_widget.set_crop_rect(QRect(x, y, crop_w, crop_h))

    def _on_confirm(self):
        """확인 버튼 클릭"""
        crop_rect = self.crop_widget.get_crop_rect()

        # 원본 이미지에서 크롭
        cropped = self.original_pixmap.copy(crop_rect)

        # 타겟 크기로 리사이즈
        scaled = cropped.scaled(
            self.TARGET_WIDTH, self.TARGET_HEIGHT,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.cropped_image = scaled.toImage()
        self.accept()

    def get_cropped_image(self) -> QImage:
        """크롭된 이미지 반환"""
        return self.cropped_image


class CropWidget(QWidget):
    """
    크롭 영역을 표시하고 드래그할 수 있는 위젯
    """

    CROP_RATIO = 2.0  # 2:1 비율

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)

        self.original_pixmap = pixmap
        self.display_pixmap = None
        self.scale_factor = 1.0

        # 크롭 영역 (원본 이미지 좌표)
        self.crop_rect = QRect(0, 0, 100, 50)

        # 드래그 상태
        self.dragging = False
        self.drag_start = QPoint()
        self.rect_start = QRect()

        self.setMouseTracking(True)
        self.setMinimumSize(200, 100)

    def set_crop_rect(self, rect: QRect):
        """크롭 영역 설정 (원본 좌표)"""
        self.crop_rect = rect
        self.update()

    def get_crop_rect(self) -> QRect:
        """크롭 영역 반환 (원본 좌표)"""
        return self.crop_rect

    def resizeEvent(self, event):
        """위젯 크기 변경 시 이미지 스케일 조정"""
        super().resizeEvent(event)
        self._update_display_pixmap()

    def _update_display_pixmap(self):
        """표시용 이미지 업데이트"""
        if self.original_pixmap.isNull():
            return

        # 위젯 크기에 맞게 스케일
        self.display_pixmap = self.original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 스케일 팩터 계산
        self.scale_factor = self.display_pixmap.width() / self.original_pixmap.width()
        self.update()

    def _to_display_coords(self, rect: QRect) -> QRect:
        """원본 좌표 -> 화면 좌표"""
        offset_x = (self.width() - self.display_pixmap.width()) // 2
        offset_y = (self.height() - self.display_pixmap.height()) // 2

        return QRect(
            int(rect.x() * self.scale_factor) + offset_x,
            int(rect.y() * self.scale_factor) + offset_y,
            int(rect.width() * self.scale_factor),
            int(rect.height() * self.scale_factor)
        )

    def _to_original_coords(self, point: QPoint) -> QPoint:
        """화면 좌표 -> 원본 좌표"""
        offset_x = (self.width() - self.display_pixmap.width()) // 2
        offset_y = (self.height() - self.display_pixmap.height()) // 2

        return QPoint(
            int((point.x() - offset_x) / self.scale_factor),
            int((point.y() - offset_y) / self.scale_factor)
        )

    def paintEvent(self, event):
        """그리기"""
        if self.display_pixmap is None:
            self._update_display_pixmap()
            if self.display_pixmap is None:
                return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 이미지 중앙에 그리기
        offset_x = (self.width() - self.display_pixmap.width()) // 2
        offset_y = (self.height() - self.display_pixmap.height()) // 2
        painter.drawPixmap(offset_x, offset_y, self.display_pixmap)

        # 어두운 오버레이 (크롭 영역 외부)
        display_rect = self._to_display_coords(self.crop_rect)

        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(offset_x, offset_y,
                        self.display_pixmap.width(), display_rect.y() - offset_y,
                        overlay_color)  # 상단
        painter.fillRect(offset_x, display_rect.bottom() + 1,
                        self.display_pixmap.width(),
                        offset_y + self.display_pixmap.height() - display_rect.bottom() - 1,
                        overlay_color)  # 하단
        painter.fillRect(offset_x, display_rect.y(),
                        display_rect.x() - offset_x, display_rect.height(),
                        overlay_color)  # 좌측
        painter.fillRect(display_rect.right() + 1, display_rect.y(),
                        offset_x + self.display_pixmap.width() - display_rect.right() - 1,
                        display_rect.height(),
                        overlay_color)  # 우측

        # 크롭 영역 테두리
        pen = QPen(QColor(255, 255, 255), 2)
        painter.setPen(pen)
        painter.drawRect(display_rect)

        # 가이드라인 (3등분)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        painter.setPen(pen)

        third_w = display_rect.width() // 3
        third_h = display_rect.height() // 3

        painter.drawLine(display_rect.x() + third_w, display_rect.y(),
                        display_rect.x() + third_w, display_rect.bottom())
        painter.drawLine(display_rect.x() + third_w * 2, display_rect.y(),
                        display_rect.x() + third_w * 2, display_rect.bottom())
        painter.drawLine(display_rect.x(), display_rect.y() + third_h,
                        display_rect.right(), display_rect.y() + third_h)
        painter.drawLine(display_rect.x(), display_rect.y() + third_h * 2,
                        display_rect.right(), display_rect.y() + third_h * 2)

    def mousePressEvent(self, event):
        """마우스 클릭"""
        if event.button() == Qt.MouseButton.LeftButton:
            display_rect = self._to_display_coords(self.crop_rect)
            if display_rect.contains(event.pos()):
                self.dragging = True
                self.drag_start = event.pos()
                self.rect_start = QRect(self.crop_rect)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """마우스 이동"""
        display_rect = self._to_display_coords(self.crop_rect)

        if self.dragging:
            # 드래그로 영역 이동
            delta = event.pos() - self.drag_start
            delta_original = QPoint(
                int(delta.x() / self.scale_factor),
                int(delta.y() / self.scale_factor)
            )

            new_x = self.rect_start.x() + delta_original.x()
            new_y = self.rect_start.y() + delta_original.y()

            # 경계 체크
            max_x = self.original_pixmap.width() - self.crop_rect.width()
            max_y = self.original_pixmap.height() - self.crop_rect.height()

            new_x = max(0, min(new_x, max_x))
            new_y = max(0, min(new_y, max_y))

            self.crop_rect.moveTo(new_x, new_y)
            self.update()
        else:
            # 커서 변경
            if display_rect.contains(event.pos()):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """마우스 릴리즈"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            display_rect = self._to_display_coords(self.crop_rect)
            if display_rect.contains(event.pos()):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
