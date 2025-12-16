@echo off
Title GTA Glitcher Launcher
chcp 65001 >nul

:: Check Admin
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (goto UACPrompt) else (goto gotAdmin)

:UACPrompt
echo Requesting Admin...
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
set params= %*
echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"
exit /B

:gotAdmin
pushd "%CD%"
CD /D "%~dp0"

:: Quick Environment Check
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [ERROR] Python not found!
    pause
    exit
)

if not exist ".venv" (
    echo [INIT] Creating Venv...
    python -m venv .venv
)

call .venv\Scripts\activate

:: Ensure 'requests' exists for the launcher to work
pip show requests >nul 2>&1
if %errorlevel% NEQ 0 pip install requests --quiet

:: Run Launcher
python launcher.py

:: If launcher exits normally, we pause. 
:: If launcher triggers a restart, it kills this window anyway.
pause