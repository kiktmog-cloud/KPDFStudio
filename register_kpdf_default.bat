@echo off
pushd "%~dp0"

if not exist "register_associations.py" (
    echo [ERROR] register_associations.py not found!
    pause
    popd
    exit /b 1
)

python "register_associations.py" %*

echo.
echo Press any key to open Windows Default Apps settings...
pause > nul

start ms-settings:defaultapps

popd
