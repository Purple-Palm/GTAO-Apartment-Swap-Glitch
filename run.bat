@echo off
Title GTA Online Glitcher Installer and Runner
color 0A
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
if %errorlevel% NEQ 0 (echo Python is not installed or not added to PATH & pause & exit)
if exist ".venv" goto StartScript
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
if not exist "requirements.txt" (echo keyboard&echo mss&echo numpy&echo opencv-python&echo pyautogui&echo pydirectinput)>requirements.txt
pip install -r requirements.txt
:StartScript
if not defined VIRTUAL_ENV call .venv\Scripts\activate
python main.py
pause
