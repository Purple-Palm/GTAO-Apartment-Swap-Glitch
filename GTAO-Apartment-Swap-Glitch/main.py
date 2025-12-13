"""
GTA Online Apartment Swap Glitch Automation
Version: 10.0
"""

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
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from pathlib import Path
from enum import Enum, auto

# ==================== CONFIGURATION ====================

@dataclass
class Config:
    """Configuration centralisée du script"""
    CONFIDENCE: float = 0.8
    BLOCKED_IPS: str = "192.81.241.170-192.81.241.171"
    RULE_NAME: str = "GTAOSAVEBLOCK"
    PANIC_KEY: str = 'q'
    START_KEY: str = 'f1'
    
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
    CONFIG_FILE: Path = Path("config.json")
    STATS_FILE: Path = Path("stats.json")


class GameState(Enum):
    """États possibles du jeu"""
    UNKNOWN = auto()
    STORY_MODE = auto()
    ONLINE = auto()
    LOADING = auto()
    BROWSER_OPEN = auto()
    MENU_OPEN = auto()


# ==================== GLOBALS ====================

CONFIG = Config()
ASSET_CACHE: Dict[str, np.ndarray] = {}
sct = mss.mss()
pydirectinput.FAILSAFE = True

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
    """Configure le système de logging"""
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
    """Charge les statistiques depuis le fichier"""
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
    """Sauvegarde les statistiques"""
    STATS["last_run"] = datetime.now().isoformat()
    try:
        with open(CONFIG.STATS_FILE, 'w') as f:
            json.dump(STATS, f, indent=2)
    except Exception as e:
        log_warning(f"[STATS] Could not save stats: {e}")

def update_stats(loops: int = 0, properties: int = 0, errors: int = 0):
    """Met à jour les statistiques"""
    STATS["total_loops_completed"] += loops
    STATS["total_properties_bought"] += properties
    STATS["errors_recovered"] += errors
    save_stats()


# ==================== SCREEN & ROI ====================

def get_screen_resolution() -> Tuple[int, int]:
    """Récupère la résolution de l'écran"""
    return pyautogui.size()

def calculate_rois(w: int, h: int) -> Dict[str, dict]:
    """Calcule les régions d'intérêt basées sur la résolution"""
    return {
        "ALL": {"top": 0, "left": 0, "width": w, "height": h},
        "BROWSER_MAIN": {"top": 0, "left": 0, "width": w, "height": h},
        "HUD_AREA": {"top": int(h * 0.7), "left": 0, "width": int(w * 0.3), "height": int(h * 0.3)},
        "BOTTOM_RIGHT": {"top": int(h * 0.7), "left": int(w * 0.7), "width": int(w * 0.3), "height": int(h * 0.3)},
        "CENTER": {"top": int(h * 0.3), "left": int(w * 0.3), "width": int(w * 0.4), "height": int(h * 0.4)},
        "TOP_HALF": {"top": 0, "left": 0, "width": w, "height": int(h * 0.5)},
    }


# ==================== ASSET MANAGEMENT ====================

def load_assets_into_ram() -> bool:
    """Charge tous les assets PNG en mémoire"""
    log("[INIT] Loading assets into RAM...")
    
    if not CONFIG.ASSETS_DIR.exists():
        log_error(f"[ERROR] '{CONFIG.ASSETS_DIR}' folder not found!")
        return False
    
    loaded_count = 0
    failed_assets = []
    
    for filepath in CONFIG.ASSETS_DIR.glob("*.png"):
        img = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            ASSET_CACHE[filepath.name] = img
            loaded_count += 1
        else:
            failed_assets.append(filepath.name)
            log_warning(f"[WARN] Failed to load {filepath.name}")
    
    log(f"[INIT] {loaded_count} assets cached in memory.")
    
    if failed_assets:
        log_warning(f"[WARN] Failed assets: {', '.join(failed_assets)}")
    
    return loaded_count > 0

