@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "BUS_MODEL_DIR=%CD%\models\qwen15"
if not exist .venv\Scripts\python.exe (
 echo README의 AI 설치 단계를 먼저 실행하세요.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" launch.py
pause
