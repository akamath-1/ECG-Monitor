// ESP32 ECG Streaming Firmware - BLE Version
// Firmware for ESP32 to collect signal from AD8232 from GPIO 34 and stream it to host device
// via BLE.

// Waits for "START" command from Python script, then streams data at 250Hz
// Stops when "STOP" command received or connection lost

// Notes:
// FIRMWARE READS FROM GPIO 34 ON THE MCU TO COLLECT ANALOG SIGNAL FROM AD8232
// LO+ AND LO- ON AD8232 ARE CONNECTED TO GPIO 13 AND 14 ON MCU (logic not included for checking these readings for now)
// SAMPLING RATE IS 250HZ (change as desired)
// DURATION IS PYTHON-CONTROLLED (no hardcoded time limit)

// Note: This version uses BINARY data format instead of UTF-8 text (like the USB version).
// Reasoning:
//   - Efficiency: 500 bytes (binary) vs ~2000+ bytes (text) for 250 samples
//   - Better BLE MTU utilization (fits in 2-3 notifications vs 5-10+)

// Data format: 250 uint16_t values per notification (500 bytes, little-endian)
// Python unpacks using: struct.unpack('<250H', data)


#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>

// ====== VARIABLES FOR BLE ========================================================================================
BLEServer* pServer  = nullptr;
BLECharacteristic* pDataChar = nullptr;  // NOTIFY (both modes share this)
BLECharacteristic* pCommandChar = nullptr;  // WRITE for commands

#define ECG_SERVICE_UUID "fa75e591-ba7c-4779-938d-4c5bcc3a431f"
#define ECG_DATA_CHARACTERISTIC_UUID "3f433ab7-4887-4b25-a57a-793cd0fdb3c2" // NOTIFY
#define ECG_COMMAND_CHARACTERISTIC_UUID "221f81c7-09ed-4af7-be04-e08033dd979f" // WRITE

bool deviceConnected = false;
const int sampling_freq = 250;
const int BLE_BUFFER_SAMPLES = 250;
uint16_t ble_buffer[BLE_BUFFER_SAMPLES];
int sample_index = 0;

// ========== HARDWARE CONFIGURATION ==========
const int ECG_OUT_PIN = 34;   // AD8232 analog output
const int LO_PLUS_PIN = 13;   // AD8232 LO+ (leads-off detection)
const int LO_MINUS_PIN = 14;  // AD8232 LO- (leads-off detection)
const int LED_PIN = 2;        // Built-in LED for status

// --- SAMPLING CONFIGURATION ---
const int FS = 250;                              // Sampling frequency (Hz)
const unsigned long SAMPLE_INTERVAL_US = 4000;   // 4000 microseconds = 250Hz

// --- STATE VARIABLES ---
bool is_recording = false;
unsigned long sample_count = 0;
unsigned long last_sample_time = 0;
// ====================================================================================================================================


// =========================================
// BLE Server callbacks (connect/disconnect)
// =========================================
class ECGServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("Client connected.");
  }

  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    is_recording = false;
    Serial.println("Client disconnected.");
    BLEDevice::startAdvertising();  // allow reconnection
  }
};

// =========================================
// Command characteristic callbacks
// Commands: START_SIMPLE, STOP_SIMPLE, START_STREAM, STOP_STREAM
// =========================================
class CommandCallbacks : public BLECharacteristicCallbacks {
// onWrite, onNotify, onRead, onStatus

  void onWrite(BLECharacteristic* pCharacteristic) override {
    String rxValue = pCommandChar->getValue(); //get value that has been transmitted to ESP32 (Characteristic 2)
    if (rxValue.length() == 0) return;

    Serial.print("Command received over BLE: ");
    Serial.println(rxValue);

   
    if (rxValue == "START") {
      // Enable stream mode, disable simple mode
      is_recording = true;
      digitalWrite(LED_PIN, HIGH);
      Serial.println("STARTING STREAMING");
    }
    else if (rxValue == "STOP") {
      is_recording = false;
      digitalWrite(LED_PIN, LOW);
      Serial.println("STOPPING STREAMING");
    }
    
  }
};



void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  // Set ADC resolution
  analogReadResolution(12);
  
  // Configure pins
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  


  // =========== BLE SETUP ==========================================================================================
  // initialize the server/device "ECG Monitor ESP32"
  BLEDevice::init("ECG Monitor ESP32");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ECGServerCallbacks()); 
  BLEDevice::setMTU(512);  // Request larger MTU (max 512 for ESP32)



  // initialize the service of the server/device (ECG Monitor Service 1)
  BLEService *pService = pServer->createService(ECG_SERVICE_UUID);
  Serial.println("Service: ECG Monitor Service");
  Serial.print("  UUID: ");
  Serial.println(ECG_SERVICE_UUID);

  // -----------------------------------------
  // Data characteristic (NOTIFY) - shared for both modes
  // -----------------------------------------
  pDataChar = pService->createCharacteristic(
      ECG_DATA_CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_NOTIFY
  );

  BLE2901* pDataDesc = new BLE2901();
  pDataDesc->setValue("ECG Test Data");
  pDataDesc->setAccessPermissions(ESP_GATT_PERM_READ);
  pDataChar->addDescriptor(pDataDesc);

  // CCCD for NOTIFY
  pDataChar->addDescriptor(new BLE2902());

  // -----------------------------------------
  // Command characteristic (WRITE) for all commands
  // -----------------------------------------
  pCommandChar = pService->createCharacteristic(
      ECG_COMMAND_CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_WRITE
  );

  BLE2901* pCmdDesc = new BLE2901();
  pCmdDesc->setValue("Commands (START_SIMPLE, STOP_SIMPLE, START_STREAM, STOP_STREAM)");
  pCmdDesc->setAccessPermissions(ESP_GATT_PERM_READ);
  pCommandChar->addDescriptor(pCmdDesc);

  pCommandChar->setCallbacks(new CommandCallbacks());

  // Start service
  pService->start();

  // Start advertising
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(ECG_SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.println("BLE advertising started. Ready for connection.");
  // =========================================================================================================================================================

  // DIAGNOSTIC: Print ESP32 reset reason
  esp_reset_reason_t reason = esp_reset_reason();
  Serial.print("RESET_REASON:");
  Serial.println(reason);
  
  // Print startup message with timestamp
  Serial.print("BOOT_TIME:");
  Serial.println(millis());
}


void loop() { 
  if (deviceConnected) {
    // Stream data if recording
    if (is_recording) {
        // Check if it's time for the next sample (every 4ms)
        if (micros() - last_sample_time >= SAMPLE_INTERVAL_US) {
        
        // Read ADC value
        int ecg_value = analogRead(ECG_OUT_PIN);
        
        ble_buffer[sample_index++] = ecg_value; 
        if (sample_index >= BLE_BUFFER_SAMPLES) { //send every 250samples
            pDataChar->setValue((uint8_t*)ble_buffer, BLE_BUFFER_SAMPLES * 2); // uint8_t buffer because
            // setValue requires a byte array, size = buffer * 2 because each sample is 2 bytes (500bytes total)
            pDataChar->notify();
            sample_index = 0; 
        } 
        
        // Update counters
        sample_count++;
        last_sample_time = micros();
        
        
        }
        }
    delay(1);
  }
}
