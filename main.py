import cv2
import numpy as np
import pyautogui
import pydirectinput
import time
import subprocess
import sys
import atexit
import keyboard
import mss
import os
import logging
import json
import win32gui
import win32con
import ctypes
import pygetwindow as gw
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from pathlib import Path
from enum import Enum, auto

# ==================== CONFIGURATION ====================

@dataclass
class Config:
    """Centralized script configuration"""
    CONFIDENCE: float = 0.7
    BLOCKED_IPS: str = "192.81.241.171"
    RULE_NAME: str = "GTAOSAVEBLOCK_V14"
    PANIC_KEY: str = 'q'
    START_KEY: str = 'f1'
    
    # Scaling Source
    SOURCE_WIDTH: int = 2560
    SOURCE_HEIGHT: int = 1440
    
    # Timeouts (seconds)
    STORY_MODE_TIMEOUT: int = 120
    ONLINE_LOAD_TIMEOUT: int = 180
    IMAGE_DEFAULT_TIMEOUT: int = 5
    
    # Delays (seconds)
    KEY_PRESS_DOWN: float = 0.02
    KEY_PRESS_UP: float = 0.03
    MOUSE_CLICK_DURATION: float = 0.06
    SCAN_INTERVAL: float = 0.01
    
    # Paths
    ASSETS_DIR: Path = Path("assets")
    DEBUG_DIR: Path = Path("debug_errors")
    LOG_FILE: Path = Path("gta_debug.log")
    STATS_FILE: Path = Path("stats.json")

# ==================== GLOBALS ====================

CONFIG = Config()
ASSET_CACHE: Dict[str, np.ndarray] = {}
sct = mss.mss()
pydirectinput.FAILSAFE = True

# Global Window State
GAME_WINDOW = None
SCALE_FACTOR_X = 1.0
SCALE_FACTOR_Y = 1.0

# Statistics
STATS = {
    "total_loops_completed": 0,
    "total_properties_bought": 0,
    "errors_recovered": 0,
    "session_start": None,
    "last_run": None
}

# ==================== LOGGING ====================

