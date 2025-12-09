@echo off
Title GTA Online Glitcher Installer and Runner
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo [INFO] Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )
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
    echo [CRITICAL ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ and check "Add to PATH" during installation.
    pause
    exit
)
if exist ".venv" (
    echo [INFO] Virtual environment found. Starting...
    goto StartScript
) else (
    echo [INIT] First run detected. Setting up environment...
    echo [1/3] Creating .venv...
    python -m venv .venv
    call .venv\Scripts\activate
    python -m pip install --upgrade pip
    if not exist "requirements.txt" (
        echo [2/3] Genererating requirements.txt...
        (
            echo keyboard
            echo mss
            echo numpy
            echo opencv-python
            echo pyautogui
            echo pydirectinput
        ) > requirements.txt
    )
    echo [3/3] Installing dependencies...
    pip install -r requirements.txt
    echo [SUCCESS] Setup complete!
    goto StartScript
)
:StartScript
    if not defined VIRTUAL_ENV call .venv\Scripts\activate
    echo.
    echo Launching Main Script...
    python main.py
    echo.
    echo [EXIT] Script finished.
    pause
