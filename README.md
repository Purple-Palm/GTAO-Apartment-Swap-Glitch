# GTA Online Apartment Trade-In Automation (Python / OCR)

**V9 - Automated No-Save Method**

## ⚠️ CRITICAL DISCLAIMER
**I (the creator) was banned (30-day suspension + wipe) after generating $200M in 4 hours.**
My friend used this exact script for $10M and is safe.
**USE AT YOUR OWN RISK.**
* **Recommended Limit:** 10M-20M per week.
* **Detection Risk:** High if abused. Low if used conservatively.

## Description
This tool replaces legacy AutoHotKey (AHK) scripts. It uses **Computer Vision (OpenCV)** to detect game elements rather than relying on blind coordinate clicking.

**Capabilities:**
1.  **Smart Detection:** Uses image matching to find buttons.
2.  **Network Control:** Automatically blocks Rockstar servers (No-Save) using Windows Firewall rules.
3.  **Automation:** Handles the purchase, trade-in, disconnection, and reconnection loop.

## Prerequisites
* **OS:** Windows 10/11
* **Python:** 3.10 or newer.
* **Game Settings (MANDATORY):**
    * **Screen Type:** Windowed Borderless
    * **Mouse Input:** Raw Input
    * **Phone Settings:** Quick Snapmatic **OFF**
    * **Resolution:** 1920x1080 or higher recommended.

## Installation
1.  **Download:** Clone this repository or download the ZIP file.
    * *Ensure you have the `assets` folder. The script will not work without it.*
2.  **Install & Run:**
    * Double-click `run.bat`.
    * This script will automatically create a virtual environment, install dependencies (`opencv`, `pyautogui`, `mss`, etc.), and launch the tool.
    * **Admin Rights:** You must allow the UAC prompt. Admin rights are required to toggle the Windows Firewall.

## Usage
1.  Launch GTA V and enter an Invite Only Session.
2.  Ensure you own the expensive apartment you wish to trade.
3.  Run the script via `run.bat`.
4.  Follow the on-screen prompts (Input number of loops).
5.  Press **F1** to begin the automation.
6.  Press **Q** to emergency stop.

## Troubleshooting
* **Script crashes/Can't find images:** Ensure your game is not in Fullscreen mode. It must be **Windowed Borderless**.
* **"Fail" screenshots:** If the script fails, check the `debug_errors` folder for screenshots of what the bot saw when it crashed.

## Development
**Status: PAUSED**
The developer is currently banned. Active development will resume when the suspension is lifted or contributors provide pull requests.