def setup_logging():
    """Configures the logging system"""
    CONFIG.DEBUG_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(CONFIG.LOG_FILE, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log(msg: str):
    logging.info(msg)

def log_debug(msg: str):
    logging.debug(msg)

def log_error(msg: str):
    logging.error(msg)

def log_warning(msg: str):
    logging.warning(msg)

# ==================== STATS MANAGEMENT ====================

def load_stats():
    global STATS
    if CONFIG.STATS_FILE.exists():
        try:
            with open(CONFIG.STATS_FILE, 'r') as f:
                saved_stats = json.load(f)
                STATS.update(saved_stats)
                log(f"[STATS] Loaded: {STATS['total_loops_completed']} loops, {STATS['total_properties_bought']} properties")
        except Exception as e:
            log_warning(f"[STATS] Could not load stats: {e}")

def save_stats():
    STATS["last_run"] = datetime.now().isoformat()
    try:
        with open(CONFIG.STATS_FILE, 'w') as f:
            json.dump(STATS, f, indent=2)
    except Exception as e:
        log_warning(f"[STATS] Could not save stats: {e}")

def update_stats(loops: int = 0, properties: int = 0, errors: int = 0):
    STATS["total_loops_completed"] += loops
    STATS["total_properties_bought"] += properties
    STATS["errors_recovered"] += errors
    save_stats()

# ==================== WINDOW & SCALING ====================

def focus_console():
    """Restores focus to the Python console window"""
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        try:
            log("[UI] Switching focus back to Console...")
            pydirectinput.press('alt') 
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            log(f"[WARN] Could not auto-focus console. {e}")

def find_game_window():
    """Finds the game window and calculates scaling factors"""
    global GAME_WINDOW, SCALE_FACTOR_X, SCALE_FACTOR_Y
    
    log("[INIT] Searching for 'Grand Theft Auto V' window...")
    
    possible_titles = ["Grand Theft Auto V", "GTA V", "Grand Theft Auto V Premium Edition"]
    target_window = None
    
    for title in possible_titles:
        windows = gw.getWindowsWithTitle(title)
        if windows:
            target_window = windows[0]
            break
            
    if not target_window:
        log("[CRITICAL] Game Window not found! Is the game running?")
        sys.exit()

    GAME_WINDOW = target_window
    
    try:
        if not target_window.isActive:
            log("[INIT] Activating Game Window...")
            target_window.activate()
            target_window.restore()
            time.sleep(1.0) 
    except Exception as e:
        log(f"[WARN] Could not force focus (Admin rights?): {e}")

    current_w, current_h = target_window.width, target_window.height
    
    # Scaling Logic
    SCALE_FACTOR_X = current_w / CONFIG.SOURCE_WIDTH
    SCALE_FACTOR_Y = current_h / CONFIG.SOURCE_HEIGHT
    
    log(f"[INIT] Game Resolution: {current_w}x{current_h}")
    log(f"[INIT] Auto-Scaling Factor: {SCALE_FACTOR_X:.4f} (X) / {SCALE_FACTOR_Y:.4f} (Y)")

def get_game_rect():
    if GAME_WINDOW:
        return {
            "left": GAME_WINDOW.left,
            "top": GAME_WINDOW.top,
            "width": GAME_WINDOW.width,
            "height": GAME_WINDOW.height
        }
    return {"left": 0, "top": 0, "width": pyautogui.size()[0], "height": pyautogui.size()[1]}

# ==================== ASSET MANAGEMENT ====================

def load_assets_into_ram() -> bool:
    """Loads and RESIZES assets into memory"""
    log("[INIT] Loading assets into RAM...")
    
    if not CONFIG.ASSETS_DIR.exists():
        log_error(f"[ERROR] '{CONFIG.ASSETS_DIR}' folder not found!")
        return False
    
    loaded_count = 0
    needs_resize = abs(SCALE_FACTOR_X - 1.0) > 0.02
    
    for filepath in CONFIG.ASSETS_DIR.glob("*.png"):
        img = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        
        if img is not None:
            if needs_resize:
                h, w = img.shape
                new_w = max(1, int(w * SCALE_FACTOR_X))
                new_h = max(1, int(h * SCALE_FACTOR_Y))
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            ASSET_CACHE[filepath.name] = img
            loaded_count += 1
        else:
            log_warning(f"[WARN] Failed to load {filepath.name}")
    
    log(f"[INIT] {loaded_count} assets cached and resized.")
    return loaded_count > 0

# ==================== ROI ====================

ROIS_REL = {
    "ALL": (0.0, 0.0, 1.0, 1.0),
    "BROWSER_MAIN": (0.0, 0.0, 1.0, 1.0),
    "HUD_AREA": (0.7, 0.0, 0.3, 0.3),         
    "BOTTOM_RIGHT": (0.7, 0.7, 0.3, 0.3)      
}

def get_region_absolute(name):
    win = get_game_rect()
    r = ROIS_REL.get(name, ROIS_REL["ALL"])
    
    top_offset = int(win["height"] * r[0])
    left_offset = int(win["width"] * r[1])
    h = int(win["height"] * r[2])
    w = int(win["width"] * r[3])
    
    return {
        "top": win["top"] + top_offset,
        "left": win["left"] + left_offset,
        "width": w,
        "height": h
    }

# ==================== FIREWALL MANAGEMENT ====================

class FirewallManager:
    _is_blocked: bool = False
    
    @classmethod
    def block(cls) -> bool:
        if cls._is_blocked:
            return True 
        log("[FIREWALL] BLOCKING Connection...")
        cmd = f'netsh advfirewall firewall add rule name="{CONFIG.RULE_NAME}" dir=out action=block remoteip={CONFIG.BLOCKED_IPS} enable=yes'
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls._is_blocked = True
        return True
    
    @classmethod
    def unblock(cls) -> bool:
        log("[FIREWALL] RESTORING Connection...")
        cmd = f'netsh advfirewall firewall delete rule name="{CONFIG.RULE_NAME}"'
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls._is_blocked = False
        return True

def clean_exit():
    FirewallManager.unblock()
    save_stats()

atexit.register(clean_exit)

# ==================== INPUT HELPERS ====================

def check_panic_key():
    if keyboard.is_pressed(CONFIG.PANIC_KEY):
        log(f"\n[PANIC] '{CONFIG.PANIC_KEY.upper()}' Pressed. Exiting.")
        FirewallManager.unblock()
        save_stats()
        sys.exit(0)

def fast_press(key: str, count: int = 1):
    for _ in range(count):
        check_panic_key()
        pydirectinput.keyDown(key)
        time.sleep(CONFIG.KEY_PRESS_DOWN)
        pydirectinput.keyUp(key)
        time.sleep(CONFIG.KEY_PRESS_UP)

def safe_type(text: str, interval: float = 0.02):
    """Uses pydirectinput write for URL typing"""
    check_panic_key()
    pydirectinput.write(text, interval=interval)

# ==================== IMAGE DETECTION (Merged Logic) ====================

def find_image(
    image_name: str, 
    region_name: str = "ALL", 
    timeout: float = 5, 
    click: bool = False, 
    wait_after: float = 0.1, 
    crash_if_missing: bool = False,
    override_confidence: float = None
) -> bool:
    
    start = time.time()
    template = ASSET_CACHE.get(image_name)
    
    if template is None:
        log_error(f"[ERROR] Asset '{image_name}' not found!")
        if crash_if_missing: sys.exit(1)
        return False

    region = get_region_absolute(region_name)
    required_confidence = override_confidence if override_confidence else CONFIG.CONFIDENCE

    if "buy" in image_name or "online" in image_name:
        log_debug(f"Scanning for '{image_name}' (Conf: {required_confidence})...")

    best_val_seen = 0.0

    while time.time() - start < timeout:
        check_panic_key()

        try:
            img_grab = sct.grab(region)
            img_np = np.array(img_grab)
            screen_gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_val_seen:
                best_val_seen = max_val

            if max_val >= required_confidence:
                if click:
                    h_img, w_img = template.shape[:2]
                    rx, ry = max_loc
                    # Exact center calculation
                    global_x = rx + region['left'] + (w_img // 2)
                    global_y = ry + region['top'] + (h_img // 2)
                    
                    log(f"[ACTION] Clicking '{image_name}' at ({global_x}, {global_y})")
                    pydirectinput.moveTo(global_x, global_y)
                    pydirectinput.mouseDown()
                    time.sleep(CONFIG.MOUSE_CLICK_DURATION)
                    pydirectinput.mouseUp()
                
                time.sleep(wait_after)
                return True
                
        except Exception:
            pass
        
        time.sleep(CONFIG.SCAN_INTERVAL)
    
    if crash_if_missing:
        # Simple dump logic
        timestamp = datetime.now().strftime("%H-%M-%S")
        err_filename = CONFIG.DEBUG_DIR / f"FAIL_{image_name}_{timestamp}.png"
        try:
            fail_grab = sct.grab(region)
            mss.tools.to_png(fail_grab.rgb, fail_grab.size, output=str(err_filename))
            log(f"[CRITICAL] Dumped failure to {err_filename}")
        except: pass
        
        log(f"[CRITICAL] Best val: {best_val_seen:.2f} / Required: {required_confidence}")
        FirewallManager.unblock()
        sys.exit(1)
        
    return False

# ==================== GAME LOGIC ====================

def confirm_story_mode_spawn():
    log("   [WAIT] Probing for Story Mode (Spamming ESC)...")
    start_time = time.time()
    while time.time() - start_time < CONFIG.STORY_MODE_TIMEOUT:
        check_panic_key()
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.1):
            log("   [SUCCESS] Story Mode Menu Detected.")
            return True
        pydirectinput.press('esc')
        time.sleep(1.2)
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.2):
            log("   [SUCCESS] Story Mode Menu Detected (After Press).")
            return True
        if find_image("first_letter_of_quit_screen.png", timeout=0.2):
            log("   [FIX] Stuck on Quit screen. Confirming...")
            pydirectinput.press('enter')
            time.sleep(5)
            
    log("[CRITICAL] Story Mode load timed out.")
    return False

def ensure_story_mode():
    log("\n--- STATE CHECK: Transitioning to Story Mode ---")
    pydirectinput.keyDown('alt')
    time.sleep(0.1)
    pydirectinput.keyDown('f6') # Default to Trevor/F6 as per Script A
    time.sleep(0.1)
    pydirectinput.keyUp('f6')
    time.sleep(0.1)
    pydirectinput.keyUp('alt')
    
    if find_image("first_letter_of_quit_screen.png", timeout=5, click=False, crash_if_missing=True):
        pydirectinput.press('enter')
    
    if confirm_story_mode_spawn():
        FirewallManager.unblock()

def go_story_to_online():
    log("\n--- TRANSITION: Story -> Online ---")
    if not find_image("online_button.png", timeout=1.0, click=False):
        log("   [NAV] Opening Pause Menu...")
        pydirectinput.press('esc')
        time.sleep(1.0)
    
    find_image("online_button.png", timeout=5, click=True, crash_if_missing=True)
    time.sleep(0.5)

    log("   [NAV] Selecting 'Play GTA Online'...")
    pydirectinput.press('up')   
    time.sleep(0.1)
    pydirectinput.press('enter') 
    time.sleep(1.0)
    
    # Specific retry loop
    if not find_image("closed_friend_session.png", timeout=5, click=True):
        log("[ERROR] 'Closed Friend Session' not found. We might be in the wrong menu.")
        log("[FIX] Backing out and retrying...")
        fast_press('esc', count=4) 
        time.sleep(1.0)
        go_story_to_online()
        return

    pydirectinput.press('enter')
    
    if find_image("first_letter_of_quit_screen.png", timeout=5):
        pydirectinput.press('enter')
        
    log("   [WAIT] Waiting for Load...")
    loading_timeout = time.time() + CONFIG.ONLINE_LOAD_TIMEOUT
    
    while time.time() < loading_timeout:
        check_panic_key()
        if find_image("joining_gta_online.png", region_name="BOTTOM_RIGHT", timeout=0.1):
            time.sleep(0.5)
            continue
        if find_image("map_north.png", region_name="HUD_AREA", timeout=0.1):
            log("\n   [SUCCESS] Minimap detected! We are spawned.")
            break
        time.sleep(0.5)
    log("   [LOADED] Spawn Confirmed. Starting immediately.")
    time.sleep(0.5)

def recover_and_reset_filters():
    log("   [RECOVERY] Backing out to list...")
    pydirectinput.mouseDown(button='right')
    time.sleep(0.1)
    pydirectinput.mouseUp(button='right')
    time.sleep(1.0) 
    
    log("   [RECOVERY] Resetting Filters...")
    find_image("web_dynasty_high_to_low.png", region_name="BROWSER_MAIN", timeout=2, click=True)
    time.sleep(0.2)
    find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=2, click=True)
    time.sleep(0.5)
    update_stats(errors=1)

