"""
활성 창 감지 테스트 스크립트
현재 활성화된 창의 정보를 실시간으로 출력
"""

import time
import psutil
import ctypes
from ctypes import windll, create_unicode_buffer, wintypes, byref

def get_active_window_info():
    """현재 활성화된 창의 상세 정보 가져오기"""

    # 활성 창 핸들 가져오기
    hwnd = windll.user32.GetForegroundWindow()

    # 창 제목 가져오기
    length = windll.user32.GetWindowTextLengthW(hwnd)
    buffer = create_unicode_buffer(length + 1)
    windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    window_title = buffer.value

    # 프로세스 ID 가져오기
    pid = wintypes.DWORD()
    windll.user32.GetWindowThreadProcessId(hwnd, byref(pid))

    try:
        # 프로세스 정보 가져오기
        process = psutil.Process(pid.value)
        process_name = process.name()
        process_path = process.exe()

        # Chrome 프로필 감지
        chrome_profile = None
        chrome_url = None
        chrome_cmdline_debug = None

        if 'chrome.exe' in process_name.lower():
            try:
                cmdline = process.cmdline()
                chrome_cmdline_debug = cmdline  # 디버깅용

                # 프로필 추출
                for arg in cmdline:
                    if '--profile-directory=' in arg:
                        chrome_profile = arg.split('=')[1]
                        break

                # 프로필이 없으면 부모 프로세스 확인
                if not chrome_profile:
                    try:
                        parent = process.parent()
                        if parent and 'chrome.exe' in parent.name().lower():
                            parent_cmdline = parent.cmdline()
                            for arg in parent_cmdline:
                                if '--profile-directory=' in arg:
                                    chrome_profile = arg.split('=')[1]
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if not chrome_profile:
                    chrome_profile = "Default"
            except Exception as e:
                chrome_profile = f"Error: {e}"

        return {
            'window_title': window_title,
            'process_name': process_name,
            'process_path': process_path,
            'pid': pid.value,
            'chrome_profile': chrome_profile,
            'chrome_cmdline_debug': chrome_cmdline_debug,
        }

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def main():
    """메인 루프: 2초마다 활성 창 정보 출력"""
    print("=" * 80)
    print("활성 창 추적 시작!")
    print("다양한 프로그램/Chrome 프로필을 전환하면서 테스트해보세요.")
    print("종료: Ctrl+C")
    print("=" * 80)
    print()

    last_info = None

    try:
        while True:
            current_info = get_active_window_info()

            # 창이 바뀌었을 때만 출력
            if current_info and current_info != last_info:
                print(f"\n[{time.strftime('%H:%M:%S')}] 활성 창 변경 감지!")
                print(f"  📝 창 제목: {current_info['window_title']}")
                print(f"  💻 프로그램: {current_info['process_name']}")
                print(f"  📂 경로: {current_info['process_path']}")
                print(f"  🆔 PID: {current_info['pid']}")

                if current_info['chrome_profile']:
                    print(f"  🌐 Chrome 프로필: {current_info['chrome_profile']}")

                # Chrome 디버깅 정보
                if current_info['chrome_cmdline_debug']:
                    print(f"\n  [디버깅] Chrome 커맨드라인:")
                    for i, arg in enumerate(current_info['chrome_cmdline_debug'][:10]):  # 처음 10개만
                        print(f"    [{i}] {arg}")
                    if len(current_info['chrome_cmdline_debug']) > 10:
                        print(f"    ... (총 {len(current_info['chrome_cmdline_debug'])}개 인자)")

                print("-" * 80)

                last_info = current_info

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n추적 종료!")

if __name__ == "__main__":
    main()
