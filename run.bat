@echo off
Title GTA Glitcher Terminal
color 0B
chcp 65001 >nul

:: ============================================
::  Admin Check
:: ============================================
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (goto UACPrompt) else (goto gotAdmin)

:UACPrompt
echo.
echo  [SYSTEM] Requesting Administrator Privileges...
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
set params= %*
echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"
exit /B

:gotAdmin
pushd "%CD%"
CD /D "%~dp0"

:START_LOOP
cls

:: ============================================
::  Silent Environment Check
:: ============================================
:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    cls
    echo.
    echo  [ERROR] Python Not Detected!
    echo  Please install Python 3.10+ and check "Add to PATH".
    pause
    exit
)

:: 2. Setup/Activate Venv
if not exist ".venv" (
    echo.
    echo  [*] Initializing Python Environment...
    python -m venv .venv
)
call .venv\Scripts\activate

:: 3. Check Launcher Deps
python -m pip show requests >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [*] Updating Libraries...
    python -m pip install requests --quiet
)

:: ============================================
::  Launch
:: ============================================
python launcher.py

:: ============================================
::  Exit Handling
:: ============================================
set EXIT_CODE=%errorlevel%

:: Code 100 = Auto-Restart
if %EXIT_CODE% EQU 100 (
    goto START_LOOP
)

:: Code 1 = Crash/Error
if %EXIT_CODE% NEQ 0 (
    echo.
    echo  [SYSTEM] Process terminated with error code %EXIT_CODE%.
    pause
)

:: Code 0 = Normal Exit
exit