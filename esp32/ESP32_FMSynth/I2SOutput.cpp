#include "driver/i2s.h" // ESP-IDF framework driver
#include "I2SOutput.h"

#define I2S_BCK  26  // Bit Clock (BCLK): Clocks each individual bit of audio data
#define I2S_WS   25  // Word Select (WCLK / LRCK): Dictates Left channel vs Right channel
#define I2S_DATA 22  // Serial Data (DIN / DOUT): Raw line carrying 16-bit audio bits


void initI2S()
{
    // Configuration structure defining how the hardware subsystem behaves
    i2s_config_t config =
    {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX), // Set the device as the Master Clock provider and configure it to Transmit (TX) audio
        .sample_rate = 44100, // Set the target sampling rate to match our FMSynth processing block
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT, // Communicate using signed 16-bit integers (-32768 to 32767)
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // Setup standard stereo channel layout
        .communication_format = I2S_COMM_FORMAT_STAND_I2S, // Use standard Philips I2S communication protocol rules
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1, // Allocate a low-priority interrupt level for background buffer switching
        .dma_buf_count = 8, // DMA Buffer Strategy: Create a ring-buffer pipeline of 8 discrete queues
        .dma_buf_len = 512, // Each individual DMA queue slot holds 512 audio frames
        .use_apll = true // High-Fidelity Clock: Enable the dedicated Audio Phase-Locked Loop (APLL). Generates integer-accurate internal audio frequencies, eliminating sample rate drift.
    };

    // Mapping structure matching the configuration variables to physical silicon pins
    i2s_pin_config_t pins =
    {
        .bck_io_num   = I2S_BCK,
        .ws_io_num    = I2S_WS,
        .data_out_num = I2S_DATA,
        .data_in_num  = I2S_PIN_NO_CHANGE // Disable audio input features since this is a pure synth
    };

    // 1. Install the driver using configuration settings into I2S Hardware Port 0
    i2s_driver_install(
        I2S_NUM_0,  // Hardware peripheral ID 0
        &config,    // Configurations defined above
        0,          // Event queue handle size (not utilizing background events)
        nullptr     // Event queue pointer (not needed)
    );

    // 2. Apply pin layout map to the newly initialized hardware port
    i2s_set_pin(
        I2S_NUM_0,
        &pins
    );
}

/**
 * Transfers completed audio synthesis buffers straight to the hardware layer.
 */
void writeAudio(
    int16_t* buffer,
    size_t sizeInBytes
)
{
    size_t written; // Local storage variable required by ESP-IDF to track successful byte transmissions

    // Push the raw buffer memory over to the DMA system.
    i2s_write(
        I2S_NUM_0,      // Target hardware port
        buffer,         // Pointer to raw data array
        sizeInBytes,    // Total payload size measured specifically in BYTES
        &written,       // Address for tracking storage execution
        portMAX_DELAY   // FreeRTOS Governor: Block and suspend this thread infinitely 
                        // if the hardware ring-buffers are completely full.
    );
}