def validate_required_assets() -> bool:
    """Vérifie que tous les assets requis sont chargés"""
    required = [
        "pause_menu_text_grand_theft_auto_v.png",
        "online_button.png",
        "closed_friend_session.png",
        "map_north.png",
        "eyefind_logo.png",
        "web_browser_input_field.png",
        "web_browser_view_property_listings.png",
        "web_dynasty_low_to_high.png",
        "web_dynasty_car_icon_black.png",
        "web_dynasty_buy_property.png",
        "trade_in_property_menu.png",
        "web_dynasty_return_to_map.png",
    ]
    
    missing = [asset for asset in required if asset not in ASSET_CACHE]
    
    if missing:
        log_error(f"[ERROR] Missing required assets: {', '.join(missing)}")
        return False
    
    log("[INIT] All required assets validated.")
    return True


# ==================== FIREWALL MANAGEMENT ====================

class FirewallManager:
    """Gère les règles de pare-feu"""
    
    _is_blocked: bool = False
    
    @classmethod
    def block(cls) -> bool:
        """Bloque la connexion aux serveurs Rockstar"""
        if cls._is_blocked:
            log_debug("[FIREWALL] Already blocked.")
            return True
            
        log("[FIREWALL] BLOCKING Connection...")
        cmd = f'netsh advfirewall firewall add rule name="{CONFIG.RULE_NAME}" dir=out action=block remoteip={CONFIG.BLOCKED_IPS} enable=yes'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        
        if result.returncode == 0:
            cls._is_blocked = True
            return True
        else:
            log_error(f"[FIREWALL] Failed to block: {result.stderr.decode()}")
            return False
    
    @classmethod
    def unblock(cls) -> bool:
        """Restaure la connexion"""
        log("[FIREWALL] RESTORING Connection...")
        cmd = f'netsh advfirewall firewall delete rule name="{CONFIG.RULE_NAME}"'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        cls._is_blocked = False
        return True
    
    @classmethod
    def is_blocked(cls) -> bool:
        return cls._is_blocked


def clean_exit():
    """Nettoyage à la sortie du script"""
    log("[EXIT] Cleaning up...")
    FirewallManager.unblock()
    save_stats()

atexit.register(clean_exit)


# ==================== INPUT HELPERS ====================

def check_panic_key() -> bool:
    """Vérifie si la touche de panique est pressée"""
    if keyboard.is_pressed(CONFIG.PANIC_KEY):
        log(f"\n[PANIC] '{CONFIG.PANIC_KEY.upper()}' Pressed. Emergency Exit!")
        FirewallManager.unblock()
        save_stats()
        sys.exit(0)
    return False

def fast_press(key: str, count: int = 1, delay_between: float = 0.05):
    """Appuie rapidement sur une touche plusieurs fois"""
    for _ in range(count):
        check_panic_key()
        pydirectinput.keyDown(key)
        time.sleep(CONFIG.KEY_PRESS_DOWN)
        pydirectinput.keyUp(key)
        time.sleep(CONFIG.KEY_PRESS_UP)
        if count > 1:
            time.sleep(delay_between)

def safe_click(x: int, y: int):
    """Click sécurisé avec vérification"""
    check_panic_key()
    pydirectinput.moveTo(x, y)
    pydirectinput.mouseDown()
    time.sleep(CONFIG.MOUSE_CLICK_DURATION)
    pydirectinput.mouseUp()

