@echo off
chcp 65001 > nul
pushd "%~dp0"
echo ===================================================
echo   K-PDF Studio 원클릭 자동 실행기
echo ===================================================
echo.
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 파이썬을 설치하시거나
    echo 윈도우 터미널에서 'winget install Python.Python.3.11' 을 실행해 주세요.
    echo (설치 시 'Add python.exe to PATH' 체크 필수)
    echo.
    pause
    popd
    exit /b 1
)

echo [1/2] 필수 패키지(PyQt6, PyMuPDF) 확인 중...
pip install -q PyQt6 pymupdf

echo [2/2] K-PDF Studio를 실행합니다...
start "" pythonw "kpdf_studio.py"
popd
exit /b 0
