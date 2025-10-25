"""
화면 캡처 모듈
mss를 사용하여 멀티모니터 스크린샷을 주기적으로 캡처합니다.
"""

import ctypes
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import os

import mss
from PIL import Image
import numpy as np

from database import Database
from utils import ensure_config_exists, get_config_path, resolve_data_path


def is_screen_locked() -> bool:
    """
    Windows 화면 잠금 상태 확인

    Returns:
        True: 화면이 잠겨있음
        False: 화면이 잠금 해제됨
    """
    try:
        user32 = ctypes.windll.User32

        # DESKTOP_SWITCHDESKTOP 권한으로 데스크톱 핸들 획득
        DESKTOP_SWITCHDESKTOP = 0x0100
        hDesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)

        if not hDesk:
            # 핸들을 못 얻었다면 잠금 상태일 가능성이 높음
            return True

        # SwitchDesktop 시도 - 잠금 상태면 실패
        can_switch = user32.SwitchDesktop(hDesk)
        user32.CloseDesktop(hDesk)

        # SwitchDesktop 실패 = 잠금 상태
        return not can_switch

    except Exception as e:
        # 에러 발생 시 잠금 상태로 간주 (안전)
        print(f"[Warning] 잠금 상태 확인 실패 (잠금으로 간주): {e}")
        return True


def is_black_screen(img: Image.Image, threshold: float = 10.0) -> bool:
    """
    이미지가 검정색 화면인지 확인 (잠금 화면 감지용)

    Args:
        img: PIL Image 객체
        threshold: 평균 밝기 임계값 (0~255, 기본값 10.0)
                  이 값보다 낮으면 검정색 화면으로 간주

    Returns:
        True: 검정색 화면 (잠금 화면일 가능성 높음)
        False: 정상 화면
    """
    try:
        # 이미지를 그레이스케일로 변환하여 평균 밝기 계산
        grayscale = img.convert('L')
        pixels = np.array(grayscale)
        mean_brightness = pixels.mean()

        is_black = mean_brightness < threshold

        if is_black:
            print(f"[Black Screen Detected] 평균 밝기: {mean_brightness:.2f} < {threshold}")

        return is_black

    except Exception as e:
        print(f"[Warning] 검정색 화면 감지 실패: {e}")
        return False


