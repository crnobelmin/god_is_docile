#pragma once
#include <stdint.h>
#include <stddef.h>

/**
 * Initializes the I2S peripheral, configures the audio hardware registers,
 * allocates DMA buffers, and binds the physical output pins.
 */
void initI2S();

/**
 * Streams raw binary audio data out to the I2S hardware queue.
 * NOTE: 'sizeInBytes' represents the total size of the payload in bytes,
 * which matches the requirements of the underlying ESP-IDF driver.
 */
void writeAudio(
    int16_t* buffer,
    size_t sizeInBytes
);