# 🏠 GTA Online Apartment Swap Glitch

> **Version 10.0** — Fully automated apartment trade-in exploit using computer vision.

---

## ⚠️ IMPORTANT: Ban Risk


> [!IMPORTANT]
> **CRITICAL RULE:** Do NOT exceed **$40 Million per run** (script execution).
> You **MUST SPEND** most of the money immediately after the run. Do not stockpile cash.


---

## 📋 Requirements

### System
- **OS:** Windows 10/11
- **Python:** 3.10+
- **Admin rights** (for firewall rules)

### GTA V Settings (MANDATORY)

| Setting | Value |
|---------|-------|
| Screen Type | **Windowed Borderless** |
| Mouse Input | **Raw Input** |
| Quick Snapmatic | **OFF** |
| Resolution | 1920×1080 or higher |

---

## 🚀 Quick Start

### Step 1: Download
```
git clone https://github.com/Pouare514/GTAO-Apartment-Swap-Glitch.git
```
Or download ZIP and extract.

### Step 2: Run
```
Double-click run.bat
```
> ✅ Auto-installs Python dependencies  
> ✅ Creates virtual environment  
> ✅ Requests admin rights automatically

### Step 3: In-Game Setup
1. Launch GTA V
2. Enter **Invite Only** or **Friend Session**
3. Own the expensive apartment you want to trade

### Step 4: Start Glitch
1. Enter number of loops when prompted
2. Select starting point (Story Mode or Online)
3. Press **F1** to start
4. Press **Q** anytime to emergency stop

---

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    LOOP CYCLE                           │
├─────────────────────────────────────────────────────────┤
│  1. Open in-game browser → Dynasty8 Real Estate        │
│  2. Block Rockstar servers (firewall)                  │
│  3. Buy cheapest apartment × 10 slots                  │
│  4. Trade-in your expensive apartment each time        │
│  5. Quit to Story Mode (changes NOT saved)             │
│  6. Unblock connection                                 │
│  7. Return Online (you keep apartments + money)        │
│  8. Force save via Interaction Menu                    │
│  9. Repeat                                             │
└─────────────────────────────────────────────────────────┘
```

**Result:** You get refund money but keep the original apartment.

---

## 📁 Project Structure

```
GTAO-Apartment-Swap-Glitch/
├── main.py           # Main automation script
├── run.bat           # One-click launcher
├── assets/           # PNG images for detection (required!)
├── debug_errors/     # Screenshots on failure (auto-created)
├── stats.json        # Persistent statistics
└── gta_debug.log     # Debug log file
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Script can't find images | Use **Windowed Borderless**, not Fullscreen |
| Clicks wrong location | Check resolution matches assets (1080p) |
| Firewall error | Run as Administrator |
| Script crashes | Check `debug_errors/` for failure screenshots |
| Stuck in loop | Press **Q** to emergency stop |

---

## 📊 Statistics

The script tracks your progress in `stats.json`:
- Total loops completed
- Total properties bought
- Errors recovered
- Session timestamps

---

## ⌨️ Controls

| Key | Action |
|-----|--------|
| **F1** | Start automation |
| **Q** | Emergency stop (works anytime) |

---

## 🛡️ Safety Features

- ✅ Panic key (Q) checked every operation
- ✅ Auto-restore firewall on exit/crash
- ✅ Failure screenshots for debugging
- ✅ Persistent stats across sessions

---

## 📜 License

MIT License — Use at your own risk. No warranty provided.

---

<p align="center">
  <b>Made for educational purposes only.</b><br>
  <i>The developers are not responsible for any bans or account actions.</i>
</p>
