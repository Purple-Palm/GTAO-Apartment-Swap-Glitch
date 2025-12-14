import requests
import os
import sys
import subprocess
import time
import zipfile
import shutil

GITHUB_USER = "Purple-Palm"
GITHUB_REPO = "GTAO-Apartment-Swap-Glitch"
BRANCH = "main"

BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
VERSION_URL = f"{BASE_URL}/version.txt"
SCRIPT_URL = f"{BASE_URL}/main.py"
ASSETS_ZIP_URL = f"{GITHUB_USER}/{GITHUB_REPO}/raw/{BRANCH}/assets.zip" 
ASSETS_ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/raw/{BRANCH}/assets.zip"

LOCAL_SCRIPT = "gta_bot.py"
LOCAL_VERSION_FILE = "version.txt"
LOCAL_ASSETS_DIR = "assets"
TEMP_ZIP = "update_assets.zip"

def get_local_version():
    if not os.path.exists(LOCAL_VERSION_FILE):
        return "0.0"
    try:
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    except:
        return "0.0"

def download_file(url, filename):
    print(f"   [DOWNLOAD] Downloading {filename}...")
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"   [ERROR] Failed to download {url}: {e}")
        return False

def extract_assets():
    print("   [INSTALL] Extracting assets...")
    try:
        if os.path.exists(LOCAL_ASSETS_DIR):
            shutil.rmtree(LOCAL_ASSETS_DIR)
        
        with zipfile.ZipFile(TEMP_ZIP, 'r') as zip_ref:
            zip_ref.extractall(".") 
            
        os.remove(TEMP_ZIP)
        return True
    except Exception as e:
        print(f"   [ERROR] Zip extraction failed: {e}")
        return False

def check_for_updates():
    print(f"[LAUNCHER] Checking for updates from {GITHUB_USER}...")
    
    try:
        response = requests.get(VERSION_URL)
        if response.status_code != 200:
            print("[WARN] Could not connect to update server. Starting existing bot...")
            return False
        remote_version = response.text.strip()
    except:
        print("[WARN] Connection timed out. Starting existing bot...")
        return False

    local_version = get_local_version()

    if remote_version != local_version or not os.path.exists(LOCAL_SCRIPT):
        print(f"\n[UPDATE DETECTED] v{local_version} -> v{remote_version}")
        
        if not download_file(SCRIPT_URL, LOCAL_SCRIPT):
            print("[FATAL] Could not download script. Aborting.")
            sys.exit()
            
        if not download_file(ASSETS_ZIP_URL, TEMP_ZIP):
            print("[FATAL] Could not download assets. Aborting.")
            sys.exit()
            
        if extract_assets():
            with open(LOCAL_VERSION_FILE, "w") as f:
                f.write(remote_version)
            print("[SUCCESS] Update complete!")
            return True
    else:
        print(f"[LAUNCHER] Version {local_version} is up to date.")
        return False

def run_bot():
    if not os.path.exists(LOCAL_SCRIPT):
        print("[ERROR] Bot script not found!")
        input("Press Enter to exit...")
        sys.exit()
        
    print("\n" + "="*30)
    print(f" STARTING BOT (v{get_local_version()})")
    print("="*30 + "\n")
    time.sleep(1)
    
    try:
        subprocess.run([sys.executable, LOCAL_SCRIPT])
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    check_for_updates()
    run_bot()