def safe_type(text: str, delay: float = 0.05):
    """
    Tape du texte caractère par caractère avec pydirectinput.
    Utilise un mapping AZERTY pour corriger les touches.
    """
    check_panic_key()
    log(f"[TYPE] Typing: {text}")
    
    # Mapping QWERTY → AZERTY
    # Pour taper le caractère de gauche, on appuie sur la touche de droite
    # Car pydirectinput envoie la position physique QWERTY
    qwerty_to_azerty = {
        'a': 'q',  # Pour taper 'a', appuyer sur 'q' (position AZERTY de 'a')
        'q': 'a',  # Pour taper 'q', appuyer sur 'a'
        'z': 'w',  # Pour taper 'z', appuyer sur 'w'
        'w': 'z',  # Pour taper 'w', appuyer sur 'z'
        'm': ';',  # Pour taper 'm', appuyer sur ';' (dépend du layout exact)
        '.': ':',  # Point sur AZERTY = Shift+; ou touche dédiée
        ',': 'm',  # Virgule
    }
    
    # Caractères spéciaux
    special_keys = {
        '.': ';',      # Le point est sur la touche ; en AZERTY (shift+,)
        '/': '/',      # Slash (peut varier)
        '-': '-',
        ' ': 'space',
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
        '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    }
    
    for char in text:
        check_panic_key()
        lower_char = char.lower()
        
        # Déterminer quelle touche appuyer
        if lower_char in qwerty_to_azerty:
            key_to_press = qwerty_to_azerty[lower_char]
        elif char in special_keys:
            key_to_press = special_keys[char]
        else:
            key_to_press = lower_char
        
        # Gérer les majuscules
        if char.isupper():
            pydirectinput.keyDown('shift')
            time.sleep(0.02)
            pydirectinput.press(key_to_press)
            time.sleep(0.02)
            pydirectinput.keyUp('shift')
        elif key_to_press == 'space':
            pydirectinput.press('space')
        elif char == '.':
            # Point en AZERTY = Shift + , (virgule)
            # La touche virgule QWERTY correspond à la bonne position
            pydirectinput.keyDown('shift')
            time.sleep(0.02)
            pydirectinput.press(',')
            time.sleep(0.02)
            pydirectinput.keyUp('shift')
        elif char.isdigit():
            # En AZERTY, les chiffres nécessitent Shift
            pydirectinput.keyDown('shift')
            time.sleep(0.02)
            pydirectinput.press(char)
            time.sleep(0.02)
            pydirectinput.keyUp('shift')
        else:
            pydirectinput.press(key_to_press)
        
        time.sleep(delay)
    
    time.sleep(0.1)


# ==================== IMAGE DETECTION ====================

def find_image(
    image_name: str, 
    region_name: str = "ALL", 
    timeout: float = 5, 
    click: bool = False, 
    wait_after: float = 0.1, 
    crash_if_missing: bool = False,
    log_search: bool = True
) -> bool:
    """
    Recherche une image sur l'écran avec correspondance de template.
    
    Args:
        image_name: Nom du fichier image dans le cache
        region_name: Région de l'écran à scanner
        timeout: Temps maximum de recherche
        click: Cliquer sur l'image si trouvée
        wait_after: Délai après action
        crash_if_missing: Quitter si l'image n'est pas trouvée
        log_search: Logger la recherche
    
    Returns:
        True si l'image est trouvée, False sinon
    """
    start = time.time()
    template = ASSET_CACHE.get(image_name)
    
    if template is None:
        log_error(f"[ERROR] Asset '{image_name}' not found in cache!")
        if crash_if_missing:
            sys.exit(1)
        return False

    # Initialiser les ROIs si nécessaire
    w, h = get_screen_resolution()
    ROIS = calculate_rois(w, h)
    region = ROIS.get(region_name, ROIS["ALL"])
    
    if log_search and ("buy" in image_name.lower() or "online" in image_name.lower()):
        log_debug(f"Scanning for '{image_name}' in {region_name}...")

    best_val_seen = 0.0

    while time.time() - start < timeout:
        check_panic_key()

        try:
            img_grab = sct.grab(region)
            img_np = np.array(img_grab)
            screen_gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            best_val_seen = max(best_val_seen, max_val)

            if max_val >= CONFIG.CONFIDENCE:
                if click:
                    h_img, w_img = template.shape[:2]
                    rx, ry = max_loc
                    global_x = rx + region['left'] + (w_img // 2)
                    global_y = ry + region['top'] + (h_img // 2)
                    
                    log(f"[ACTION] Clicking '{image_name}' at ({global_x}, {global_y}) [conf: {max_val:.2f}]")
                    safe_click(global_x, global_y)
                
                time.sleep(wait_after)
                return True
                
        except Exception as e:
            log_debug(f"[SCAN ERROR] {e}")
            
        time.sleep(CONFIG.SCAN_INTERVAL)
    
    # Timeout atteint
    if crash_if_missing:
        dump_failure_screenshot(image_name, region)
        log_error(f"[CRITICAL] '{image_name}' not found after {timeout}s (best: {best_val_seen:.2f})")
        FirewallManager.unblock()
        sys.exit(1)
    
    if best_val_seen > 0.5:
        log_debug(f"[MISS] '{image_name}' not found (best: {best_val_seen:.2f})")
        
    return False

def dump_failure_screenshot(image_name: str, region: dict):
    """Sauvegarde une capture d'écran en cas d'échec"""
    timestamp = datetime.now().strftime("%H-%M-%S")
    err_filename = CONFIG.DEBUG_DIR / f"FAIL_{image_name}_{timestamp}.png"
    
    try:
        fail_grab = sct.grab(region)
        mss.tools.to_png(fail_grab.rgb, fail_grab.size, output=str(err_filename))
        log(f"[DEBUG] Failure screenshot saved: {err_filename}")
    except Exception as e:
        log_error(f"[DEBUG] Failed to save screenshot: {e}")


# ==================== GAME STATE DETECTION ====================

def detect_game_state() -> GameState:
    """Détecte l'état actuel du jeu"""
    
    # Vérifier si en Story Mode (menu pause)
    if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.3, log_search=False):
        return GameState.STORY_MODE
    
    # Vérifier si online (minimap visible)
    if find_image("map_north.png", region_name="HUD_AREA", timeout=0.3, log_search=False):
        return GameState.ONLINE
    
    # Vérifier si navigateur ouvert
    if find_image("eyefind_logo.png", timeout=0.3, log_search=False):
        return GameState.BROWSER_OPEN
    
    # Vérifier si en chargement
    if find_image("joining_gta_online.png", region_name="BOTTOM_RIGHT", timeout=0.3, log_search=False):
        return GameState.LOADING
    
    return GameState.UNKNOWN


# ==================== GAME TRANSITIONS ====================

def confirm_story_mode_spawn() -> bool:
    """Confirme que le jeu est bien en mode Histoire"""
    log("   [WAIT] Probing for Story Mode...")
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < CONFIG.STORY_MODE_TIMEOUT:
        check_panic_key()
        attempts += 1
        
        # Vérifier si déjà dans le menu
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.2, log_search=False):
            log(f"   [SUCCESS] Story Mode Menu Detected (attempt {attempts})")
            return True

        # Appuyer sur ESC pour ouvrir le menu
        pydirectinput.press('esc')
        time.sleep(1.2)
        
        # Revérifier
        if find_image("pause_menu_text_grand_theft_auto_v.png", timeout=0.3, log_search=False):
            log(f"   [SUCCESS] Story Mode Menu Detected after ESC (attempt {attempts})")
            return True
        
        # Gérer l'écran de confirmation de quitter
        if find_image("first_letter_of_quit_screen.png", timeout=0.2, log_search=False):
            log("   [FIX] Stuck on Quit screen. Confirming...")
            pydirectinput.press('enter')
            time.sleep(5)
    
    log_error("[CRITICAL] Story Mode load timed out.")
    return False

def ensure_story_mode():
    """Assure la transition vers le mode Histoire"""
    log("\n--- STATE CHECK: Transitioning to Story Mode ---")
    
    # Quitter via la roue des personnages
    # Alt+F5 = Franklin (toujours disponible dès le début)
    # Alt+F4 = Michael, Alt+F6 = Trevor (débloqué plus tard)
    pydirectinput.keyDown('alt')
    time.sleep(0.1)
    pydirectinput.keyDown('f5')  # Franklin
    time.sleep(0.1)
    pydirectinput.keyUp('f5')
    time.sleep(0.1)
    pydirectinput.keyUp('alt')
    
    # Attendre l'écran de confirmation
    if find_image("first_letter_of_quit_screen.png", timeout=5, crash_if_missing=True):
        pydirectinput.press('enter')
    
    # Confirmer le spawn en Story Mode
    success = confirm_story_mode_spawn()
    
    if success:
        # Restaurer la connexion seulement si on est bien en Story Mode
        FirewallManager.unblock()
    else:
        log_error("[ERROR] Failed to confirm Story Mode spawn - KEEPING FIREWALL BLOCKED!")
        log_error("[ERROR] Les achats ne seront PAS sauvegardés tant que le firewall bloque.")
        update_stats(errors=1)

def go_story_to_online():
    """Transition du mode Histoire vers Online"""
    log("\n--- TRANSITION: Story -> Online ---")
    
    # Ouvrir le menu si nécessaire
    if not find_image("online_button.png", timeout=1.0, log_search=False):
        log("   [NAV] Opening Pause Menu...")
        pydirectinput.press('esc')
        time.sleep(1.0)
    
    # Cliquer sur Online
    if not find_image("online_button.png", timeout=5, click=True, crash_if_missing=True):
        return
    
    time.sleep(0.5)

    log("   [NAV] Selecting 'Play GTA Online'...")
    pydirectinput.press('up')
    time.sleep(0.1)
    pydirectinput.press('enter')
    time.sleep(1.0)
    
    # Sélectionner le type de session
    max_retries = 3
    for attempt in range(max_retries):
        if find_image("closed_friend_session.png", timeout=5, click=True):
            break
        else:
            log_warning(f"[WARN] 'Closed Friend Session' not found (attempt {attempt + 1}/{max_retries})")
            fast_press('esc', count=4)
            time.sleep(1.0)
            
            if attempt < max_retries - 1:
                go_story_to_online()
                return
            else:
                log_error("[ERROR] Failed to find session menu.")
                return

    pydirectinput.press('enter')
    
    # Gérer la confirmation de quitte
    if find_image("first_letter_of_quit_screen.png", timeout=5, log_search=False):
        pydirectinput.press('enter')
    
    # Attendre le chargement
    wait_for_online_load()

def wait_for_online_load():
    """Attend que le joueur soit spawné en ligne"""
    log("   [WAIT] Waiting for Online Load...")
    
    loading_timeout = time.time() + CONFIG.ONLINE_LOAD_TIMEOUT
    last_state = None
    
    while time.time() < loading_timeout:
        check_panic_key()
        
        # Détecter l'état actuel
        if find_image("joining_gta_online.png", region_name="BOTTOM_RIGHT", timeout=0.2, log_search=False):
            if last_state != "loading":
                log_debug("   [STATE] Loading screen detected...")
                last_state = "loading"
            time.sleep(0.5)
            continue
            
        if find_image("map_north.png", region_name="HUD_AREA", timeout=0.2, log_search=False):
            log("\n   [SUCCESS] Minimap detected! Spawn confirmed.")
            time.sleep(0.5)
            return True
        
        time.sleep(0.5)
    
    log_error("[ERROR] Online load timed out!")
    update_stats(errors=1)
    return False


# ==================== BROWSER OPERATIONS ====================

def recover_and_reset_filters():
    """Récupère de l'écran de détails et réinitialise les filtres"""
    log("   [RECOVERY] Backing out to list...")
    
    # Clic droit pour revenir
    pydirectinput.mouseDown(button='right')
    time.sleep(0.1)
    pydirectinput.mouseUp(button='right')
    time.sleep(1.0)
    
    # Réinitialiser les filtres
    log("   [RECOVERY] Resetting Filters...")
    find_image("web_dynasty_high_to_low.png", region_name="BROWSER_MAIN", timeout=2, click=True, log_search=False)
    time.sleep(0.2)
    find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=2, click=True, log_search=False)
    time.sleep(0.5)
    
    update_stats(errors=1)

