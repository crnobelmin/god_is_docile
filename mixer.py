import tkinter as tk
from tkinter import ttk
import numpy as np
import sounddevice as sd
import threading

class FullScaleSynthStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("🎛️ godisdocile - Full Parameter Eurorack Drum Synth Studio")
        self.root.resizable(True, True)

        # 1. AUDIO ENGINE RUNTIME VARIABLES
        self.is_running = True
        self.visual_step = 0
        self.sample_rate = 44100

        # 2. MASTER PARAMETER DICTIONARY (Fully Exposed variables)
        self.p = {
            'bpm': 120,
            # Kick parameters
            'kick_f_start': 150.0, 'kick_f_end': 40.0, 'kick_p_decay': 60.0, 'kick_a_decay': 18.0,
            # Snare parameters
            'snare_f_start': 180.0, 'snare_f_end': 80.0, 'snare_t_decay': 30.0, 'snare_n_decay': 12.0, 'snare_noise_ratio': 0.6,
            # Hi-hats
            'closed_hat_decay': 75.0, 'open_hat_decay': 15.0,
            # Clap
            'clap_strike_decay': 120.0, 'clap_tail_decay': 15.0,
            # Low / High Toms
            'ltom_pitch': 115.0, 'ltom_decay': 11.0, 'htom_pitch': 210.0, 'htom_decay': 11.0,
            # Rimshot
            'rim_pitch': 1400.0, 'rim_decay': 110.0
        }

        # Initialize Sequencer Grid State (8 steps x 8 channels)
        self.pattern_matrix = np.zeros((8, 8), dtype=np.float32)
        self.instrument_names = ["Kick", "Snare", "Cl-Hat", "Op-Hat", "Clap", "Low-Tom", "High-Tom", "Rimshot"]

        # Seed default rhythms so it grooves immediately
        self.pattern_matrix[0, 0] = 1.0; self.pattern_matrix[4, 0] = 1.0  # Four-on-the-floor Kicks
        self.pattern_matrix[2, 1] = 1.0; self.pattern_matrix[6, 1] = 1.0  # Snares
        self.pattern_matrix[2, 4] = 1.0                                  # Clap layer
        for step in [0, 2, 4, 6]: self.pattern_matrix[step, 2] = 1.0      # Closed Hats
        self.pattern_matrix[5, 3] = 1.0; self.pattern_matrix[7, 7] = 1.0  # Open Hat + Rim accents

        # 3. BUILD INTERFACE
        self.create_layout()

        # 4. RUNTIME THREADS
        self.audio_thread = threading.Thread(target=self.audio_processing_loop, daemon=True)
        self.audio_thread.start()

        self.playhead_animation_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_layout(self):
        """Assembles the UI elements into a responsive interface."""
        # Top-level canvas container
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        self.scroll_frame = ttk.Frame(main_canvas, padding="15")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)

        # --- SECTION 1: MASTER BPM CONTROLLER ---
        master_frame = ttk.Frame(self.scroll_frame)
        master_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(master_frame, text="MASTER TEMPO Control:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.bpm_lbl = ttk.Label(master_frame, text=f"{self.p['bpm']} BPM", font=("Helvetica", 10))
        self.bpm_lbl.pack(side=tk.RIGHT, padx=5)
        bpm_slider = ttk.Scale(master_frame, from_=50, to=220, value=self.p['bpm'], command=lambda v: self.update_param('bpm', v, self.bpm_lbl, "{:0.0f} BPM", True))
        bpm_slider.pack(side=tk.LEFT, fill='x', expand=True, padx=10)

        # --- SECTION 2: THE 8x8 HARDWARE PAD MATRIX ---
        matrix_box = ttk.LabelFrame(self.scroll_frame, text=" HARDWARE STEP MATRIX SEQUENCER ", padding="10")
        matrix_box.pack(pady=5, fill='x')

        for c in range(8):
            ttk.Label(matrix_box, text=self.instrument_names[c], font=("Helvetica", 9, "bold"), width=9, anchor="center").grid(row=0, column=c+1, padx=2, pady=5)

        self.row_labels, self.grid_buttons = [], []
        for r in range(8):
            lbl = tk.Label(matrix_box, text=f"Step {r+1} →", font=("Helvetica", 9), width=8, anchor="w")
            lbl.grid(row=r+1, column=0, padx=5, pady=2)
            self.row_labels.append(lbl)

            button_row = []
            for c in range(8):
                active = self.pattern_matrix[r, c] == 1.0
                btn = tk.Button(matrix_box, bg="#4CAF50" if active else "#2E2E2E", activebackground="#666", width=6, height=1, relief="flat", command=lambda row=r, col=c: self.toggle_pad(row, col))
                btn.grid(row=r+1, column=c+1, padx=2, pady=2)
                button_row.append(btn)
            self.grid_buttons.append(button_row)

        # --- SECTION 3: MODULAR SYNTH RACK (Parameter Knobs & Sliders) ---
        rack_box = ttk.LabelFrame(self.scroll_frame, text=" MODULAR SIGNAL SYNTHESIZER CONTROL BLOCKS ", padding="10")
        rack_box.pack(fill='both', expand=True, pady=10)

        # Configure dynamic multi-column channel alignment
        for col_idx in range(4):
            rack_box.columnconfigure(col_idx, weight=1, uniform="rack_col")

        # ------------------ KICK BLOCK (Row 0, Col 0) ------------------
        b_kick = ttk.LabelFrame(rack_box, text=" 🟥 KICK SYNTH (SINE SWEEP) ", padding="8")
        b_kick.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_kick, "Start Pitch (Hz)", 60, 300, 'kick_f_start', "{:.0f} Hz")
        self.add_knob(b_kick, "End Sub-Pitch (Hz)", 20, 80, 'kick_f_end', "{:.0f} Hz")
        self.add_knob(b_kick, "Pitch Drop Speed", 10, 150, 'kick_p_decay', "{:.0f}")
        self.add_knob(b_kick, "Amp Decay Length", 2, 50, 'kick_a_decay', "{:.0f}")

        # ------------------ SNARE BLOCK (Row 0, Col 1) ------------------
        b_snare = ttk.LabelFrame(rack_box, text=" 🟨 SNARE SYNTH (HYBRID) ", padding="8")
        b_snare.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_snare, "Shell Start Pitch (Hz)", 100, 350, 'snare_f_start', "{:.0f} Hz")
        self.add_knob(b_snare, "Shell End Pitch (Hz)", 50, 150, 'snare_f_end', "{:.0f} Hz")
        self.add_knob(b_snare, "Shell Decay", 5, 80, 'snare_t_decay', "{:.0f}")
        self.add_knob(b_snare, "Noise Rattle Snap", 2, 40, 'snare_n_decay', "{:.0f}")
        self.add_knob(b_snare, "Tone / Noise Mix Balance", 0.0, 1.0, 'snare_noise_ratio', "{:.2f}")

        # ------------------ CLOSED HAT (Row 0, Col 2) ------------------
        b_chat = ttk.LabelFrame(rack_box, text=" 🟩 CLOSED HI-HAT ", padding="8")
        b_chat.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_chat, "Choke Decay Speed", 20, 180, 'closed_hat_decay', "{:.0f}")

        # ------------------ OPEN HAT (Row 0, Col 3) ------------------
        b_ohat = ttk.LabelFrame(rack_box, text=" 🟦 OPEN HI-HAT ", padding="8")
        b_ohat.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_ohat, "Sustain Tail Sizzle", 2, 40, 'open_hat_decay', "{:.0f}")

        # ------------------ HANDCLAP (Row 1, Col 0) ------------------
        b_clap = ttk.LabelFrame(rack_box, text=" 🟪 HANDCLAP ENVELOPE ", padding="8")
        b_clap.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_clap, "Stagger Spike Decay", 40, 250, 'clap_strike_decay', "{:.0f}")
        self.add_knob(b_clap, "Room Echo Tail Decay", 4, 40, 'clap_tail_decay', "{:.0f}")

        # ------------------ LOW TOM (Row 1, Col 1) ------------------
        b_ltom = ttk.LabelFrame(rack_box, text=" 🟫 LOW TOM TOM ", padding="8")
        b_ltom.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_ltom, "Fundamental Pitch (Hz)", 60, 180, 'ltom_pitch', "{:.0f} Hz")
        self.add_knob(b_ltom, "Resonance Tail Length", 2, 30, 'ltom_decay', "{:.0f}")

        # ------------------ HIGH TOM (Row 1, Col 2) ------------------
        b_htom = ttk.LabelFrame(rack_box, text=" 🟧 HIGH TOM TOM ", padding="8")
        b_htom.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_htom, "Fundamental Pitch (Hz)", 150, 350, 'htom_pitch', "{:.0f} Hz")
        self.add_knob(b_htom, "Resonance Tail Length", 2, 30, 'htom_decay', "{:.0f}")

        # ------------------ RIMSHOT (Row 1, Col 3) ------------------
        b_rim = ttk.LabelFrame(rack_box, text=" ⬜ WOODEN RIMSHOT ", padding="8")
        b_rim.grid(row=1, column=3, padx=5, pady=5, sticky="nsew")
        self.add_knob(b_rim, "Metallic Pop Pitch (Hz)", 800, 2200, 'rim_pitch', "{:.0f} Hz")
        self.add_knob(b_rim, "Choke Decay Time", 40, 200, 'rim_decay', "{:.0f}")

    def add_knob(self, frame, label_text, min_v, max_v, dict_key, fmt_str):
        """Helper to safely instantiate tracking labels along with linked synth control sliders."""
        lbl_title = ttk.Label(frame, text=label_text, font=("Helvetica", 8))
        lbl_title.pack(anchor='w', pady=(4, 0))
        
        lbl_val = ttk.Label(frame, text=fmt_str.format(self.p[dict_key]), font=("Helvetica", 8, "italic"), foreground="#555")
        lbl_val.pack(anchor='e')
        
        slider = ttk.Scale(frame, from_=min_v, to=max_v, value=self.p[dict_key], 
                           command=lambda v: self.update_param(dict_key, v, lbl_val, fmt_str))
        slider.pack(fill='x', pady=(0, 4))

    def update_param(self, key, value, label, fmt, is_int=False):
        """Dispatches modified slider state numbers into the thread-safe global store dictionary."""
        val = int(float(value)) if is_int or float(value).is_integer() else float(value)
        self.p[key] = val
        label.config(text=fmt.format(val))

    def toggle_pad(self, row, col):
        if self.pattern_matrix[row, col] == 0.0:
            self.pattern_matrix[row, col] = 1.0
            self.grid_buttons[row][col].config(bg="#4CAF50")
        else:
            self.pattern_matrix[row, col] = 0.0
            self.grid_buttons[row][col].config(bg="#2E2E2E")

    def playhead_animation_loop(self):
        curr = self.visual_step
        for r in range(8):
            if r == curr:
                self.row_labels[r].config(fg="#E91E63", font=("Helvetica", 9, "bold"))
            else:
                self.row_labels[r].config(fg="black", font=("Helvetica", 9, "normal"))
        if self.is_running:
            self.root.after(12, self.playhead_animation_loop)

    # =====================================================================
    # PRODUCTION LEVEL LIVE EQUATION RENDERER
    # =====================================================================
    def audio_processing_loop(self):
        sr = self.sample_rate
        step_idx = 0
        stream = sd.OutputStream(samplerate=sr, channels=1, dtype='float32')
        stream.start()

        while self.is_running:
            # 1. Fetch snapshot of slider metrics at the step boundary line
            bpm = self.p['bpm']
            self.visual_step = step_idx % 8

            seconds_per_step = (60.0 / bpm) / 2.0
            samples_per_step = int(sr * seconds_per_step)
            step_buffer = np.zeros(samples_per_step, dtype=np.float32)

            # 2. Iterate through columns and solve mathematical equations on-demand
            for inst in range(8):
                if self.pattern_matrix[self.visual_step, inst] == 1.0:
                    hit = np.zeros(10, dtype=np.float32)

                    if inst == 0:  #🟩 KICK DRUM ENGINE
                        t = np.linspace(0, 0.3, int(sr * 0.3), endpoint=False)
                        f_sweep = self.p['kick_f_end'] + (self.p['kick_f_start'] - self.p['kick_f_end']) * np.exp(-self.p['kick_p_decay'] * t)
                        phase = 2 * np.pi * np.cumsum(f_sweep / sr)
                        hit = np.sin(phase) * np.exp(-self.p['kick_a_decay'] * t)

                    elif inst == 1: #🟩 HYBRID SNARE ENGINE
                        t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
                        f_sweep = self.p['snare_f_end'] + (self.p['snare_f_start'] - self.p['snare_f_end']) * np.exp(-self.p['snare_t_decay'] * t)
                        phase = 2 * np.pi * np.cumsum(f_sweep / sr)
                        tone = np.sin(phase) * np.exp(-30.0 * t)
                        noise = np.random.normal(0, 0.3, len(t)) * np.exp(-self.p['snare_n_decay'] * t)
                        n_ratio = self.p['snare_noise_ratio']
                        hit = ((1.0 - n_ratio) * tone) + (n_ratio * noise)

                    elif inst == 2: #🟩 CLOSED HI-HAT ENGINE
                        t = np.linspace(0, 0.05, int(sr * 0.05), endpoint=False)
                        hit = np.random.normal(0, 0.4, len(t)) * np.exp(-self.p['closed_hat_decay'] * t)

                    elif inst == 3: #🟩 OPEN HI-HAT ENGINE
                        t = np.linspace(0, 0.3, int(sr * 0.3), endpoint=False)
                        hit = np.random.normal(0, 0.3, len(t)) * np.exp(-self.p['open_hat_decay'] * t)

                    elif inst == 4: #🟩 MULTI-STRIKE CLAP ENGINE
                        t_full = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
                        hit = np.zeros_like(t_full)
                        for offset in [0, int(sr * 0.012), int(sr * 0.024)]:
                            rem = len(t_full) - offset
                            if rem > 0:
                                hit[offset:] += np.random.normal(0, 0.25, rem) * np.exp(-self.p['clap_strike_decay'] * np.linspace(0, rem/sr, rem, endpoint=False))
                        hit += np.random.normal(0, 0.2, len(t_full)) * np.exp(-self.p['clap_tail_decay'] * t_full)

                    elif inst == 5: #🟩 LOW TOM ENGINE
                        t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
                        f_sweep = (self.p['ltom_pitch'] * 0.6) + (self.p['ltom_pitch'] * 0.4) * np.exp(-25.0 * t)
                        hit = np.sin(2 * np.pi * np.cumsum(f_sweep / sr)) * np.exp(-self.p['ltom_decay'] * t)

                    elif inst == 6: #🟩 HIGH TOM ENGINE
                        t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
                        f_sweep = (self.p['htom_pitch'] * 0.6) + (self.p['htom_pitch'] * 0.4) * np.exp(-25.0 * t)
                        hit = np.sin(2 * np.pi * np.cumsum(f_sweep / sr)) * np.exp(-self.p['htom_decay'] * t)

                    elif inst == 7: #🟩 RIMSHOT ENGINE
                        t = np.linspace(0, 0.04, int(sr * 0.04), endpoint=False)
                        hit = np.sin(2 * np.pi * self.p['rim_pitch'] * t) * np.exp(-self.p['rim_decay'] * t)

                    # Dynamic mixing calculation block
                    write_len = min(len(hit), samples_per_step)
                    step_buffer[:write_len] += hit[:write_len]

            # 3. SAFETY GAIN NORMALIZATION STAGE
            peak = np.max(np.abs(step_buffer))
            if peak > 1.0:
                step_buffer /= peak

            if self.is_running:
                stream.write(step_buffer.astype(np.float32))
            step_idx += 1

        stream.stop()
        stream.close()

    def on_close(self):
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    window = tk.Tk()
    window.geometry("960x780")
    app = FullScaleSynthStudio(window)
    window.mainloop()