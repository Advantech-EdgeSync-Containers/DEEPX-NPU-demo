@echo off
setlocal EnableDelayedExpansion
cls
echo ===============================
echo   Select installation option
echo ===============================
echo 1. PyQT5 Version Demo
echo 2. OpenCV Version Demo
echo ===============================
set /p choice=Enter your choice (1 or 2): 

if "%choice%"=="1" (
    echo Preparing PyQT5 demo
    set "PYQT_DEMO_INSTALL=true"
    set "OPENCV_DEMO_INSTALL=false"
) else if "%choice%"=="2" (
    echo Preparing OpenCV demo
    set "PYQT_DEMO_INSTALL=false"
    set "OPENCV_DEMO_INSTALL=true"
) else (
    echo Invalid input. Please enter 1 or 2 only.
    pause
    exit /b
)
set "PYQT_DEMO_INSTALL=!PYQT_DEMO_INSTALL: =!"
set "OPENCV_DEMO_INSTALL=!OPENCV_DEMO_INSTALL: =!"

rem -------------------------------------
rem 2. Download model and video assets
rem -------------------------------------
set "MODELS_URL=https://sdk.deepx.ai/res/assets/clip_assets.tar.gz"
set "VIDEOS_URL=https://sdk.deepx.ai/res/video/videos.tar.gz"
set "MODELS_PATH=assets"
set "VIDEOS_PATH=assets\demo_videos"

echo.
echo [INFO] Preparing to download model and video files...

if not exist "%MODELS_PATH%" (
    echo "not found models, make dir %MODELS_PATH%"
    mkdir "%MODELS_PATH%"
    echo "Download clip_assets.tar.gz file URL : %MODELS_URL%"
    curl --progress-bar -o clip_assets.tar.gz %MODELS_URL%
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to download model files.
        pause
        exit /b
    )
    echo "extract clip_assets.tar.gz to %MODELS_PATH%"
    tar -xzvf clip_assets.tar.gz -C %MODELS_PATH%
    if !errorlevel! == 0 (
        del /f /q clip_assets.tar.gz
        echo "remove clip_assets.tar.gz"
    )
    echo "Download clip_assets.tar.gz and extract models : Complete"
) else (
    echo "models directory found (%MODELS_PATH%)"
    echo "stop downloading models tar gz"
)

if not exist "%VIDEOS_PATH%" (
    echo "not found videos, make dir %VIDEOS_PATH%"
    mkdir "%VIDEOS_PATH%"
    echo "Download videos tar.gz file URL : %VIDEOS_URL%"
    curl --progress-bar -o videos.tar.gz %VIDEOS_URL%
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to download video files.
        pause
        exit /b
    )
    echo "extract videos.tar.gz to %VIDEOS_PATH%"
    tar -xzvf videos.tar.gz -C %VIDEOS_PATH%
    if !errorlevel! == 0 (
        del /f /q videos.tar.gz
        echo "remove videos.tar.gz"
    )
    echo "Download videos.tar.gz and extract videos : Complete"
) else (
    echo "videos directory found (%VIDEOS_PATH%)"
    echo "stop downloading videos tar gz"
)

rem -------------------------------------
rem 3. Create venv and install requirements
rem -------------------------------------
echo.
echo [INFO] Preparing virtual environment and demo...

if "!OPENCV_DEMO_INSTALL!" == "true"  (
    set "ENV_FOLDER=venv-opencv"
    set "SETUP_VENV=setup_clip_demo_app_opencv.bat"
) else if "!PYQT_DEMO_INSTALL!" == "true" (
    set "ENV_FOLDER=venv-pyqt"
    set "SETUP_VENV=setup_clip_demo_app_pyqt.bat"
)

if exist "%~dp0!ENV_FOLDER!\" (
echo Directory exists: %~dp0!ENV_FOLDER!
) else (
    echo call !SETUP_VENV! file ....  
    call "%~dp0scripts\x86_64_win\!SETUP_VENV!"
)

if !errorlevel! neq 0 (
    echo [ERROR] Failed to configurate virtual environment.
    pause
    exit /b
)

echo .
echo [INFO]Installation complete. 
echo Would you like to run the demo now? [y / n] (default: "n")

set /p choice=

if "%choice%"=="" set "choice=n"

if /i "%choice%"=="y" (
    if "!OPENCV_DEMO_INSTALL!" == "true"  (
        call "%~dp0\run_script_opencv.bat"
    ) else if "!PYQT_DEMO_INSTALL!" == "true" (
        call "%~dp0\run_script_pyqt.bat"
    )
) else (
    echo Exiting the script.
)

