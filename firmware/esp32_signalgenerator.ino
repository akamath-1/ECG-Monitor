// ===============================================================
// Firmware: ESP32 Signal Generator MCU
// Description: Repeatedly streams hard-coded digital ECG values (one heartbeat, generated from Incentia dataset, 
// Patient P00000, through generate_dataset_esp32_sig_gen.py) from DAC to gateway (main) MCU. 
// Board: ESP32 DevKitC
// Role: Upstream data source for the system
// ===============================================================

const uint8_t heartbeat_signal[] = {115, 115, 115, 115, 115, 115, 115, 
115, 115, 115, 115, 115, 115, 115, 115, 115, 116, 116, 116, 117, 
118, 119, 120, 119, 118, 115, 112, 110, 109, 110, 112, 114, 115, 
115, 115, 115, 115, 115, 116, 116, 116, 115, 116, 116, 116, 116, 
116, 116, 116, 116, 116, 116, 116, 116, 116, 116, 117, 117, 117, 
117, 117, 117, 118, 118, 118, 118, 118, 119, 119, 119, 119, 119, 
119, 119, 119, 119, 119, 119, 119, 119, 119, 118, 118, 117, 117, 
117, 117, 116, 116, 116, 116, 116, 116, 116, 115, 115, 115, 115, 
115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 
115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 
115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115};

const int dac_pin = 25;
const int num_samples = sizeof(heartbeat_signal) / sizeof(heartbeat_signal[0]); 
const unsigned long SAMPLE_INTERVAL_US = 4000; // 4 ms → 250 Hz
//sizeof() returns # bytes - divide total bytes by byte # of one entry to get number of samples


void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  pinMode(dac_pin, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  
  static unsigned long last_sample_time = 0;
  static int i = 0;  // index into heartbeat_signal

  unsigned long now = micros();
  if (now - last_sample_time >= SAMPLE_INTERVAL_US) {
    uint8_t value = heartbeat_signal[i];
    dacWrite(dac_pin, value);

    // Optional: print to Serial Monitor for debugging
    //Serial.println(value);

    i = (i + 1) % num_samples;   // wrap around to loop waveform
    last_sample_time = now;   
  }
}
