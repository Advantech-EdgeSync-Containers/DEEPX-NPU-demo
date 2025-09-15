@echo off
setlocal

call venv-opencv\Scripts\activate

start cmd /K "python" clip_demo_app_opencv\dx_realtime_multi_demo.py

endlocal