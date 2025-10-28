"""
화면 잠금 감지 테스트
Win+L 눌러서 잠그고, 풀어서 테스트
"""

import ctypes
import time
from ctypes import Structure, windll, byref, sizeof

class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('dwTime', ctypes.c_uint),
    ]

def get_idle_duration():
    """마지막 키보드/마우스 입력 이후 경과 시간(초)"""
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

def is_screen_locked():
    """화면 잠금 상태 확인"""
    hDesktop = windll.user32.OpenInputDesktop(0, False, 0)
    if hDesktop == 0:
        return True  # 잠금 상태
    windll.user32.CloseDesktop(hDesktop)
    return False

def main():
    print("=" * 70)
    print("🔒 화면 잠금 감지 테스트")
    print("=" * 70)
    print()
    print("📌 Win+L을 눌러서 화면을 잠그고, 다시 로그인해보세요.")
    print("   마우스를 안 움직이면 idle 시간도 증가하는지 확인하세요.")
    print()
    print("종료: Ctrl+C")
    print("=" * 70)
    print()

    last_locked = None

    try:
        while True:
            locked = is_screen_locked()
            idle = get_idle_duration()

            # 상태 변화 감지 시 알림
            if locked != last_locked:
                if locked:
                    print(f"\n[{time.strftime('%H:%M:%S')}] 🔒 화면 잠금 감지!")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔓 화면 잠금 해제!")
                last_locked = locked

            # 실시간 상태 표시
            if locked:
                status = "🔒 잠금 상태"
            else:
                if idle > 10:
                    status = f"🟡 활성 (idle: {idle:.1f}초)"
                else:
                    status = f"🟢 활성 (idle: {idle:.1f}초)"

            print(f"\r[{time.strftime('%H:%M:%S')}] {status}    ", end='', flush=True)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n테스트 종료!")

if __name__ == "__main__":
    main()