def open_phone_browser():
    log("   [NAV] Opening Phone...")
    pydirectinput.press('up')
    
    phone_confirmed = False
    for attempt in range(2):
        if find_image("phone_browser_icon.png", region_name="ALL", timeout=2.0):
            phone_confirmed = True
            log("   [NAV] Phone Open Confirmed.")
            break
        else:
            log(f"   [WARN] Phone icon not visible (Attempt {attempt+1}). Retrying Input...")
            pydirectinput.press('up')
            time.sleep(0.5)
            
    if not phone_confirmed:
        log("[ERR] Phone verification failed. Proceeding blindly.")
    
    time.sleep(0.5)
    pydirectinput.press('down')
    time.sleep(0.2)
    pydirectinput.press('enter')
    time.sleep(1.0)

def batch_buy_routine():
    log("\n--- PHASE: Batch Buy (10 Slots) ---")
    
    open_phone_browser()

    find_image("eyefind_logo.png", timeout=5, crash_if_missing=True)
    find_image("web_browser_input_field.png", region_name="BROWSER_MAIN", timeout=5, click=True, crash_if_missing=True)
    
    time.sleep(0.5) 
    safe_type("www.dynasty8realestate.com") 
    time.sleep(0.2)
    pydirectinput.press('enter')
    
    log("[WAIT] 1.0s for keyboard animation...")
    time.sleep(1.0) 
    
    find_image("web_browser_view_property_listings.png", region_name="BROWSER_MAIN", timeout=10, click=True, wait_after=1.0, crash_if_missing=True)
    
    if not find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=8, click=True):
        log("[CRITICAL ERROR] 'Low to High' filter not found.")
        sys.exit()

    time.sleep(0.5)

    FirewallManager.block()
    time.sleep(1.0) 
    
    properties_bought = 0

    for current_slot in range(10):
        log(f"   [SLOT {current_slot+1}/10]")
        check_panic_key()
        
        max_retries = 3
        success = False
        
        # Strict logic loop
        for attempt in range(max_retries):
            if not find_image("web_dynasty_car_icon_black.png", region_name="BROWSER_MAIN", timeout=3, click=True, override_confidence=0.8):
                log("   [WARN] Car icon not found (Strict Mode). Recovery...")
                recover_and_reset_filters()
                continue 

            if find_image("web_dynasty_buy_property.png", region_name="BROWSER_MAIN", timeout=4, click=True, override_confidence=0.8):
                success = True
                break 
            else:
                log(f"   [WARN] Buy button NOT found (Attempt {attempt+1}). Wrong apt?")
                recover_and_reset_filters()
        
        if not success:
            log("[CRITICAL] Failed to buy slot. Exiting.")
            sys.exit()

        if find_image("trade_in_property_menu.png", region_name="ALL", timeout=5, crash_if_missing=True):
            if current_slot > 0:
                fast_press('down', count=current_slot)
            
            pydirectinput.press('enter')
            time.sleep(0.2)
            pydirectinput.press('enter')
            time.sleep(0.5)
            
            # Logic from Script A regarding map return
            if find_image("web_dynasty_return_to_map.png", region_name="BROWSER_MAIN", timeout=60, click=True):
                time.sleep(0.2)
                find_image("web_dynasty_high_to_low.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1)
                find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1)
                properties_bought += 1
            else:
                log("   [ERROR] 'Return to Map' not found.")
                sys.exit()

    log("   [EXIT] Batch Complete.")
    update_stats(properties=properties_bought)
    
    # Close browser
    while True:
        for _ in range(9):
            pydirectinput.mouseDown(button='right')
            time.sleep(0.02)
            pydirectinput.mouseUp(button='right')
            time.sleep(0.03)
            
        if find_image("map_north.png", region_name="HUD_AREA", timeout=1.0):
            log("   [SUCCESS] Browser Closed.")
            break

    log("   [EXIT] Attempting to reach Story Mode...")
    ensure_story_mode() 