def close_browser():
    """Ferme le navigateur in-game"""
    log("   [EXIT] Closing browser...")
    
    max_attempts = 15
    for _ in range(max_attempts):
        check_panic_key()
        
        # Spam clic droit pour fermer
        for _ in range(9):
            pydirectinput.mouseDown(button='right')
            time.sleep(0.02)
            pydirectinput.mouseUp(button='right')
            time.sleep(0.03)
        
        # Vérifier si fermé
        if find_image("map_north.png", region_name="HUD_AREA", timeout=1.0, log_search=False):
            log("   [SUCCESS] Browser Closed.")
            return True
    
    log_warning("[WARN] Browser may not be fully closed.")
    return False

def buy_single_property(slot_index: int) -> bool:
    """Achète une seule propriété pour un slot donné"""
    log(f"   [SLOT {slot_index + 1}/10]")
    
    max_retries = 3
    
    for attempt in range(max_retries):
        check_panic_key()
        
        # Sélectionner la propriété
        if not find_image("web_dynasty_car_icon_black.png", region_name="BROWSER_MAIN", timeout=3, click=True):
            log_warning("   [WARN] Car icon not found. Recovering...")
            recover_and_reset_filters()
            continue
        
        # Chercher le bouton acheter
        if find_image("web_dynasty_buy_property.png", region_name="BROWSER_MAIN", timeout=4, click=True):
            return True
        else:
            log_warning(f"   [WARN] Buy button NOT found (Attempt {attempt + 1}/{max_retries}). Wrong apartment?")
            recover_and_reset_filters()
    
    return False

