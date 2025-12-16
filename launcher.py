import requests
import os
import sys
import subprocess
import time
import zipfile
import shutil
import threading

# --- CONFIGURATION ---
GITHUB_USER = "Purple-Palm"
GITHUB_REPO = "GTAO-Apartment-Swap-Glitch"
BRANCH = "v14-integration"

# GitHub URLs
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
VERSION_URL = f"{BASE_URL}/version.txt"

# Files to manage
FILES_TO_SYNC = {
    "main.py": f"{BASE_URL}/main.py",
    "launcher.py": f"{BASE_URL}/launcher.py",
    "run.bat": f"{BASE_URL}/run.bat"
}

ASSETS_ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/raw/{BRANCH}/assets.zip"
LOCAL_ASSETS_DIR = "assets"
LOCAL_VERSION_FILE = "version.txt"
TEMP_ZIP = "assets_update.zip"

# Bot Dependencies
BOT_REQUIREMENTS = [
    "keyboard", "mss", "numpy", "opencv-python", 
    "pyautogui", "pydirectinput"
]

def get_local_version():
    if not os.path.exists(LOCAL_VERSION_FILE): return "0.0"
    try:
        with open(LOCAL_VERSION_FILE, "r") as f: return f.read().strip()
    except: return "0.0"

def download_file(url, filename):
    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"\n   [ERROR] Failed to download {filename}: {e}")
        return False

def extract_assets():
    print("   [INSTALL] Extracting assets...")
    try:
        # Remove old assets to prevent conflicts
        if os.path.exists(LOCAL_ASSETS_DIR):
            shutil.rmtree(LOCAL_ASSETS_DIR)
        
        with zipfile.ZipFile(TEMP_ZIP, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        os.remove(TEMP_ZIP)
        return True
    except Exception as e:
        print(f"   [ERROR] Zip extraction failed: {e}")
        return False

def perform_self_update_restart():
    """
    Creates a temporary batch file to swap locked files (run.bat/launcher.py)
    and restarts the process.
    """
    print("\n[SYSTEM] Applying updates and restarting...")
    
    updater_script = """
@echo off
timeout /t 2 /nobreak >nul
:: Move new files over old ones
if exist "run.bat.new" move /y "run.bat.new" "run.bat" >nul
if exist "launcher.py.new" move /y "launcher.py.new" "launcher.py" >nul
:: Restart
start "" "run.bat"
del "%~f0"
"""
    with open("_updater.bat", "w") as f:
        f.write(updater_script)
    
    # Launch the updater and exit this python process
    subprocess.Popen(["_updater.bat"], shell=True)
    sys.exit()

def check_integrity_and_update():
    print(f"[LAUNCHER] Checking integrity and updates...")
    
    # 1. Get Remote Version
    try:
        response = requests.get(VERSION_URL, timeout=5)
        if response.status_code == 200:
            remote_version = response.text.strip()
        else:
            remote_version = get_local_version()
    except:
        remote_version = get_local_version() # Assume offline if failed

    local_version = get_local_version()
    
    # 2. Check for missing critical files (Force Update if missing)
    missing_assets = not os.path.exists(LOCAL_ASSETS_DIR)
    missing_main = not os.path.exists("main.py")
    
    needs_update = (remote_version != local_version) or missing_assets or missing_main

    if needs_update:
        if missing_assets:
            print(f"[REPAIR] Assets folder missing. Restoring...")
        elif missing_main:
            print(f"[REPAIR] Main script missing. Restoring...")
        else:
            print(f"[UPDATE] v{local_version} -> v{remote_version}")

        # Download Files
        for filename, url in FILES_TO_SYNC.items():
            # Download to .new to avoid locking issues
            temp_name = f"{filename}.new"
            if download_file(url, temp_name):
                # If it's main.py, we can just swap it here
                if filename == "main.py":
                    if os.path.exists("main.py"): os.remove("main.py")
                    os.rename(temp_name, "main.py")
            
        # Download Assets
        if download_file(ASSETS_ZIP_URL, TEMP_ZIP):
            extract_assets()
            
        # Update Version File
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(remote_version)

        # If launcher or run.bat were downloaded as .new, trigger restart
        if os.path.exists("run.bat.new") or os.path.exists("launcher.py.new"):
            perform_self_update_restart()
            
        print("[SUCCESS] Update complete!")
    else:
        print(f"[LAUNCHER] System is up to date (v{local_version}).")

# --- SMOOTH PROGRESS BAR LOGIC ---
stop_thread = False

def animate_bar(current_step, total_steps, package_name):
    """
    Runs in a thread to animate the bar smoothly between steps
    """
    bar_width = 30
    step_width = 100 / total_steps
    start_percent = (current_step - 1) * step_width
    end_percent = current_step * step_width
    
    current_val = start_percent
    
    while not stop_thread and current_val < end_percent:
        time.sleep(0.01) # Speed of animation
        current_val += 0.5 # Increment
        
        # Draw Bar
        filled_len = int(bar_width * (current_val / 100))
        bar = '█' * filled_len + '-' * (bar_width - filled_len)
        sys.stdout.write(f"\r[{bar}] {int(current_val)}% | Checking: {package_name:<15}")
        sys.stdout.flush()

def verify_dependencies():
    global stop_thread
    print(f"\n[*] Verifying environment...")
    
    total = len(BOT_REQUIREMENTS)
    
    for i, package in enumerate(BOT_REQUIREMENTS, 1):
        stop_thread = False
        
        # Start animation thread
        t = threading.Thread(target=animate_bar, args=(i, total, package))
        t.start()
        
        try:
            # Run pip verify/install
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass # Ignore errors for smooth flow, bot will crash later if critical
            
        # Stop animation and fill bar for this step
        stop_thread = True
        t.join()

    # Final 100% Bar
    bar_width = 30
    sys.stdout.write(f"\r[{'█' * bar_width}] 100% | Ready!                       \n")
    sys.stdout.flush()

def run_bot():
    if not os.path.exists("main.py"):
        print("[ERROR] Bot script not found!")
        return
        
    print("\n" + "="*35)
    print(f" STARTING GTA ONLINE APARTMENT GLITCH (v{get_local_version()})")
    print("="*35 + "\n")
    time.sleep(1)
    
    try:
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    check_integrity_and_update()
    verify_dependencies()
    run_bot()