class ScreenCapture:
    def __init__(self, config_path: str = None):
        """
        화면 캡처 초기화

        Args:
            config_path: 설정 파일 경로 (None이면 자동으로 찾음)
        """
        # 설정 파일 경로 확인 및 생성
        if config_path is None:
            ensure_config_exists()
            config_path = get_config_path()

        # 설정 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # 경로 해석 (상대 경로 → 절대 경로)
        db_path = resolve_data_path(self.config['storage']['database_path'])
        screenshots_path = resolve_data_path(self.config['storage']['screenshots_dir'])

        # 데이터베이스 초기화
        self.db = Database(str(db_path))

        # 카테고리 초기화
        self.db.init_categories(self.config['categories'])

        # 스크린샷 디렉토리
        self.screenshots_dir = screenshots_path
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # 캡처 설정
        self.interval_minutes = self.config['capture']['interval_minutes']
        self.image_quality = self.config['capture']['image_quality']
        self.image_format = self.config['capture']['format']

        # 캡처 상태
        self.is_running = False
        self.is_paused = False
        self.scheduled_stop = None  # "HH:MM" 형식

        print(f"[ScreenCapture] 초기화 완료")
        print(f"  - 캡처 간격: {self.interval_minutes}분")
        print(f"  - 이미지 품질: {self.image_quality}")
        print(f"  - 저장 경로: {self.screenshots_dir}")

    def capture_all_monitors(self) -> List[Dict]:
        """
        모든 모니터 캡처

        Returns:
            캡처된 이미지 정보 리스트 [{"monitor_num": 1, "filepath": "..."}]
        """
        # 화면 잠금 상태 확인 (1차 방어)
        if is_screen_locked():
            print("[Capture] 화면 잠금 상태 - 캡처 건너뜀")
            return []

        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H-%M-%S")

        # 날짜별 폴더 생성
        date_dir = self.screenshots_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # 1단계: 먼저 모든 모니터를 캡처하고 검정색 화면 체크
        captured_images = []  # (monitor_num, img) 튜플 저장

        with mss.mss() as sct:
            # 모니터 개수 확인 (0번은 모든 모니터를 포함하는 가상 모니터)
            num_monitors = len(sct.monitors) - 1

            for i in range(1, num_monitors + 1):
                # 스크린샷 캡처
                monitor = sct.monitors[i]
                screenshot = sct.grab(monitor)

                # PIL Image로 변환
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                # 검정색 화면 감지 (2차 방어 - 잠금 화면 감지)
                if is_black_screen(img):
                    print(f"[Capture] Monitor {i}: 검정색 화면 감지 - 잠금 상태로 판단")
                    print("[Capture] 하나 이상의 모니터가 잠금 상태이므로 전체 캡처 건너뜀")
                    return []  # 하나라도 검정색이면 전체 캡처 중단

                # 정상 화면이면 임시 저장
                captured_images.append((i, img))

        # 2단계: 모든 모니터가 정상이면 파일로 저장
        captured_files = []

        for monitor_num, img in captured_images:
            # 파일명 생성
            filename = f"{time_str}_m{monitor_num}.jpg"
            filepath = date_dir / filename

            # JPEG로 저장 (압축)
            img.save(filepath, self.image_format, quality=self.image_quality, optimize=True)

            # 데이터베이스에 기록
            self.db.add_capture(timestamp, monitor_num, str(filepath))

            captured_files.append({
                "monitor_num": monitor_num,
                "filepath": str(filepath)
            })

            print(f"[Capture] Monitor {monitor_num}: {filepath}")

        return captured_files

    def start_capture_loop(self):
        """
        캡처 루프 시작 (블로킹)
        주기적으로 화면을 캡처합니다.
        """
        self.is_running = True
        print(f"[ScreenCapture] 캡처 시작 (간격: {self.interval_minutes}분)")

        while self.is_running:
            # 예약 종료 확인
            if self.scheduled_stop:
                now = datetime.now().strftime("%H:%M")
                if now == self.scheduled_stop:
                    print(f"[ScreenCapture] 예약된 시간({self.scheduled_stop})에 도달하여 자동 종료합니다.")
                    self.stop_capture()
                    break

            if not self.is_paused:
                try:
                    self.capture_all_monitors()
                except Exception as e:
                    print(f"[Error] 캡처 실패: {e}")

            # 다음 캡처까지 대기
            # 1초 단위로 체크하면서 중단 가능하도록
            for _ in range(self.interval_minutes * 60):
                if not self.is_running:
                    break
                time.sleep(1)

    def stop_capture(self):
        """캡처 중지"""
        self.is_running = False
        print("[ScreenCapture] 캡처 중지")

    def pause_capture(self):
        """캡처 일시정지"""
        self.is_paused = True
        print("[ScreenCapture] 캡처 일시정지")

    def resume_capture(self):
        """캡처 재개"""
        self.is_paused = False
        print("[ScreenCapture] 캡처 재개")


def main():
    """
    단독 실행 시 메인 함수
    """
    capture = ScreenCapture()

    try:
        # 즉시 한 번 캡처
        print("[Test] 테스트 캡처 시작...")
        capture.capture_all_monitors()
        print("[Test] 테스트 캡처 완료!")

        # 주기적 캡처 시작 (Ctrl+C로 중단)
        print(f"\n[Info] {capture.interval_minutes}분마다 자동 캡처를 시작합니다.")
        print("[Info] Ctrl+C를 눌러 중단할 수 있습니다.\n")

        capture.start_capture_loop()

    except KeyboardInterrupt:
        print("\n\n[Info] 사용자에 의해 중단되었습니다.")
        capture.stop_capture()


if __name__ == "__main__":
    main()
