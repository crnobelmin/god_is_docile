#include <WiFi.h>            // Core ESP32 Wi-Fi library
#include <WiFiUdp.h>         // UDP socket connections
#include <ArduinoJson.h>     // JSON parsing

#include "NetworkController.h" 
#include "Parameters.h"        

// Network credentials
const char* ssid = "Netmin";
const char* password = "Belminet";
#define RECEIVER_ID "R" // Red Receiver

// Create the UDP utility
WiFiUDP udp; 


static void processJsonPayload(const char* jsonBuffer)
{
    // Pre-allocate memory on the stack for the JSON tree
    StaticJsonDocument<512> json; 

    // Deserialize the JSON string into doc object
    DeserializationError err = deserializeJson(json, jsonBuffer);

    // Extract the JSON object assigned to this RECEIVER_ID
    JsonObject params = json[RECEIVER_ID];

    // Extract and store parameters
    float chanval = params["channel_value"] | 1.0f;
    float p1 = params["param_1"];
    
    synthParams.frequency.store(chanval);
    synthParams.modulation.store(p1); 
}

void initNetwork()
{
    Serial.print("Connecting to WiFi...");
    WiFi.begin(ssid, password);

    // Allow hardware to automatically handle re-connections seamlessly in the background
    WiFi.setAutoReconnect(true);

    // Block execution until connection is established
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected");
    Serial.print("Receiver ID: ");   Serial.println(RECEIVER_ID);
    Serial.print("IP address: ");    Serial.println(WiFi.localIP());
    Serial.print("UDP Port: ");      Serial.println(12345);

    // Bind UDP listener to port 12345
    udp.begin(12345);
}

/**
 * Regularly checks for incoming UDP packets. Call this inside your main loop.
 */
void networkUpdate()
{
    // Safety Connection Guard: If Wi-Fi drops, skip UDP checks and print an alert every 2 seconds
    if (WiFi.status() != WL_CONNECTED)
    {
        static uint32_t lastWarningTime = 0;
        if (millis() - lastWarningTime > 2000)
        {
            Serial.println("WiFi disconnected! Waiting for background auto-reconnect...");
            lastWarningTime = millis();
        }
        return; 
    }

    // Check if a network packet has arrived
    int packetSize = udp.parsePacket();
    if (!packetSize) 
    {
        return; // No packet available; exit early to keep the main loop fast
    }

    char buffer[512]; // Buffer allocation to store incoming packet characters

    // Read the packet contents into our buffer array
    int len = udp.read(buffer, sizeof(buffer) - 1);

    if (len <= 0) 
    {
        return; // Guard against read execution failures
    }

    buffer[len] = '\0'; // Append null-terminator to make it a valid C-string

    // ADJUSTMENT: The raw data handling is decoupled and delegated to our helper function
    processJsonPayload(buffer);
}