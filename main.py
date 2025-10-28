"""
활동 추적 시스템 V2 - 메인 진입점
"""
import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import apply_dark_theme


def main():
    """메인 함수"""
    print("=" * 70)
    print("활동 추적 시스템 V2 시작")
    print("=" * 70)

    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)

    # 다크 테마 적용
    apply_dark_theme(app)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()

    # 이벤트 루프 실행
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
