@echo off
chcp 65001 >nul
Title GTA Online Apartment Glitch v10

:: ============================================
::  Check for Admin Rights (required for firewall)
:: ============================================
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (goto UACPrompt) else (goto gotAdmin)

:UACPrompt
echo [!] Requesting Administrator privileges...
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
set params= %*
echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"
exit /B

:gotAdmin
pushd "%CD%"
CD /D "%~dp0"

echo.
echo ==========================================
echo   GTA Online Apartment Glitch v10
echo ==========================================
echo.

:: ============================================
::  Check Python Installation
:: ============================================
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [X] Python is not installed or not in PATH!
    echo     Download from: https://www.python.org/downloads/
    pause
    exit
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python %PYVER% detected

:: ============================================
::  Setup Virtual Environment
:: ============================================
if exist ".venv" goto CheckVenv

echo [*] Creating virtual environment...
python -m venv .venv
if %errorlevel% NEQ 0 (
    echo [X] Failed to create virtual environment!
    pause
    exit
)

:CheckVenv
if not defined VIRTUAL_ENV (
    echo [*] Activating virtual environment...
    call .venv\Scripts\activate
)

:: ============================================
::  Install/Update Dependencies
:: ============================================
if not exist "requirements.txt" (
    echo [*] Creating requirements.txt...
    (
        echo keyboard
        echo mss
        echo numpy
        echo opencv-python
        echo pyautogui
        echo pydirectinput
    ) > requirements.txt
)

:: Check if packages are installed
pip show keyboard >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [*] Installing dependencies...
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    if %errorlevel% NEQ 0 (
        echo [X] Failed to install dependencies!
        pause
        exit
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

:: ============================================
::  Check Assets Folder
:: ============================================
if not exist "assets" (
    echo [X] 'assets' folder not found!
    echo     Make sure you have the assets folder with PNG images.
    pause
    exit
)
echo [OK] Assets folder found

:: ============================================
::  Run the Script
:: ============================================
echo.
echo [*] Starting GTA Online Glitcher...
echo     Press Q at any time to emergency stop.
echo.
python main.py

:: ============================================
::  Cleanup on Exit
:: ============================================
echo.
echo [*] Cleaning up firewall rules...
netsh advfirewall firewall delete rule name="GTAOSAVEBLOCK" >nul 2>&1
echo [OK] Done!
echo.
pause
