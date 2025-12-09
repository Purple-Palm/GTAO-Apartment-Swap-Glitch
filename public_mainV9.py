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
from datetime import datetime

CONFIDENCE = 0.8
BLOCKED_IPS = "192.81.241.170-192.81.241.171"
RULE_NAME = "GTAOSAVEBLOCK"

pydirectinput.FAILSAFE = True 

if not os.path.exists("debug_errors"):
    os.makedirs("debug_errors")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("gta_debug.log", mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(msg):
    logging.info(msg)

def log_debug(msg):
    logging.debug(msg)


ASSET_CACHE = {}
sct = mss.mss()

def load_assets_into_ram():
    log("[INIT] Loading assets into RAM...")
    if not os.path.exists("assets"):
        log("[ERROR] 'assets' folder not found!")
        sys.exit()
        
    loaded_count = 0
    for filename in os.listdir("assets"):
        if filename.endswith(".png"):
            path = os.path.join("assets", filename)
            img = cv2.imread(path, 0) 
            if img is not None:
                ASSET_CACHE[filename] = img
                loaded_count += 1
            else:
                log(f"[WARN] Failed to load {filename}")
    
    log(f"[INIT] {loaded_count} assets cached in memory.")

def get_screen_resolution():
    return pyautogui.size()

w, h = get_screen_resolution()
log(f"[INIT] Screen Resolution detected: {w}x{h}")

ROIS = {
    "ALL": {"top": 0, "left": 0, "width": w, "height": h},
    "BROWSER_MAIN": {"top": 0, "left": 0, "width": w, "height": h},
    "HUD_AREA": {"top": int(h * 0.7), "left": 0, "width": int(w * 0.3), "height": int(h * 0.3)},
    "BOTTOM_RIGHT": {"top": int(h * 0.7), "left": int(w * 0.7), "width": int(w * 0.3), "height": int(h * 0.3)}
}


def toggle_firewall(block=False):
    if block:
        log("[FIREWALL] BLOCKING Connection...")
        cmd = f'netsh advfirewall firewall add rule name="{RULE_NAME}" dir=out action=block remoteip={BLOCKED_IPS} enable=yes'
    else:
        log("[FIREWALL] RESTORING Connection...")
        cmd = f'netsh advfirewall firewall delete rule name="{RULE_NAME}"'
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def clean_exit():
    toggle_firewall(block=False)

atexit.register(clean_exit)

def fast_press(key, count=1):
    for _ in range(count):
        pydirectinput.keyDown(key)
        time.sleep(0.02) 
        pydirectinput.keyUp(key)
        time.sleep(0.03) 

def find_image(image_name, region_name="ALL", timeout=5, click=False, wait_after=0.1, crash_if_missing=False):
    start = time.time()
    template = ASSET_CACHE.get(image_name)
    if template is None:
        log(f"[ERROR] Asset '{image_name}' not found!")
        sys.exit()

    region = ROIS.get(region_name, ROIS["ALL"])
    
    if "buy" in image_name or "online" in image_name:
        log_debug(f"Scanning for '{image_name}' in {region_name}...")

    best_val_seen = 0.0

    while time.time() - start < timeout:
        if keyboard.is_pressed('q'):
            log("\n[PANIC] 'Q' Pressed. Exiting.")
            sys.exit()

        try:
            img_grab = sct.grab(region)
            img_np = np.array(img_grab)
            screen_gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_val_seen:
                best_val_seen = max_val

            if max_val >= CONFIDENCE:
                if click:
                    h_img, w_img = template.shape[:2]
                    rx, ry = max_loc
                    global_x = rx + region['left'] + (w_img // 2)
                    global_y = ry + region['top'] + (h_img // 2)
                    
                    log(f"[ACTION] Clicking '{image_name}' at ({global_x}, {global_y})")
                    pydirectinput.moveTo(global_x, global_y) 
                    pydirectinput.mouseDown()
                    time.sleep(0.06) 
                    pydirectinput.mouseUp()
                
                time.sleep(wait_after)
                return True
        except Exception as e:
            pass
        time.sleep(0.01) 
    
    
    if crash_if_missing:
        timestamp = datetime.now().strftime("%H-%M-%S")
        err_filename = f"debug_errors/FAIL_{image_name}_{timestamp}.png"
        fail_grab = sct.grab(region)
        mss.tools.to_png(fail_grab.rgb, fail_grab.size, output=err_filename)
        log(f"[CRITICAL] Dumped failure screenshot to {err_filename}")
        log("[CRITICAL] Exiting safely.")
        toggle_firewall(block=False)
        sys.exit()
        
    return False


def confirm_story_mode_spawn():
    log("   [WAIT] Probing for Story Mode...")
    
    start_time = time.time()
    while time.time() - start_time < 120:
        
        # 1. Check if we are ALREADY in the menu
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.1):
            log("   [SUCCESS] Story Mode Menu Detected.")
            return True

        # 2. Press ESC to try and open it
        pydirectinput.press('esc')
        
        # 3. Wait for animation
        time.sleep(1.2)
        
        # 4. Check again
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.2):
            log("   [SUCCESS] Story Mode Menu Detected (After Press).")
            return True
            
        # 5. Safety
        if find_image("first_letter_of_quit_screen.png", timeout=0.2):
            log("   [FIX] Stuck on Quit screen. Confirming...")
            pydirectinput.press('enter')
            time.sleep(5)
            
    log("[CRITICAL] Story Mode load timed out.")
    return False

def ensure_story_mode():
    log("\n--- STATE CHECK: Transitioning to Story Mode ---")
    
    # 1. Quitting via char. wheel
    pydirectinput.keyDown('alt')
    time.sleep(0.1)
    pydirectinput.keyDown('f6')
    time.sleep(0.1)
    pydirectinput.keyUp('f6')
    time.sleep(0.1)
    pydirectinput.keyUp('alt')
    
    # 2. Checking for confirm. screen
    if find_image("first_letter_of_quit_screen.png", timeout=5, click=False, crash_if_missing=True):
        pydirectinput.press('enter')
    
    # 3. Confirming story mode spawn
    confirm_story_mode_spawn()
    
    # 4. Restore internet to ensure clean state for next loop
    toggle_firewall(block=False) 

def go_story_to_online():
    log("\n--- TRANSITION: Story -> Online ---")
    
    # 1. Open menu
    if not find_image("online_button.png", timeout=1.0, click=False):
        log("   [NAV] Opening Pause Menu...")
        pydirectinput.press('esc')
        time.sleep(1.0)
    
    # 2. Click online
    find_image("online_button.png", timeout=5, click=True, crash_if_missing=True)
    time.sleep(0.5)

    log("   [NAV] Selecting 'Play GTA Online'...")
    pydirectinput.press('up')   
    time.sleep(0.1)
    pydirectinput.press('enter') 
    time.sleep(1.0)
    
    # 3. Verify menu state
    if not find_image("closed_friend_session.png", timeout=5, click=True):
        log("[ERROR] 'Closed Friend Session' not found. We might be in the wrong menu.")
        log("[FIX] Backing out and retrying...")
        fast_press('esc', count=4) 
        time.sleep(1.0)
        go_story_to_online()
        return

    pydirectinput.press('enter')
    
    # 4. Check for quit confirmation
    if find_image("first_letter_of_quit_screen.png", timeout=5):
        pydirectinput.press('enter')
        
    log("   [WAIT] Waiting for Load...")
    loading_timeout = time.time() + 180 
    
    while time.time() < loading_timeout:
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

def batch_buy_routine():
    log("\n--- PHASE: Batch Buy (10 Slots) ---")
    pydirectinput.press('up')
    time.sleep(0.5)
    pydirectinput.press('down')
    time.sleep(0.1)
    pydirectinput.press('enter')
    time.sleep(1.0)

    find_image("eyefind_logo.png", timeout=5, crash_if_missing=True)
    find_image("web_browser_input_field.png", region_name="BROWSER_MAIN", timeout=5, click=True, crash_if_missing=True)
    
    time.sleep(0.5) 
    pydirectinput.write("www.dynasty8realestate.com", interval=0.01) 
    time.sleep(0.2)
    pydirectinput.press('enter')
    
    log("[WAIT] 1.0s for keyboard animation...")
    time.sleep(1.0) 
    
    find_image("web_browser_view_property_listings.png", region_name="BROWSER_MAIN", timeout=10, click=True, wait_after=1.0, crash_if_missing=True)
    
    if not find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=8, click=True):
        log("[CRITICAL ERROR] 'Low to High' filter not found.")
        sys.exit()

    time.sleep(0.5)

    toggle_firewall(block=True)
    time.sleep(1.0) 
    
    for current_slot in range(10):
        log(f"   [SLOT {current_slot+1}/10]")
        
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            # 1. Select property
            if not find_image("web_dynasty_car_icon_black.png", region_name="BROWSER_MAIN", timeout=3, click=True):
                log("   [WARN] Car icon not found. Recovery...")
                recover_and_reset_filters()
                continue 

            # 2. Check for buy button
            if find_image("web_dynasty_buy_property.png", region_name="BROWSER_MAIN", timeout=4, click=True):
                success = True
                break 
            else:
                log(f"   [WARN] Buy button NOT found (Attempt {attempt+1}). Wrong apt?")
                recover_and_reset_filters()
        
        if not success:
            log("[CRITICAL] Failed to buy slot. Exiting.")
            sys.exit()

        # 3. Trade in
        if find_image("trade_in_property_menu.png", region_name="ALL", timeout=5, crash_if_missing=True):
            if current_slot > 0:
                fast_press('down', count=current_slot)
            
            pydirectinput.press('enter')
            time.sleep(0.2)
            pydirectinput.press('enter')
            time.sleep(0.5)
            
            # 4. Return to map
            if find_image("web_dynasty_return_to_map.png", region_name="BROWSER_MAIN", timeout=60, click=True):
                time.sleep(0.2)
                # Reset filters
                find_image("web_dynasty_high_to_low.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1)
                find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1)
            else:
                log("   [ERROR] 'Return to Map' not found.")
                sys.exit()

    log("   [EXIT] Batch Complete.")
    
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

if __name__ == "__main__":
    toggle_firewall(False)
    load_assets_into_ram()
    print("==========================================")
    print("        GTA ONLINE GLITCHER (V9)          ")
    print("==========================================")
    
    try:
        total_loops = int(input("Loops? "))
    except ValueError:
        total_loops = 1

    print("\nWhere are you starting?")
    print("1. Story Mode")
    print("2. Already Online(Invite/Friend Only)")
    start_choice = input("Choice (1/2): ")

    print("\nPress F1 to START. ('q' to STOP)")
    keyboard.wait('f1') 
    
    start_time = time.time()
    
    if start_choice == "2":
        log("[START] Skipping first transition (Already Online).")
    else:
        go_story_to_online()
    
    for i in range(total_loops):
        log(f"\n>>> LOOP {i+1} / {total_loops} <<<")
        batch_buy_routine()
        go_story_to_online()
        force_save_logic()
        
    log(f"=== COMPLETED ===")