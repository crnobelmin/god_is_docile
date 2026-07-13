import os
import threading
import config
from sequencer import MasterSequencer
from app import app

if __name__ == "__main__":
    # Ensure system telemetry asset root folder directories exist on disk
    if not os.path.exists(config.GROUPS_DIR):
        os.makedirs(config.GROUPS_DIR)

    # Instantiate our stateful sequencer system engine 
    sequencer = MasterSequencer()

    # Bind the engine loop instance to the background worker thread context
    sequencer_thread = threading.Thread(target=sequencer.run)
    sequencer_thread.daemon = True 
    sequencer_thread.start()

    # Start the native server interface on the environment target
    print("Starting Kustos API Server natively on Termux...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)