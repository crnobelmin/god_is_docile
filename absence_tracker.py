import time
import numpy as np

class InstallationStateManager:
    def __init__(self, session_duration_secs: float = 300.0):
        self.duration = session_duration_secs
        self.start_time = time.time()
        
        # 4 Channels representing the 4 visitor portrait frames
        # Tracks the Unix timestamp of when motion was last detected
        self.last_motion_timestamps = [time.time()] * 4
        
        # Audio gain profiles
        self.idle_volume = 0.1       # Baseline whisper volume when active
        self.base_ramp_rate = 0.02   # Gain increase per second of absence at start

    def update_motion(self, frame_index: int):
        """Called immediately via an interrupt/callback when ESP32 alerts a pin HIGH"""
        self.last_motion_timestamps[frame_index] = time.time()

    def get_channel_volumes(self) -> np.ndarray:
        """Calculates the current volume multipliers for all 4 channels"""
        now = time.time()
        
        # 1. Calculate overall session progress (clamped between 0.0 and 1.0)
        elapsed = now - self.start_time
        session_progress = np.clip(elapsed / self.duration, 0.0, 1.0)
        
        # 2. Scale the ramp speed based on session progress
        # Using a squaring factor ensures the acceleration curve feels dramatic near the end
        aggression_multiplier = 1.0 + (5.0 * (session_progress ** 2)) 
        current_ramp_rate = self.base_ramp_rate * aggression_multiplier
        
        volumes = np.zeros(4, dtype=np.float32)
        
        for i in range(4):
            # Calculate how long this specific frame has been vacant
            absence_duration = now - self.last_motion_timestamps[i]
            
            # Calculate dynamic gain accumulation
            accumulated_gain = absence_duration * current_ramp_rate
            target_vol = self.idle_volume + accumulated_gain
            
            # Clamp volume so it never exceeds maximum headroom safety ceiling
            volumes[i] = np.clip(target_vol, self.idle_volume, 1.0)
            
        return volumes
        
        
        
        
 # Instantiated at the start of kustos session
state = InstallationStateManager(session_duration_secs=300.0) 

# ... Simulated Background Audio Thread ...
while True:
    # Get current calculated weights: e.g., [0.1, 0.45, 0.1, 0.92]
    vols = state.get_channel_volumes()
    
    # Apply weights directly to individual channel vectors before mixing
    ch1_scaled = ch1_frame_buffer * vols[0]
    ch2_scaled = ch2_frame_buffer * vols[1]
    ch3_scaled = ch3_frame_buffer * vols[2]
    ch4_scaled = ch4_frame_buffer * vols[3]
    
    # Mix into the master output stream
    master_mix = ch1_scaled + ch2_scaled + ch3_scaled + ch4_scaled
    
    # Convert mix array to bytes and ship via UDP to ESP32 endpoints...