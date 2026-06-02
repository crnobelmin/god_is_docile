import asyncio
import socket
import time
import numpy as np

# --- SYSTEM CONFIGURATION ---
SAMPLE_RATE = 44100
CHUNK_SIZE = 512
DECAY_RATE = 0.15  # Controls how fast the audio calms down

# Hardware Registry (IPs of your 4 future ESP32 frames)
FRAME_IPS = ["192.168.1.101", "192.168.1.102", "192.168.1.103", "192.168.1.104"]
UDP_PORT = 5001        # Port where the ESP32s listen for audio bytes
LISTEN_PORT = 6000     # Port where Termux listens for PIR sensor pings

# --- INITIAL SYSTEM STATE ---
intensities = np.array([0.0, 0.0, 0.0, 0.0]) 
last_update_time = time.time()

# Mock setup: Pre-generating empty arrays for testing
# Replace these with your actual JPEG-converted .npy or raw audio tracks later
audio_tracks = [np.zeros(44100 * 10, dtype=np.float32) for _ in range(4)]
track_pointers = [0, 0, 0, 0]

# High-speed UDP socket creation
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def apply_chained_modulation(x_chunk, intensity):
    """Applies mathematical transformations to the sound array based on motion intensity"""
    if intensity <= 0.01:
        return (x_chunk * 0.1).astype(np.int16).tobytes() # Quiet ambient baseline
        
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

async def process_and_stream_audio_tick():
    """Main pacing loop running non-stop to feed all 4 frames simultaneously"""
    global last_update_time, intensities
    
    print("📡 Audio stream active. Pacing 4 channels simultaneously...")
    while True:
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time
        
        # Smoothly decay the intensity arrays downward toward 0 over time
        intensities = intensities * np.exp(-DECAY_RATE * dt)
        intensities = np.clip(intensities, 0.0, 1.0)
        
        for i, ip in enumerate(FRAME_IPS):
            ptr = track_pointers[i]
            chunk = audio_tracks[i][ptr : ptr + CHUNK_SIZE]
            
            # Loop track if it hits the end
            if len(chunk) < CHUNK_SIZE:
                track_pointers[i] = 0
                chunk = audio_tracks[i][0:CHUNK_SIZE]
            else:
                track_pointers[i] += CHUNK_SIZE
                
            # Run the math matrix
            modulated_bytes = apply_chained_modulation(chunk, intensities[i])
            
            # Fire packet over the air
            sock.sendto(modulated_bytes, (ip, UDP_PORT))
            
        # Pacing throttle (~11.6ms chunks)
        await asyncio.sleep(CHUNK_SIZE / SAMPLE_RATE)

class ESP32MotionReceiver(asyncio.DatagramProtocol):
    """Intercepts incoming network pings from physical hardware sensors"""
    def datagram_received(self, data, addr):
        global intensities
        try:
            msg = data.decode().strip()
            if "TRIGGER" in msg:
                frame_id = int(msg.split(":")[1])
                print(f"💥 PIR Motion Triggered at Frame {frame_id}! Spiking effects.")
                intensities[frame_id - 1] = 1.0
        except Exception as e:
            print(f"Error parsing incoming UDP packet: {e}")

async def main():
    loop = asyncio.get_running_loop()
    
    # Establish the background UDP port listener for the PIR sensors
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ESP32MotionReceiver(),
        local_addr=('0.0.0.0', LISTEN_PORT)
    )
    
    # Concurrently execute the data transmission and sensor listening pipelines
    await asyncio.gather(
        process_and_stream_audio_tick()
    )

if __name__ == "__main__":
    print("🔊 Starting 4-channel autonomous interactive sound engine...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down audio engine.")