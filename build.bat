@echo off
echo ====================================
echo ScreenCapture exe 빌드 시작
echo ====================================
echo.

REM PyInstaller 설치 확인
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되어 있지 않습니다.
    echo PyInstaller를 설치합니다...
    pip install pyinstaller
    echo.
)

REM 이전 빌드 산출물 삭제
echo 이전 빌드 산출물 삭제 중...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

REM exe 빌드
echo exe 빌드 중...
pyinstaller ScreenCapture.spec

echo.
if exist dist\ScreenCapture.exe (
    echo ====================================
    echo 빌드 성공!
    echo ====================================
    echo.
    echo 빌드된 파일: dist\ScreenCapture.exe
    echo.
    echo 배포하려면 다음 파일/폴더를 함께 복사하세요:
    echo   - dist\ScreenCapture.exe
    echo   - config.json
    echo.
    pause
) else (
    echo ====================================
    echo 빌드 실패!
    echo ====================================
    pause
)
