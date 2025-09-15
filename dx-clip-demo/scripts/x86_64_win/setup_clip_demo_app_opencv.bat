@echo off

REM Pre-Requisite: Ensure Python 3.11 or 3.12 is installed
for /f "tokens=2-3 delims=. " %%v in ('python -V 2^>^&1') do set PY_MAJOR=%%v& set PY_MINOR=%%w
if not defined PY_MAJOR goto :python_not_installed
if not defined PY_MINOR goto :python_not_installed
if %PY_MAJOR% LSS 3 goto :python_too_old
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 11 goto :python_too_old

REM Update Python packages
python -m pip install --upgrade pip

REM 1. Set up Virtual Environment
python -m venv venv-opencv
call venv-opencv\Scripts\activate.bat

REM 2. Install pip packages
pip install -r requirements.opencv.txt
pip install ./assets/CLIP

REM 3. Install DX-RunTime Python package based on Python version
if %PY_MAJOR% EQU 3 if %PY_MINOR% EQU 11 (
    pip install install_dep/windows_python311/dx_engine-1.0.0-py3-none-any.whl
) else if %PY_MAJOR% EQU 3 if %PY_MINOR% EQU 12 (
    pip install install_dep/windows_python312/dx_engine-1.0.1-py3-none-any.whl
) else (
    echo Python version not supported for DX-RunTime installation
)

if !errorlevel! neq 0 (
    exit /b 1
)

echo Setup complete!
exit /b 0

:python_not_installed
echo Python is not installed. Please install Python 3.11 or 3.12 first.
pause
exit /b 1

:python_too_old
echo Python version is less than 3.11. Please upgrade Python.
pause
exit /b 1
