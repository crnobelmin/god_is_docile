#include "I2SOutput.h"

#include "driver/i2s.h"



#define I2S_BCK 26
#define I2S_WS 25
#define I2S_DATA 22


void initI2S()
{

    i2s_config_t config =
    {
        .mode =
        (i2s_mode_t)
        (I2S_MODE_MASTER |
         I2S_MODE_TX),

        .sample_rate = 44100,

        .bits_per_sample =
        I2S_BITS_PER_SAMPLE_16BIT,

        .channel_format =
        I2S_CHANNEL_FMT_RIGHT_LEFT,

        .communication_format =
        I2S_COMM_FORMAT_STAND_I2S,

        .intr_alloc_flags =
        ESP_INTR_FLAG_LEVEL1,

        .dma_buf_count = 8,

        .dma_buf_len = 512,

        .use_apll = true
    };


    i2s_pin_config_t pins =
    {
        .bck_io_num = I2S_BCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_DATA,
        .data_in_num =
        I2S_PIN_NO_CHANGE
    };


    i2s_driver_install(
        I2S_NUM_0,
        &config,
        0,
        nullptr
    );


    i2s_set_pin(
        I2S_NUM_0,
        &pins
    );
}



void writeAudio(
    int16_t* buffer,
    size_t samples
)
{
    size_t written;

    i2s_write(
        I2S_NUM_0,
        buffer,
        samples,
        &written,
        portMAX_DELAY
    );
}