def force_save_logic():
    log("   [SAVE] Forcing Game Save...")
    pydirectinput.press('m')
    time.sleep(0.5) 
    find_image("interaction_menu_appearance_entry.png", timeout=5, click=True)
    pydirectinput.press('enter')
    find_image("interaction_menu_accessories_entry.png", timeout=5, click=True)
    pydirectinput.press('enter')
    find_image("interaction_menu_hats_entry.png", timeout=5, click=True)
    time.sleep(0.2)
    pydirectinput.press('enter')
    time.sleep(0.2)
    fast_press('esc', count=3)
    log("   [WAIT] Saving (2.0s)...")
    time.sleep(2.0) 

# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    setup_logging()
    FirewallManager.unblock()
    load_stats()
    
    print("==========================================")
    print("   GTA ONLINE GLITCHER (V14 MERGED)")
    print(f"   Total Loops: {STATS['total_loops_completed']}")
    print(f"   Properties: {STATS['total_properties_bought']}")
    print("==========================================")

    find_game_window()
    load_assets_into_ram()
    focus_console()
    
    try:
        total_loops = int(input("Loops? "))
    except ValueError:
        total_loops = 1

    print("\nWhere are you starting?")
    print("1. Story Mode")
    print("2. Already Online")
    start_choice = input("Choice (1/2): ")

    print(f"\nPress {CONFIG.START_KEY.upper()} to START. ('{CONFIG.PANIC_KEY.upper()}' to STOP)")
    keyboard.wait(CONFIG.START_KEY) 
    
    if GAME_WINDOW:
        try:
            GAME_WINDOW.activate()
        except: pass
            
    start_time = time.time()
    STATS["session_start"] = datetime.now().isoformat()
    
    if start_choice == "2":
        log("[START] Skipping first transition (Already Online).")
    else:
        go_story_to_online()
    
    for i in range(total_loops):
        log(f"\n>>> LOOP {i+1} / {total_loops} <<<")
        try:
            batch_buy_routine()
            go_story_to_online()
            force_save_logic()
            update_stats(loops=1)
        except Exception as e:
            log_error(f"Loop failed: {e}")
            FirewallManager.unblock()
        
    log(f"=== COMPLETED ===")
    save_stats()