"""
통합 실행 스크립트
캡처 프로그램과 Flask 뷰어를 동시에 실행하고, 시스템 트레이 아이콘을 제공합니다.
"""

import json
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from capture import ScreenCapture
from viewer import app, config


# 전역 변수
capture_instance = None
tray_icon = None


def create_tray_icon():
    """
    시스템 트레이 아이콘 생성
    """
    # 간단한 아이콘 이미지 생성 (초록색 원)
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, width-8, height-8), fill='#4CAF50', outline='#2E7D32')

    return image


def open_viewer():
    """브라우저에서 뷰어 열기"""
    port = config['viewer']['port']
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    print(f"[Tray] 브라우저 열기: {url}")


def toggle_pause():
    """캡처 일시정지/재개"""
    global capture_instance
    if capture_instance:
        if capture_instance.is_paused:
            capture_instance.resume_capture()
        else:
            capture_instance.pause_capture()


def quit_app(icon, item):
    """프로그램 종료"""
    global capture_instance, tray_icon

    print("\n[Quit] 프로그램 종료 중...")

    # 캡처 중지
    if capture_instance:
        capture_instance.stop_capture()

    # 트레이 아이콘 종료
    if tray_icon:
        icon.stop()

    print("[Quit] 종료 완료")


def setup_tray():
    """
    시스템 트레이 설정
    """
    global tray_icon

    # 메뉴 항목
    menu = pystray.Menu(
        pystray.MenuItem("뷰어 열기", lambda: open_viewer()),
        pystray.MenuItem("일시정지/재개", lambda: toggle_pause()),
        pystray.MenuItem("종료", quit_app)
    )

    # 트레이 아이콘 생성
    icon_image = create_tray_icon()
    tray_icon = pystray.Icon("ScreenCapture", icon_image, "ScreenCapture", menu)

    return tray_icon


def run_capture_thread(capture_instance):
    """
    캡처 스레드 실행
    """
    print("[Thread] 캡처 스레드 시작")

    # 캡처 루프 시작 (블로킹)
    capture_instance.start_capture_loop()


def run_flask_thread(capture_instance):
    """
    Flask 스레드 실행
    """
    print("[Thread] Flask 스레드 시작")
    port = config['viewer']['port']

    # 캡처 인스턴스를 Flask app에 등록
    app.config['capture_instance'] = capture_instance
    app.config['scheduled_stop'] = None

    # Flask 실행 (블로킹)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def check_scheduled_stop():
    """
    예약 종료 체크 스레드
    """
    global capture_instance
    import time

    while True:
        time.sleep(30)  # 30초마다 체크

        if not capture_instance or not capture_instance.is_running:
            continue

        # Flask app에서 예약 종료 시간 가져오기
        scheduled_stop = app.config.get('scheduled_stop')
        if scheduled_stop:
            capture_instance.scheduled_stop = scheduled_stop


def main():
    """
    메인 함수 - 통합 실행
    """
    global capture_instance

    print("=" * 60)
    print("  ScreenCapture - 개인 활동 기록 및 분석 도구")
    print("=" * 60)
    print()

    # 1. 캡처 인스턴스 생성 (메인 스레드에서)
    print("[Init] 캡처 인스턴스 생성 중...")
    capture_instance = ScreenCapture()
    print("[Init] 캡처 인스턴스 생성 완료")

    # 2. 캡처 스레드 시작
    capture_thread = threading.Thread(target=run_capture_thread, args=(capture_instance,), daemon=True)
    capture_thread.start()

    # 3. Flask 스레드 시작
    flask_thread = threading.Thread(target=run_flask_thread, args=(capture_instance,), daemon=True)
    flask_thread.start()

    # 4. 예약 종료 체크 스레드
    scheduled_thread = threading.Thread(target=check_scheduled_stop, daemon=True)
    scheduled_thread.start()

    # 5. 자동으로 브라우저 열기 (2초 후)
    def delayed_open():
        import time
        time.sleep(2)
        open_viewer()

    browser_thread = threading.Thread(target=delayed_open, daemon=True)
    browser_thread.start()

    # 6. 시스템 트레이 실행 (메인 스레드)
    print("\n[Info] 시스템 트레이 아이콘이 생성되었습니다.")
    print("[Info] 트레이 아이콘을 우클릭하여 메뉴를 사용하세요.")
    print("[Info] '종료' 메뉴를 선택하여 프로그램을 종료할 수 있습니다.\n")

    try:
        tray = setup_tray()
        tray.run()  # 블로킹
    except KeyboardInterrupt:
        print("\n[Info] Ctrl+C로 중단되었습니다.")
        quit_app(None, None)


if __name__ == "__main__":
    main()
