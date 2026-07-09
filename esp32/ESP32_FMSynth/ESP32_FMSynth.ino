#include <Arduino.h>

#include "Parameters.h"
#include "I2SOutput.h"
#include "AudioTask.h"
#include "NetworkController.h"


void setup()
{
    Serial.begin(115200);

    initParameters();

    initI2S();

    initNetwork();

    startAudioTask();
}


void loop()
{
    networkUpdate();

    delay(1);
}