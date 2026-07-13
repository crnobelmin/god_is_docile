#include <WiFi.h>
#include <WiFiUdp.h>
#include <math.h>
#include "driver/i2s.h" // Native ESP32 hardware I2S driver

// --- NETWORK CONFIGURATION ---
const char* ssid     = "Netmin";
const char* password = "Belminet";
const unsigned int localUdpPort = 12345;

WiFiUDP udp;
char packetBuffer[255];

// --- HARDWARE PIN CONFIGURATION ---
const int MOTION_SENSOR_PIN = 13; 
const int LED_PIN           = 14; 

// --- I2S PCM5102A PIN MAPPING ---
const int I2S_BCK_PIN       = 26; // Bit Clock
const int I2S_LRCK_PIN      = 25; // Left/Right Clock (LCK)
const int I2S_DIN_PIN       = 22; // Data In

// --- AUDIO CONFIGURATION ---
const int SAMPLE_RATE       = 44100;
const float dt              = 1.0 / (float)SAMPLE_RATE; // Exact time step per sample

// --- PYTHON MATCHED SYNTHESIZER CONSTANTS ---
const float MIN_FREQ        = 130.0;    // Python: 130 Hz base
const float MAX_FREQ        = 500.0;    // Python: 500 Hz max
// Since the loop runs 44,100 times a second now, we make alpha tiny 
// for a silky-smooth ~50ms glide across network updates.
const float GLIDE_ALPHA     = 0.0005;   

// --- LFO CONFIGURATION ---
const float LFO_FREQ        = 3.5;       
const float LFO_BASE_DEPTH  = 15.0;

// --- FM SYNTHESIS PHASE ACCUMULATORS ---
float carrierBasePhase      = 0.0;
float modPhase              = 0.0;

// --- TIMING & FLOW REGULATORS ---
unsigned long lastMovementTime = 0;
int networkCheckCounter        = 0; // Throttles network tasks to save CPU

// --- STATE VARIABLES ---
float targetFreq            = MIN_FREQ;
float smoothedFreq          = MIN_FREQ;
float incomingNormalizedVal = 1.0; 

void initI2S() {
    // 1. Configure the I2S hardware settings
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX), // Master Transmitter
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,        // Standard 16-bit audio
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,        // Stereo Output
        .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false
    };

    // 2. Configure the physical pins
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCK_PIN,
        .ws_io_num = I2S_LRCK_PIN,
        .data_out_num = I2S_DIN_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    // 3. Enable the driver
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
}

void setup() {
    Serial.begin(115200);
    
    // For testing with a motion sensor
    pinMode(MOTION_SENSOR_PIN, INPUT);
    // For testing without a motion sensor:
    // pinMode(MOTION_SENSOR_PIN, INPUT_PULLDOWN);


    pinMode(LED_PIN, OUTPUT);
    
    // Initialize standard I2S pipeline
    initI2S();

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected!");

    // --- ADD THESE TWO LINES HERE ---
    Serial.print("Target this IP in Flask: ");
    Serial.println(WiFi.localIP());

    udp.begin(localUdpPort);
    lastMovementTime = millis();
}

void loop() {
    // =====================================================================
    // 1. THROTTLED NETWORK & SENSOR INGESTION (~every 10ms)
    // =====================================================================
    // Running UDP parsers 44,100 times a second will choke the CPU. 
    // We skip network checks for 441 samples to run it at a clean 10ms rhythm.
    networkCheckCounter++;
    if (networkCheckCounter >= 441) {
        networkCheckCounter = 0;

        int packetSize = udp.parsePacket();
        if (packetSize) {
            int len = udp.read(packetBuffer, 255);
            if (len > 0) packetBuffer[len] = 0;
            
            incomingNormalizedVal = atof(packetBuffer);
            if (incomingNormalizedVal > 1.0) incomingNormalizedVal = 1.0;
            if (incomingNormalizedVal < 0.0) incomingNormalizedVal = 0.0;

            // Python Step 1 Map: 130 + (val * 370)
            targetFreq = MIN_FREQ + (incomingNormalizedVal * (MAX_FREQ - MIN_FREQ));
            
            // Update LED Brightness once per network frame
            int pwmValue = (int)(incomingNormalizedVal * 255.0);
            analogWrite(LED_PIN, pwmValue); 
        }

        if (digitalRead(MOTION_SENSOR_PIN) == HIGH) {
            lastMovementTime = millis();
        }
    }

    // =====================================================================
    // 2. TIMING DELTA CALCULATIONS
    // =====================================================================
    float secondsSinceMovement = 0.0f;
    // =====================================================================
    // 3. CORE REAL-TIME FM SYNTH MATHEMATICS
    // =====================================================================
    // Creamy exponential portamento calculated per-sample
    smoothedFreq += (targetFreq - smoothedFreq) * GLIDE_ALPHA;

    // Vibrato LFO Calculation
    float lfoPhase = 0.0;
    lfoPhase += 2.0 * PI * LFO_FREQ * dt;
    if (lfoPhase > 2 * PI)
        lfoPhase -= 2 * PI;
    float lfoSignal = sin(lfoPhase);
    float dynamicLfoDepth = LFO_BASE_DEPTH * (secondsSinceMovement * 0.5);
    
    float currentCarrierFreq = smoothedFreq + (lfoSignal * dynamicLfoDepth);
    float currentModFreq     = currentCarrierFreq * 1.5; // Harmonic Perfect 5th Ratio
    float currentModIndex    = incomingNormalizedVal * 5.0; // Timbre intensity

    // Phase Accumulation using our fixed hardware time slice (dt)
    carrierBasePhase += 2.0 * PI * currentCarrierFreq * dt;
    modPhase         += 2.0 * PI * currentModFreq * dt;

    // Precision boundary reset
    if (carrierBasePhase > 2.0 * PI) carrierBasePhase -= 2.0 * PI;
    if (modPhase > 2.0 * PI)         modPhase         -= 2.0 * PI;

    // Pure Python-matched FM synthesis formula
    float totalPhase = carrierBasePhase + (currentModIndex * sin(modPhase));
    float audioSample = sin(totalPhase); // Continuous signal float (-1.0 to 1.0)

    // =====================================================================
    // 4. AUDIO HARDWARE DMA SHIFT (Stereo 16-Bit Signed Integer)
    // =====================================================================
    // Convert float to a standard 16-bit signed integer (-32768 to 32767)
    int16_t sampleOut = (int16_t)(audioSample * 32767.0);

    // Prepare a stereo audio frame array [Left Channel, Right Channel]
    int16_t stereoFrame[2];
    stereoFrame[0] = sampleOut; // Left data channel
    stereoFrame[1] = sampleOut; // Right data channel

    // Write data to the I2S peripheral. 
    // This blocks automatically if the DMA buffer is full, pacing the loop perfectly.
    size_t bytesWritten;
    i2s_write(I2S_NUM_0, &stereoFrame, sizeof(stereoFrame), &bytesWritten, portMAX_DELAY);
}