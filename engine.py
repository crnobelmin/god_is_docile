import asyncio
import socket
import time
import os
import numpy as np

# --- SYSTEM CONFIGURATION ---
SAMPLE_RATE = 44100
CHUNK_SIZE = 512
DECAY_RATE = 0.15  # Controls how fast the audio calms down

# Absolute path matching your Flask server upload target
AUDIO_DIR = os.path.expanduser('~/godisdocile/god_is_docile/audio_files')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Hardware Registry (IPs of your 4 future ESP32 frames)
FRAME_IPS = ["192.168.1.50", "192.168.1.102", "192.168.1.103", "192.168.1.104"]
UDP_PORT = 5001        # Port where the ESP32s/FFmpeg listen for audio
LISTEN_PORT = 6000     # Port where Termux listens for PIR sensor pings

# --- INITIAL SYSTEM MIXER STATE ---
intensities = np.array([0.0, 0.0, 0.0, 0.0]) 
last_update_time = time.time()

# Mixer storage tracks (Active audio buffers in RAM)
active_tracks = [np.zeros(SAMPLE_RATE * 5, dtype=np.float32) for _ in range(4)]
track_pointers = [0, 0, 0, 0]
track_filenames = ["", "", "", ""] # Tracks what is currently loaded

# High-speed UDP socket creation
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def generate_fallback_ambient():
    """Generates a safe, super-low frequency baseline tone if a slot is empty"""
    t = np.linspace(0, 5.0, SAMPLE_RATE * 5, endpoint=False)
    return (np.sin(2 * np.pi * 55.0 * t) * 0.05).astype(np.float32)

def apply_chained_modulation(x_chunk, intensity):
    """Applies mathematical transformations to the sound array based on motion intensity"""
    if intensity <= 0.01:
        # Quiet ambient baseline state when no one is near the frame
        return (x_chunk * 0.1).astype(np.int16).tobytes() 
        
    # 1. Exponential Overdrive Distortion
    drive = 1.0 + (intensity * 10.0)
    y = np.tanh(drive * x_chunk)
    
    # 2. Sinusoidal Wavefolding
    y = np.sin(y * (1.0 + intensity * np.pi))
    
    # 3. Dynamic Loudness Scaling
    gain = 0.1 + (intensity * 0.9)
    y = y * gain
    
    # Convert safe float32 math directly back to raw 16-bit PCM bytes
    return (y * 32767).astype(np.int16).tobytes()

async def directory_watcher():
    """Asynchronous background task that watches the folder and hot-swaps tracks"""
    global active_tracks, track_filenames
    
    while True:
        try:
            # Find all available .npy files and sort them alphabetically
            all_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith('.npy')])
            
            for i in range(4):
                if i < len(all_files):
                    fname = all_files[i]
                    # If this file isn't loaded in this channel slot yet, hot-swap it!
                    if track_filenames[i] != fname:
                        fpath = os.path.join(AUDIO_DIR, fname)
                        try:
                            # Load binary numpy array into RAM instantly
                            loaded_data = np.load(fpath)
                            
                            # Ensure data size matches formatting expectations safely
                            if len(loaded_data) > 0:
                                active_tracks[i] = loaded_data.astype(np.float32)
                                track_filenames[i] = fname
                                print(f"🔄 [Hot-Swap] Channel {i+1} loaded new track asset: {fname}")
                        except Exception as e:
                            # Keeps loop alive if transformer.py is still actively writing the file
                            pass
                else:
                    # Fallback configuration if fewer than 4 files exist in the matrix
                    if track_filenames[i] != "__fallback__":
                        active_tracks[i] = generate_fallback_ambient()
                        track_filenames[i] = "__fallback__"
                        print(f"💤 [Mixer] Channel {i+1} idling on fallback ambient drone.")
                        
        except Exception as e:
            print(f"Error scanning directories: {e}")
            
        # Check for new assets every 2 seconds without putting pressure on the audio pacing
        await asyncio.sleep(2.0)

async def process_and_stream_audio_tick():
    """Main pacing loop running non-stop to feed all 4 channels simultaneously"""
    global last_update_time, intensities
    
    print("📡 Audio engine processing matrix loops. Ready for hardware deployment...")
    while True:
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time
        
        # Smoothly decay the motion intensity arrays downward over time
        intensities = intensities * np.exp(-DECAY_RATE * dt)
        intensities = np.clip(intensities, 0.0, 1.0)
        
        for i, ip in enumerate(FRAME_IPS):
            ptr = track_pointers[i]
            track_data = active_tracks[i]
            
            # Slice our chunk out of the active track array
            chunk = track_data[ptr : ptr + CHUNK_SIZE]
            
            # Loop track seamlessly if it hits the end of the 5-second vector
            if len(chunk) < CHUNK_SIZE:
                track_pointers[i] = 0
                chunk = track_data[0:CHUNK_SIZE]
            else:
                track_pointers[i] += CHUNK_SIZE
                
            # Execute DSP chain
            modulated_bytes = apply_chained_modulation(chunk, intensities[i])
            
            # Fire packet over the air to target client IP
            try:
                sock.sendto(modulated_bytes, (ip, UDP_PORT))
            except Exception:
                pass
            
        # Highly precise real-time pacing throttle (~11.6ms chunks)
        await asyncio.sleep(CHUNK_SIZE / SAMPLE_RATE)

class ESP32MotionReceiver(asyncio.DatagramProtocol):
    """Intercepts incoming network pings from physical hardware sensors"""
    def datagram_received(self, data, addr):
        global intensities
        try:
            msg = data.decode().strip()
            if "TRIGGER" in msg:
                frame_id = int(msg.split(":")[1])
                if 1 <= frame_id <= 4:
                    print(f"💥 PIR Motion Triggered at Frame {frame_id}! Spiking effects matrix.")
                    intensities[frame_id - 1] = 1.0
        except Exception as e:
            print(f"Error parsing incoming UDP packet: {e}")

async main():
    loop = asyncio.get_running_loop()
    
    # Establish the background UDP port listener for the hardware PIR sensors
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ESP32MotionReceiver(),
        local_addr=('0.0.0.0', LISTEN_PORT)
    )
    
    # Concurrently execute streaming, network listening, and background hot-reloading
    await asyncio.gather(
        process_and_stream_audio_tick(),
        directory_watcher()
    )

if __name__ == "__main__":
    print("🔊 Starting 4-channel autonomous interactive sound engine...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down audio engine.")