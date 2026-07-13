#include "AudioTask.h"

#include <Arduino.h>
#include "freertos/FreeRTOS.h" // Core FreeRTOS configuration headers
#include "freertos/task.h"     // Enables multi-threaded task creation and management

#include "FMSynth.h"    // Gives access to the FMSynth class
#include "I2SOutput.h"  // Gives access to writeAudio() for hardware I2S DMA streaming

#define BLOCK_SIZE 512 // Processing size: 512 stereo audio frames per processing block

// Instantiates the synth engine statically. This ensures it is allocated in global 
// memory and remains alive for the entire duration of the application execution.
static FMSynth synth;

/**
 * The infinite worker loop executed by the FreeRTOS thread.
 * 'parameter' is a mandatory void pointer required by FreeRTOS task signatures.
 */
void audioTask(void* parameter)
{
    // Allocate two separate memory blocks. They are marked 'static' so they reside 
    // in the global BSS memory segment rather than the limited 8KB task stack, 
    // completely preventing stack overflow crashes.
    static int16_t bufferA[BLOCK_SIZE * 2]; // 512 frames * 2 channels (Stereo) = 1024 samples
    static int16_t bufferB[BLOCK_SIZE * 2]; // Alternate buffer for ping-pong double buffering

    // Pointer tracking which buffer is currently being processed and written
    int16_t* current = bufferA;

    // Real-time tasks in FreeRTOS must never return; they run in an infinite loop
    while (true)
    {
        // 1. Render the audio block: Synthesizes 512 frames of digital audio into the current buffer
        synth.generateBlock(
            current,
            BLOCK_SIZE
        );

        // 2. Output to hardware: Sends the generated raw PCM bytes to the I2S DMA engine.
        // This function typically blocks the thread when the I2S hardware queue is full,
        // acting as the natural clock/governor for this entire execution loop.
        writeAudio(
            current,
            sizeof(bufferA) // Pass the buffer size in bytes (1024 samples * 2 bytes per sample = 2048 bytes)
        );

        // 3. Double-Buffering Switch: Ping-pong between buffer A and buffer B.
        // While the I2S hardware finishes draining the active buffer, the synth can 
        // begin preparing audio inside the alternate buffer slot.
        if (current == bufferA)
            current = bufferB;
        else
            current = bufferA;
    }
}

/**
 * Spawns the audio thread and pins it directly to a specific ESP32 hardware core.
 */
void startAudioTask()
{
    // FreeRTOS function to create a thread bound permanently to a specific CPU core
    xTaskCreatePinnedToCore(
        audioTask,       // Pointer to the function containing the infinite task loop
        "Audio",         // Text name for the task (useful for debugging/profiling tools)
        8192,            // Stack size allocated to this task in bytes
        nullptr,         // Input parameters to pass into the task function (none needed)
        24,              // Task Priority: 24 is extremely high (Max is usually 25). 
                         // This guarantees audio processing preempts almost everything else.
        nullptr,         // Task handle pointer (Not required here as we don't plan to delete it)
        1                // Core ID: Pin this task strictly to CPU Core 1
    );
}