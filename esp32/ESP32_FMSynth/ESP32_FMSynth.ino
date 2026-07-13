#include <Arduino.h>

// Include our custom modules so the compiler knows how to initialize and update them
#include "Parameters.h"
#include "I2SOutput.h"
#include "AudioTask.h"
#include "NetworkController.h"

/**
 * The setup function runs exactly once when the ESP32 first boots up or resets.
 * This is used to configure hardware and prepare memory structures.
 */
void setup()
{
    // Initialize serial communication for diagnostic logging at 115200 baud rate
    Serial.begin(115200);

    // 1. Memory Preparation: Instantiates default safe values into the shared atomic parameters.
    // Must be called first so that any other subsystem accessing parameters won't read garbage memory.
    initParameters();

    // 2. Hardware Preparation: Configures the internal I2S clock routing, APLL, and registers,
    // allocating the DMA ring buffers so they are completely ready to receive audio bytes.
    initI2S();

    // 3. Telemetry Preparation: Boots up the physical radio antennas and establishes a 
    // connection to the Wi-Fi network, opening up UDP Port 12345 for JSON stream reception.
    initNetwork();

    // 4. Runtime Ignition: Spawns the real-time audio generation loop as an independent 
    // thread and pins it permanently to CPU Core 1 with near-maximum priority.
    startAudioTask();
}

/**
 * The loop function executes continuously on the main application thread.
 * Once it reaches the bottom, it instantly starts again at the top.
 */
void loop()
{
    // Continuously parse incoming UDP network packets, decode JSON instructions, 
    // and write updated parameters safely across cores to our atomic structure.
    networkUpdate();

    // Cooperative Multitasking Yield: Briefly gives up control for 1 millisecond.
    // This allows background operating system tasks (like maintaining the Wi-Fi TCP/IP stack)
    // to execute smoothly, preventing the chip's Watchdog Timer from timing out and resetting.
    delay(1);
}