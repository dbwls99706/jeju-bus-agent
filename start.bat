@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem This launcher is explicitly the rules-only path.
set "BUS_MODEL_DIR="
where py >nul 2>nul
if not errorlevel 1 (
 py -3 launch.py
 goto done
)
where python >nul 2>nul
if errorlevel 1 (
 echo Python을 찾을 수 없습니다. python.org에서 Python 3.12를 설치한 뒤 다시 실행하세요.
 goto done
)
python launch.py
:done
pause
