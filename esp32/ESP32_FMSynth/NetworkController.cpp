// Single Value Processing
// #include "Network.h"

// #include <WiFi.h>
// #include <WiFiUdp.h>

// #include "Parameters.h"


// const char* ssid="Netmin";
// const char* password="Belminet";


// WiFiUDP udp;


// void initNetwork()
// {

//     WiFi.begin(
//         ssid,
//         password
//     );


//     while(WiFi.status()!=WL_CONNECTED)
//     {
//         delay(200);
//         Serial.print(".");
//     }

//     Serial.println();
//     Serial.println("WiFi connected");

//     Serial.print("ESP32 IP address: ");
//     Serial.println(WiFi.localIP());

//     Serial.print("UDP listening on port: ");
//     Serial.println(12345);


//     udp.begin(12345);
// }



// void networkUpdate()
// {

//     int size =
//         udp.parsePacket();


//     if(size)
//     {

//         char buffer[32];

//         int len =
//             udp.read(
//                 buffer,
//                 sizeof(buffer)-1
//             );


//         buffer[len]=0;


//         float value =
//             atof(buffer);



//         value =
//             constrain(
//                 value,
//                 0,
//                 1
//             );


//         synthParams.frequency.store(
//             130.0f +
//             value*370.0f
//         );


//         synthParams.modulation.store(
//             value*5.0f
//         );

//     }
// }










// JSON PROCESSING via broadcast

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

#include "NetworkController.h"
#include "Parameters.h"

const char* ssid = "Netmin";
const char* password = "Belminet";

// ----------------------------------------------------
// Change this for each ESP32
// ----------------------------------------------------
#define RECEIVER_ID "R"
// "G"
// "B"
// "L"

WiFiUDP udp;

void initNetwork()
{
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(200);
        Serial.print(".");
        WiFi.reconnect();
    }

    Serial.println();
    Serial.println("WiFi connected");

    Serial.print("Receiver ID: ");
    Serial.println(RECEIVER_ID);

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("UDP Port: ");
    Serial.println(12345);

    udp.begin(12345);
}

void networkUpdate()
{
    int packetSize = udp.parsePacket();

    if (!packetSize)
        return;

    char buffer[512];

    int len = udp.read(
        buffer,
        sizeof(buffer) - 1
    );

    if (len <= 0)
        return;

    buffer[len] = '\0';

    StaticJsonDocument<512> doc;

    DeserializationError err =
        deserializeJson(doc, buffer);

    if (err)
    {
        Serial.print("JSON Error: ");
        Serial.println(err.c_str());
        return;
    }

    //--------------------------------------------------
    // Optional sequence number
    //--------------------------------------------------

    uint32_t sequence =
        doc["seq"] | 0;

    (void)sequence;

    //--------------------------------------------------
    // Get this receiver's object
    //--------------------------------------------------

    JsonObject receiver =
        doc[RECEIVER_ID];

    if (receiver.isNull())
        return;

    //--------------------------------------------------
    // Read parameters
    //--------------------------------------------------

    float value =
        receiver["value"] | 1.0f;

    value = constrain(
        value,
        0.0f,
        1.0f
    );

    //--------------------------------------------------
    // Update lock-free synth parameters
    //--------------------------------------------------

    synthParams.frequency.store(
        130.0f +
        value * 370.0f
    );

    synthParams.modulation.store(
        value * 5.0f
    );

    //--------------------------------------------------
    // Future parameters
    //--------------------------------------------------

    // float volume =
    //     receiver["volume"] | 1.0f;

    // float lfoDepth =
    //     receiver["lfoDepth"] | 0.5f;

    // float fmIndex =
    //     receiver["fmIndex"] | 2.0f;

    // synthParams.volume.store(volume);
    // synthParams.lfoDepth.store(lfoDepth);
    // synthParams.fmIndex.store(fmIndex);
}