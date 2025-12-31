#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Activity Tracker 릴리즈 빌드 스크립트

사용법:
    python build_release.py 1.0.3
    python build_release.py 1.0.3 --force  # 강제 리빌드
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from glob import glob

# Windows cp949 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# PyInstaller가 설치된 Python 3.12 경로 (py launcher 사용)
PYTHON_312 = None

# === 설정 ===
PROJECT_DIR = Path(__file__).parent
DIST_DIR = PROJECT_DIR / "dist"
APP_DIR = DIST_DIR / "ActivityTracker"
EXE_PATH = APP_DIR / "ActivityTracker.exe"
RELEASE_ASSETS_DIR = PROJECT_DIR / "release_assets"
SPEC_FILE = PROJECT_DIR / "ActivityTracker.spec"

# 빌드 체크할 소스 패턴들
SOURCE_PATTERNS = [
    "*.py",
    "*.pyw",
    "*.spec",
    "backend/**/*.py",
    "webui/dist/**/*",
    "resources/*",
]


def get_latest_source_mtime() -> float:
    """소스 파일들 중 가장 최근 수정 시간 반환"""
    latest = 0.0
    for pattern in SOURCE_PATTERNS:
        for path in glob(str(PROJECT_DIR / pattern), recursive=True):
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)
                if mtime > latest:
                    latest = mtime
    return latest


def need_rebuild() -> bool:
    """리빌드 필요 여부 확인"""
    if not EXE_PATH.exists():
        return True

    exe_mtime = os.path.getmtime(EXE_PATH)
    source_mtime = get_latest_source_mtime()

    return source_mtime > exe_mtime


def get_python_312() -> str:
    """PyInstaller가 설치된 Python 3.12 경로 찾기"""
    global PYTHON_312
    if PYTHON_312:
        return PYTHON_312

    # py launcher로 3.12 경로 확인
    try:
        result = subprocess.run(
            ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
            capture_output=True, text=True, check=True
        )
        PYTHON_312 = result.stdout.strip()
        return PYTHON_312
    except subprocess.CalledProcessError:
        print("  ❌ Python 3.12 not found! Install it or check 'py --list'")
        sys.exit(1)


def run_pyinstaller():
    """PyInstaller 빌드 실행 (Python 3.12 사용)"""
    python = get_python_312()
    cmd = [python, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"]
    print(f"  Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("  ❌ PyInstaller failed!")
        sys.exit(1)


def create_release_zip(version: str) -> Path:
    """최종 릴리즈 zip 생성"""
    release_name = f"ActivityTracker-v{version}"
    release_zip = DIST_DIR / f"{release_name}.zip"

    # 기존 파일 삭제
    if release_zip.exists():
        release_zip.unlink()

    chrome_ext_dir = RELEASE_ASSETS_DIR / "chrome_extension"
    if not chrome_ext_dir.exists():
        print(f"  ❌ chrome_extension not found: {chrome_ext_dir}")
        sys.exit(1)

    with zipfile.ZipFile(release_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. ActivityTracker 폴더 전체 추가
        for file in APP_DIR.rglob("*"):
            if file.is_file():
                arcname = Path(release_name) / file.relative_to(APP_DIR)
                zf.write(file, arcname)

        # 2. chrome_extension 폴더 그대로 추가 (압축 없이)
        for file in chrome_ext_dir.rglob("*"):
            if file.is_file():
                arcname = Path(release_name) / "chrome_extension" / file.relative_to(chrome_ext_dir)
                zf.write(file, arcname)

        # 3. README.txt 추가
        readme = RELEASE_ASSETS_DIR / "README.txt"
        if readme.exists():
            zf.write(readme, Path(release_name) / "README.txt")

    return release_zip


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_release.py <version> [--force]")
        print("Example: python build_release.py 1.0.3")
        sys.exit(1)

    version = sys.argv[1].lstrip('v')
    force = "--force" in sys.argv

    print(f"\n🚀 Building ActivityTracker v{version}\n")

    # Step 1: 빌드 체크
    print("[1/2] Checking build status...")
    if force:
        print("  → Force rebuild requested")
        run_pyinstaller()
    elif need_rebuild():
        print("  → Source changed, rebuilding...")
        run_pyinstaller()
    else:
        print("  → SKIP (already up to date)")

    # Step 2: 릴리즈 패키지 생성 (chrome_extension 폴더 포함)
    print("\n[2/2] Creating release package...")
    release_zip = create_release_zip(version)

    # 결과 출력
    size_mb = release_zip.stat().st_size / (1024 * 1024)
    print(f"\n✅ Created: {release_zip}")
    print(f"   Size: {size_mb:.1f} MB\n")


if __name__ == "__main__":
    main()
