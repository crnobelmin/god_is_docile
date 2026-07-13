# JSON TEST (Resilient Dashboard Edition)
import socket
import json
import time
import sys

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 1. FIX: Allow instant reuse of the port so previous crashed runs don't clog it
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((UDP_IP, UDP_PORT))

# 2. FIX: Set a 0.5-second timeout so the script stays awake and handles Ctrl+C
sock.settimeout(0.5)

# ANSI Terminal Styling Codes
RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[91m"
GREEN   = "\033[92m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"

# Clear the screen completely once at startup
print("\033[2J\033[H", end="")
print(f"{BOLD}{CYAN}Listening for UDP broadcasts on port {UDP_PORT}...{RESET}")
print("Press Ctrl+C to exit.\n")

last_seq = None
last_packet_time = None
packet_count = 0

def make_visual_bar(val, length=25):
    clamped_val = max(0.0, min(1.0, val))
    filled_length = int(clamped_val * length)
    return "█" * filled_length + "░" * (length - filled_length)

try:
    while True:
        try:
            # Try to grab data, but only wait for up to 0.5 seconds
            data, addr = sock.recvfrom(2048)
            now = time.time()
            packet_count += 1
            
            packet = json.loads(data.decode("utf-8"))
            seq = packet.get("seq", 0)

            if last_packet_time is None:
                dt = 0.0
            else:
                dt = (now - last_packet_time) * 1000

            if last_seq is None:
                dropped = 0
            else:
                dropped = max(0, seq - last_seq - 1)

            last_seq = seq
            last_packet_time = now

            r_val = packet['R']['freq']
            g_val = packet['G']['freq']
            b_val = packet['B']['freq']
            l_val = packet['L']['freq']

            # Move cursor back to row 4, column 1
            print("\033[4;1H", end="")

            # Live Active Dashboard
            print(f"{BOLD}[NET STATS]{RESET} Status: {GREEN}ONLINE{RESET} | Pkts: {packet_count:06d} | Src: {addr[0]} | Delta: {dt:5.1f}ms   ")
            print("─" * 65)
            print(f"{BOLD}{RED}[R]{RESET} {make_visual_bar(r_val)}  {RED}{r_val:.4f}{RESET}  ")
            print(f"{BOLD}{GREEN}[G]{RESET} {make_visual_bar(g_val)}  {GREEN}{g_val:.4f}{RESET}  ")
            print(f"{BOLD}{BLUE}[B]{RESET} {make_visual_bar(b_val)}  {BLUE}{b_val:.4f}{RESET}  ")
            print(f"{BOLD}{MAGENTA}[L]{RESET} {make_visual_bar(l_val)}  {MAGENTA}{l_val:.4f}{RESET}  ")
            print("─" * 65)

        except socket.timeout:
            # 3. FIX: If no packets arrive, update the dashboard status instead of hanging
            print("\033[4;1H", end="")
            print(f"{BOLD}[NET STATS]{RESET} Status: {YELLOW}WAITING FOR TRANSMITTER...{RESET} (No UDP packets detected)         ")
            print("─" * 65)
            print(f"{BOLD}{RED}[R]{RESET} {make_visual_bar(0)}  0.0000  ")
            print(f"{BOLD}{GREEN}[G]{RESET} {make_visual_bar(0)}  0.0000  ")
            print(f"{BOLD}{BLUE}[B]{RESET} {make_visual_bar(0)}  0.0000  ")
            print(f"{BOLD}{MAGENTA}[L]{RESET} {make_visual_bar(0)}  0.0000  ")
            print("─" * 65)
            continue

        except Exception as e:
            print(f"\n\033[31mProcessing Error: {e}\033[0m")
            continue

except KeyboardInterrupt:
    print("\nStopping receiver...")

finally:
    sock.close()
    print("Socket closed.")
    sys.exit(0)