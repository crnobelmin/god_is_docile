import os
import time
import json
import socket
import numpy as np
import config

class MasterSequencer:
    def __init__(self):
        # Initialize UDP Socket and set Broadcast permissions
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Internal Loop Control States
        self.mode = "WAITING" 
        self.loop_freq_matrix = np.array([])
        self.playback_ticks = 0
        self.max_playback_ticks = int(config.INSTALLATION_DURATION / config.TICK_INTERVAL)
        self.sequence_num = 0

        # Historical registers to calculate sustained ties (ZOH checks)
        self.prev_freq_r = None
        self.prev_freq_g = None
        self.prev_freq_b = None
        self.prev_freq_l = None

    def resample_to_chord_progression(self, data, steps_per_loop=32):
        """STAGE 1 RESAMPLING: Maps pixel matrices onto structural musical steps."""
        original_samples = len(data)
        old_indices = np.linspace(0, original_samples - 1, original_samples)
        new_indices = np.linspace(0, original_samples - 1, steps_per_loop)
        
        progression_data = np.zeros((steps_per_loop, 4))
        for channel in range(4):
            progression_data[:, channel] = np.interp(new_indices, old_indices, data[:, channel])
        return progression_data

    def resample_to_ticks(self, macro_matrix, target_duration_sec=8.0, interval_sec=0.02):
        """STAGE 2 RESAMPLING: Stretches stable steps via Zero-Order Hold."""
        target_samples = int(target_duration_sec / interval_sec)
        indices = np.linspace(0, len(macro_matrix), target_samples, endpoint=False).astype(int)
        return macro_matrix[indices]

    def snap_to_double_harmonic_major_vectorized(self, midi_note_array, root=0):
        """Vectorized Arabic Scale Quantization System."""
        scale_degrees = np.array([0, 1, 4, 5, 7, 8, 11])
        relative_note = midi_note_array - root
        octave_base = (relative_note // 12) * 12
        note_in_octave = relative_note % 12
        
        diffs = np.abs(note_in_octave[..., np.newaxis] - scale_degrees)
        closest_idx = np.argmin(diffs, axis=-1)
        closest_degree = scale_degrees[closest_idx]
        
        wrap_condition = np.abs(note_in_octave - 12) < np.abs(note_in_octave - closest_degree)
        octave_base = np.where(wrap_condition, octave_base + 12, octave_base)
        closest_degree = np.where(wrap_condition, scale_degrees[0], closest_degree)
            
        return octave_base + closest_degree + root

    def map_value_to_scale_frequency_vectorized(self, raw_value_array, min_midi=55, max_midi=77, root=0):
        """Converts raw arrays into absolute quantized frequency values (Hz)."""
        continuous_midi = min_midi + (raw_value_array * (max_midi - min_midi))
        target_midi = np.rint(continuous_midi).astype(int)
        quantized_midi = self.snap_to_double_harmonic_major_vectorized(target_midi, root=root)
        return 440.0 * (2.0 ** ((quantized_midi - 69) / 12.0))

    def run(self):
        """Core timeline loop executed continuously inside the background thread."""
        print(f"Master Audio Sequencer Initialized ({config.BPM} BPM, 4-Bar Loop = {config.LOOP_DURATION:.2f}s).")
        
        while True:
            start_time = time.time()
            local_play_requested = False
            group_name = ""
            active_root = 0

            # Atomic Thread Safe read of UI playback triggers
            with config.state_lock:
                if config.shared_state['play_requested']:
                    local_play_requested = True
                    config.shared_state['play_requested'] = False
                    group_name = config.shared_state['current_group']

            # --- PARSE NEW TRACK SELECTIONS ---
            if local_play_requested:
                file_path = os.path.join(config.GROUPS_DIR, group_name, 'outputs', 'masked_portrait_array.npy')

                if os.path.exists(file_path):
                    print(f"Sequencer: Spooling up refactored 2-stage pipeline for {group_name}...")
                    data = np.load(file_path)
                    
                    # Compute transformations
                    progression_matrix = self.resample_to_chord_progression(data, steps_per_loop=config.STEPS_PER_LOOP)
                    macro_freq_matrix = self.map_value_to_scale_frequency_vectorized(
                        progression_matrix, min_midi=55, max_midi=77, root=active_root
                    )
                    self.loop_freq_matrix = self.resample_to_ticks(macro_freq_matrix, config.LOOP_DURATION, config.TICK_INTERVAL)
                    
                    self.playback_ticks = 0  
                    self.mode = "PLAYING"
                else:
                    print(f"Sequencer Error: File target {file_path} cannot be found.")
                    self.mode = "WAITING"

            # --- AUDIO TRACK STEP TRACKER ---
            if self.mode == "PLAYING":
                loop_length_samples = len(self.loop_freq_matrix)
                loop_idx = self.playback_ticks % loop_length_samples
                
                freq_r, freq_g, freq_b, freq_l = self.loop_freq_matrix[loop_idx, :]

                # Establish if notes are held or freshly re-triggered
                is_r_extended = (freq_r == self.prev_freq_r)
                is_g_extended = (freq_g == self.prev_freq_g)
                is_b_extended = (freq_b == self.prev_freq_b)
                is_l_extended = (freq_l == self.prev_freq_l)
                
                self.prev_freq_r, self.prev_freq_g, self.prev_freq_b, self.prev_freq_l = freq_r, freq_g, freq_b, freq_l

                self.playback_ticks += 1
                if self.playback_ticks >= self.max_playback_ticks:
                    print(f"Installation duration timeout ({config.INSTALLATION_DURATION}s). Resetting to standby.")
                    self.mode = "WAITING"

            elif self.mode == "WAITING":
                freq_r = freq_g = freq_b = freq_l = 220.0
                is_r_extended = is_g_extended = is_b_extended = is_l_extended = False

            # --- UDP TRANSMISSION STREAM ---
            packet = {
                "seq": self.sequence_num,
                "R": {"freq": round(freq_r, 2), "mod": 0.5, "ext": int(is_r_extended)},
                "G": {"freq": round(freq_g, 2), "mod": 0.5, "ext": int(is_g_extended)},
                "B": {"freq": round(freq_b, 2), "mod": 0.5, "ext": int(is_b_extended)},
                "L": {"freq": round(freq_l, 2), "mod": 0.5, "ext": int(is_l_extended)}
            }
            self.sequence_num += 1
            message = json.dumps(packet).encode("utf-8")

            try:
                self.sock.sendto(message, (config.BROADCAST_IP, config.UDP_PORT))
            except Exception as e:
                print(f"Network Socket Exception: {e}")

            # Drift Compensation
            elapsed_time = time.time() - start_time
            sleep_time = max(0.001, config.TICK_INTERVAL - elapsed_time) 
            time.sleep(sleep_time)