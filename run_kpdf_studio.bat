@echo off
pushd "%~dp0"

if not exist "kpdf_studio.py" (
    echo [ERROR] kpdf_studio.py not found!
    pause
    popd
    exit /b 1
)

python "kpdf_studio.py" %*

if not "%~1"=="" (
    pause > nul
)
popd