def complete_trade_in(slot_index: int) -> bool:
    """Complète l'échange de propriété"""
    
    if not find_image("trade_in_property_menu.png", region_name="ALL", timeout=5, crash_if_missing=True):
        return False
    
    # Naviguer vers le bon slot
    if slot_index > 0:
        fast_press('down', count=slot_index)
    
    # Confirmer deux fois
    pydirectinput.press('enter')
    time.sleep(0.2)
    pydirectinput.press('enter')
    time.sleep(0.5)
    
    # Retourner à la carte
    if find_image("web_dynasty_return_to_map.png", region_name="BROWSER_MAIN", timeout=60, click=True):
        time.sleep(0.2)
        # Réinitialiser les filtres
        find_image("web_dynasty_high_to_low.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1, log_search=False)
        find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=3, click=True, wait_after=0.1, log_search=False)
        return True
    else:
        log_error("   [ERROR] 'Return to Map' not found.")
        return False

def batch_buy_routine():
    """Routine d'achat en lot de 10 propriétés"""
    log("\n--- PHASE: Batch Buy (10 Slots) ---")
    
    properties_bought = 0
    
    # Navigation initiale
    pydirectinput.press('up')
    time.sleep(0.5)
    pydirectinput.press('down')
    time.sleep(0.1)
    pydirectinput.press('enter')
    time.sleep(1.0)

    # Attendre le navigateur
    if not find_image("eyefind_logo.png", timeout=5, crash_if_missing=True):
        return
    
    if not find_image("web_browser_input_field.png", region_name="BROWSER_MAIN", timeout=5, click=True, crash_if_missing=True):
        return
    
    # Attendre que le clavier virtuel GTA apparaisse
    log("[WAIT] Waiting for keyboard to appear...")
    time.sleep(1.5)
    
    # Taper l'URL
    log("[TYPE] Typing Dynasty8 URL...")
    safe_type("www.dynasty8realestate.com")
    
    # Attendre un peu puis confirmer
    time.sleep(0.3)
    pydirectinput.press('enter')
    
    # Attendre que le clavier se ferme et la page charge
    log("[WAIT] Waiting for page to load...")
    time.sleep(1.5)
    
    # Aller aux listings
    if not find_image("web_browser_view_property_listings.png", region_name="BROWSER_MAIN", timeout=10, click=True, wait_after=1.0, crash_if_missing=True):
        return
    
    # Appliquer le filtre
    if not find_image("web_dynasty_low_to_high.png", region_name="BROWSER_MAIN", timeout=8, click=True):
        log_error("[CRITICAL ERROR] 'Low to High' filter not found.")
        return
    
    time.sleep(0.5)

    # Bloquer la connexion
    FirewallManager.block()
    time.sleep(1.0)
    
    # Acheter les 10 slots
    for current_slot in range(10):
        check_panic_key()
        
        if not buy_single_property(current_slot):
            log_error(f"[CRITICAL] Failed to buy slot {current_slot + 1}. Aborting batch.")
            break
        
        if not complete_trade_in(current_slot):
            log_error(f"[CRITICAL] Failed to complete trade-in for slot {current_slot + 1}.")
            break
        
        properties_bought += 1
    
    log(f"   [BATCH] Completed: {properties_bought}/10 properties bought")
    update_stats(properties=properties_bought)
    
    # Fermer le navigateur
    close_browser()
    
    # Retourner en Story Mode
    log("   [EXIT] Transitioning to Story Mode...")
    ensure_story_mode()


