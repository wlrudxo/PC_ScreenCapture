"""
Activity Tracker - 메인 진입점
"""
import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import apply_dark_theme


def main():
    """메인 함수"""
    print("=" * 70)
    print("Activity Tracker 시작")
    print("=" * 70)

    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)

    # 다크 테마 적용
    apply_dark_theme(app)

    # 메인 윈도우 생성 및 표시
    try:
        window = MainWindow()
        window.show()
    except Exception as e:
        print(f"[main] 초기화 실패: {e}")
        # QMessageBox는 MainWindow 생성 전에 이미 표시됨
        # 여기서는 종료만 처리
        sys.exit(1)

    # 이벤트 루프 실행
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
