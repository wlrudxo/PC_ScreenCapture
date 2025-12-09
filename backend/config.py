"""
애플리케이션 설정 및 경로 관리
"""
import os
import sys
from pathlib import Path


class AppConfig:
    """
    애플리케이션 설정 및 경로 관리

    개발 모드 vs 빌드 모드 자동 구분:
    - 개발 중: 프로젝트 폴더에 DB/설정 저장 (디버깅 편함)
    - 빌드 후: AppData에 저장 (Windows 표준)
    """

    @staticmethod
    def is_dev_mode():
        """
        개발 모드 체크
        PyInstaller로 빌드되면 sys.frozen = True
        """
        return not getattr(sys, 'frozen', False)

    @staticmethod
    def get_app_dir():
        """
        애플리케이션 데이터 디렉토리

        개발 모드:
            H:\\GitProject\\PC_ScreenCapture_V2\\

        빌드 모드:
            C:\\Users\\User\\AppData\\Roaming\\ActivityTracker\\
        """
        if AppConfig.is_dev_mode():
            # 개발 중: 프로젝트 폴더
            return Path(__file__).parent.parent
        else:
            # 빌드 후: AppData
            if os.name == 'nt':  # Windows
                app_dir = Path(os.getenv('APPDATA')) / "ActivityTracker"
            else:  # macOS, Linux
                app_dir = Path.home() / ".activitytracker"

            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir

    @staticmethod
    def get_db_path():
        """SQLite DB 파일 경로"""
        return AppConfig.get_app_dir() / "activity_tracker.db"

    @staticmethod
    def get_config_path():
        """설정 파일 경로 (JSON)"""
        return AppConfig.get_app_dir() / "config.json"

    @staticmethod
    def get_log_dir():
        """로그 디렉토리"""
        log_dir = AppConfig.get_app_dir() / "logs"
        log_dir.mkdir(exist_ok=True)
        return log_dir

    @staticmethod
    def get_log_path():
        """로그 파일 경로"""
        return AppConfig.get_log_dir() / "app.log"

    @staticmethod
    def get_sounds_dir():
        """알림음 저장 디렉토리"""
        sounds_dir = AppConfig.get_app_dir() / "sounds"
        sounds_dir.mkdir(exist_ok=True)
        return sounds_dir