# ==================== SAVE LOGIC ====================

def force_save_logic():
    """Force une sauvegarde via le menu d'interaction"""
    log("   [SAVE] Forcing Game Save...")
    
    # Ouvrir le menu d'interaction
    pydirectinput.press('m')
    time.sleep(0.5)
    
    # Naviguer dans les menus
    steps = [
        ("interaction_menu_appearance_entry.png", "Appearance"),
        ("interaction_menu_accessories_entry.png", "Accessories"),
        ("interaction_menu_hats_entry.png", "Hats"),
    ]
    
    for image, name in steps:
        if find_image(image, timeout=5, click=True):
            pydirectinput.press('enter')
            time.sleep(0.2)
        else:
            log_warning(f"   [WARN] '{name}' not found in interaction menu")
    
    time.sleep(0.2)
    fast_press('esc', count=3)
    
    log("   [WAIT] Saving (2.0s)...")
    time.sleep(2.0)


# ==================== MAIN EXECUTION ====================

def display_banner():
    """Affiche la bannière du script"""
    print("\n" + "=" * 50)
    print("       GTA ONLINE APARTMENT GLITCH (V10)")
    print("=" * 50)
    print(f"  Total Loops: {STATS['total_loops_completed']}")
    print(f"  Properties: {STATS['total_properties_bought']}")
    print(f"  Errors Recovered: {STATS['errors_recovered']}")
    print("=" * 50)

