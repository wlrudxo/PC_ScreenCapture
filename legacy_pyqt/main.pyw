"""
Activity Tracker - 프로덕션 진입점 (터미널 없이 실행)
"""
import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import apply_dark_theme


def main():
    """메인 함수"""
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)

    # 다크 테마 적용
    apply_dark_theme(app)

    # 메인 윈도우 생성 및 표시
    try:
        window = MainWindow()
        window.show()
    except Exception as e:
        # 프로덕션 모드: 콘솔 출력 제거
        sys.exit(1)

    # 이벤트 루프 실행
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
