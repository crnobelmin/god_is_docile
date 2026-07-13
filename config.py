import os
import threading

# --- PATH CONFIGURATIONS ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'visitor_groups')

# --- CONFIGURATION TUNING ---
BPM = 120               # Adjust this to speed up or slow down the rhythm
BEATS_PER_BAR = 4       # Standard 4/4 time signature
BARS_IN_LOOP = 4        # Length of our repeating phrase
TICK_INTERVAL = 0.02    # Strict 20ms network clock interval
STEPS_PER_LOOP = 32

# Musical Math Derivations
BEATS_PER_LOOP = BEATS_PER_BAR * BARS_IN_LOOP
SECONDS_PER_BEAT = 60.0 / BPM
LOOP_DURATION = SECONDS_PER_BEAT * BEATS_PER_LOOP  # e.g., 8.0 seconds at 120 BPM

INSTALLATION_DURATION = 420  # 7-minute limit to return to drone sound
KUSTOS_PASS = 'kustosisdocile'
MAX_PORTRAIT_SIZE = (1000, 1000)

# --- NETWORK CONFIGURATION ---
BROADCAST_IP = "255.255.255.255"
UDP_PORT = 12345

# --- THREAD-SAFE SHARED MEMORY ---
shared_state = {
    'current_group': "",
    'play_requested': False
}
state_lock = threading.Lock()