def get_user_input() -> Tuple[int, str]:
    """Récupère les entrées utilisateur"""
    try:
        total_loops = int(input("\nNumber of loops to run: "))
    except ValueError:
        log_warning("[WARN] Invalid input, defaulting to 1 loop.")
        total_loops = 1

    print("\nWhere are you starting?")
    print("  1. Story Mode")
    print("  2. Already Online (Invite/Friend Only)")
    start_choice = input("Choice (1/2): ").strip()
    
    return total_loops, start_choice

def run_main_loop(total_loops: int, start_online: bool):
    """Boucle principale d'exécution"""
    start_time = time.time()
    STATS["session_start"] = datetime.now().isoformat()
    
    # Skip la première transition si déjà online
    if start_online:
        log("[START] Skipping first transition (Already Online).")
    else:
        go_story_to_online()
    
    # Boucle principale
    for i in range(total_loops):
        check_panic_key()
        
        log(f"\n{'=' * 20} LOOP {i + 1} / {total_loops} {'=' * 20}")
        
        try:
            batch_buy_routine()
            go_story_to_online()
            force_save_logic()
            
            update_stats(loops=1)
            
            elapsed = time.time() - start_time
            avg_per_loop = elapsed / (i + 1)
            remaining = (total_loops - i - 1) * avg_per_loop
            
            log(f"\n[PROGRESS] Loop {i + 1} complete. ETA remaining: {remaining / 60:.1f} min")
            
        except KeyboardInterrupt:
            log("\n[INTERRUPT] User cancelled.")
            break
        except Exception as e:
            log_error(f"[ERROR] Loop {i + 1} failed: {e}")
            update_stats(errors=1)
            # Tenter de récupérer
            FirewallManager.unblock()
            time.sleep(2)
    
    # Résumé final
    total_time = time.time() - start_time
    log("\n" + "=" * 50)
    log("               SESSION COMPLETE")
    log("=" * 50)
    log(f"  Loops Completed: {total_loops}")
    log(f"  Total Time: {total_time / 60:.1f} minutes")
    log(f"  Avg per Loop: {total_time / total_loops / 60:.1f} minutes")
    log(f"  Total Properties (All Time): {STATS['total_properties_bought']}")
    log("=" * 50)


def main():
    """Point d'entrée principal"""
    setup_logging()
    
    # Initialisation
    FirewallManager.unblock()
    load_stats()
    
    if not load_assets_into_ram():
        log_error("[FATAL] Failed to load assets. Exiting.")
        sys.exit(1)
    
    if not validate_required_assets():
        log_error("[FATAL] Missing required assets. Exiting.")
        sys.exit(1)
    
    display_banner()
    
    total_loops, start_choice = get_user_input()
    start_online = (start_choice == "2")
    
    print(f"\nPress {CONFIG.START_KEY.upper()} to START. ('{CONFIG.PANIC_KEY.upper()}' to STOP at any time)")
    keyboard.wait(CONFIG.START_KEY)
    
    run_main_loop(total_loops, start_online)


if __name__ == "__main__":
    main()
