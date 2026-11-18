@echo off
pushd "%~dp0"

if not exist "create_shortcut.py" (
    echo [ERROR] create_shortcut.py not found!
    pause
    popd
    exit /b 1
)

python "create_shortcut.py" %*

pause
popd
