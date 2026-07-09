#include "AudioTask.h"

#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "FMSynth.h"
#include "I2SOutput.h"



#define BLOCK_SIZE 512


static FMSynth synth;



void audioTask(void* parameter)
{

    static int16_t bufferA[BLOCK_SIZE*2];
    static int16_t bufferB[BLOCK_SIZE*2];


    int16_t* current =
        bufferA;



    while(true)
    {

        synth.generateBlock(
            current,
            BLOCK_SIZE
        );


        writeAudio(
            current,
            sizeof(bufferA)
        );


        if(current==bufferA)
            current=bufferB;
        else
            current=bufferA;

    }
}




void startAudioTask()
{

    xTaskCreatePinnedToCore(
        audioTask,
        "Audio",
        8192,
        nullptr,
        24,
        nullptr,
        1
    );

}