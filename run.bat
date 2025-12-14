@echo off
Title GTA Glitcher Launcher
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (goto UACPrompt) else (goto gotAdmin)
:UACPrompt
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
set params= %*
echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"
exit /B
:gotAdmin
pushd "%CD%"
CD /D "%~dp0"
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and check "Add to PATH" in the installer.
    pause
    exit
)
if not exist ".venv" (
    echo [INIT] Creating Virtual Environment...
    python -m venv .venv
)
call .venv\Scripts\activate
echo [INIT] Checking dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install requests keyboard mss numpy opencv-python pyautogui pydirectinput pygetwindow pywin32 >nul 2>&1
cls
python launcher.py
pause
