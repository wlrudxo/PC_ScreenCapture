"""
유틸리티 함수 모음
"""

import os
import sys
import json
import shutil
from pathlib import Path


def get_app_data_dir():
    """
    애플리케이션 데이터 디렉토리 경로 반환

    개발 모드: 프로젝트 루트 디렉토리 사용 (기존 방식)
    배포 모드 (exe): AppData/Roaming/ScreenCapture 사용

    Returns:
        Path: 애플리케이션 데이터 디렉토리 경로
    """
    # exe로 패키징되었는지 확인
    if getattr(sys, 'frozen', False):
        # 배포 모드: AppData/Roaming 사용
        appdata = os.getenv('APPDATA')
        if not appdata:
            raise RuntimeError("APPDATA 환경 변수를 찾을 수 없습니다.")
        app_dir = Path(appdata) / 'ScreenCapture'
    else:
        # 개발 모드: 프로젝트 루트 디렉토리 사용
        app_dir = Path(__file__).parent

    # 디렉토리 생성
    app_dir.mkdir(parents=True, exist_ok=True)

    return app_dir


def get_config_path():
    """
    config.json 파일 경로 반환

    Returns:
        Path: config.json 경로
    """
    return get_app_data_dir() / 'config.json'


def ensure_config_exists():
    """
    config.json 파일이 없으면 기본값으로 생성

    Returns:
        Path: config.json 경로
    """
    config_path = get_config_path()

    if not config_path.exists():
        # 개발 모드에서 원본 config.json 찾기
        if getattr(sys, 'frozen', False):
            # exe 모드: 내장된 기본 설정 사용
            default_config = {
                "capture": {
                    "interval_minutes": 3,
                    "image_quality": 50,
                    "format": "JPEG"
                },
                "storage": {
                    "screenshots_dir": "./data/screenshots",
                    "database_path": "./data/activity.db",
                    "auto_delete_after_tagging": True
                },
                "viewer": {
                    "port": 5000,
                    "thumbnail_size": [320, 180]
                },
                "categories": [
                    {
                        "name": "연구",
                        "color": "#4CAF50",
                        "activities": ["코딩", "자료 조사", "논문 작성", "PPT 제작", "공부"]
                    },
                    {
                        "name": "행정",
                        "color": "#2196F3",
                        "activities": ["메일", "서류 작성", "영수증 처리"]
                    },
                    {
                        "name": "개인",
                        "color": "#FF9800",
                        "activities": ["언어 공부", "앱 개발", "인터넷", "유튜브"]
                    },
                    {
                        "name": "기타",
                        "color": "#9E9E9E",
                        "activities": ["자리 비움"]
                    }
                ]
            }
        else:
            # 개발 모드: 원본 config.json이 있으면 복사
            source_config = Path(__file__).parent / 'config.json'
            if source_config.exists():
                shutil.copy(source_config, config_path)
                print(f"[Config] 설정 파일 생성: {config_path}")
                return config_path
            else:
                # 원본도 없으면 기본값 사용
                default_config = {
                    "capture": {
                        "interval_minutes": 3,
                        "image_quality": 50,
                        "format": "JPEG"
                    },
                    "storage": {
                        "screenshots_dir": "./data/screenshots",
                        "database_path": "./data/activity.db",
                        "auto_delete_after_tagging": True
                    },
                    "viewer": {
                        "port": 5000,
                        "thumbnail_size": [320, 180]
                    },
                    "categories": [
                        {
                            "name": "연구",
                            "color": "#4CAF50",
                            "activities": ["코딩", "자료 조사", "논문 작성", "PPT 제작", "공부"]
                        },
                        {
                            "name": "행정",
                            "color": "#2196F3",
                            "activities": ["메일", "서류 작성", "영수증 처리"]
                        },
                        {
                            "name": "개인",
                            "color": "#FF9800",
                            "activities": ["언어 공부", "앱 개발", "인터넷", "유튜브"]
                        },
                        {
                            "name": "기타",
                            "color": "#9E9E9E",
                            "activities": ["자리 비움"]
                        }
                    ]
                }

        # 기본 설정 파일 생성
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        print(f"[Config] 기본 설정 파일 생성: {config_path}")

    return config_path


def resolve_data_path(relative_path):
    """
    상대 경로를 절대 경로로 변환

    config.json의 경로(./data/screenshots 등)를 AppData 기준으로 변환

    Args:
        relative_path (str): 상대 경로 (예: "./data/screenshots")

    Returns:
        Path: 절대 경로
    """
    app_dir = get_app_data_dir()

    # ./ 제거
    if relative_path.startswith('./'):
        relative_path = relative_path[2:]
    elif relative_path.startswith('.\\'):
        relative_path = relative_path[2:]

    return app_dir / relative_path
