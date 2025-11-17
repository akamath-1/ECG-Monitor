#define HEADER_1 0xAA
#define HEADER_2 0x55
#define END_MARKER 0xFF  // placeholder to indicate packet end
#define LED_PIN 2

// #define SAMPLES_PER_PACKET 10
const uint16_t heartbeat_signal[] = {};

const uint32_t heartbeat_length = sizeof(heartbeat_signal) / sizeof(heartbeat_signal[0]); //length of heartbeat_signal, should be 7500 (30 sec of data)

const uint8_t PACKET_SAMPLES = 10;
uint8_t packet_id = 0;  
uint16_t packet_buffer[PACKET_SAMPLES]; // buffer for samples that are being streamed, creates allocation in RAM
uint8_t sample_index = 0;
String cmd_buffer = "";
bool streaming = false;
const int trigger_output_pin = 26;
int total_sample_count = 0;

void startStreaming() {
    packet_id = 1;    // reset packet ID
    sample_index = 0; // reset sample buffer index
    total_sample_count = 0;
    streaming = true;

    // Send HIGH trigger pulse to signal generator
    digitalWrite(trigger_output_pin, HIGH);
    delay(100);  // Keep HIGH for 100ms
    digitalWrite(trigger_output_pin, LOW);  // Return to LOW


    // DEBUG: Confirm function was called
    digitalWrite(LED_PIN, HIGH);  // Turn LED on when START received
    delay(500);
    digitalWrite(LED_PIN, LOW);
    delay(500);
    digitalWrite(LED_PIN, HIGH);  // Blink twice
    delay(500);
    digitalWrite(LED_PIN, LOW);
}


void sendPacket(uint16_t *data) {
  // Calculate total packet size
  // Header (2) + Packet ID (1) + Timestamp (4) + 10 samples (20) + End marker (1) = 28 bytes
  const uint8_t packet_size = 2 + 1 + 4 + (PACKET_SAMPLES * 2) + 1; //make this PACKET_SAMPLES * 2 for 12 bit !!
  uint8_t packet[packet_size];
  uint8_t index = 0;
  
  // assign header to the first two bytes
  packet[index++] = HEADER_1;
  packet[index++] = HEADER_2;

  // assign packet ID to the third byte
  packet[index++] = packet_id;
  packet_id++;  // increment after assigning
  if (packet_id == 0) packet_id = 1;  // in case of overflow wrap

  // assign timestamp to bytes 4-7 (4 bytes, little-endian)
  unsigned long timestamp = millis();
  memcpy(&packet[index], &timestamp, sizeof(timestamp));
  index += sizeof(timestamp);

  // assign each of 10 signal values (2 bytes each) to bytes 8-27
  for (uint8_t i = 0; i < PACKET_SAMPLES; i++) {
    uint16_t sample = data[i] & 0x0FFF; // bit mask so only the 12bits are stored in a sample (optional but good to have)
    memcpy(&packet[index], &sample, sizeof(uint16_t));
    index += sizeof(uint16_t);
  }

  // assign end marker to last byte, 28
  packet[index++] = END_MARKER;

  // send entire packet at once
  //Serial.print(packet);
  Serial.write(packet, sizeof(packet));

  // Serial.print("Packet ID: ");
  // Serial.print(packet_id - 1);
  // Serial.print(" | Data: ");
  // for (uint8_t i = 0; i < packet_size; i++) {
  //     Serial.print(packet[i], HEX);
  //     Serial.print(" ");
  // }
  // Serial.println();

}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  // pinMode(34, INPUT);
  // // pinMode(26, OUTPUT);
  // // digitalWrite(26, LOW);
  // analogReadResolution(8);
  
  // DIAGNOSTIC: Print reset reason
  esp_reset_reason_t reason = esp_reset_reason();
  Serial.print("RESET_REASON:");
  Serial.println(reason);
  
  // Print startup message with timestamp
  Serial.print("BOOT_TIME:");
  Serial.println(millis());
}

void addADCSampleToBuffer() { 
  if (total_sample_count >= heartbeat_length) {
        streaming = false;
        return;
    }

  uint16_t sample = heartbeat_signal[total_sample_count];
  total_sample_count++;
  packet_buffer[sample_index++] = sample; 
  if (sample_index >= PACKET_SAMPLES) { 
    sendPacket(packet_buffer); 
    sample_index = 0; 
  } 
} 
  
void loop() { 
  if (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') { // end of command
      if (cmd_buffer == "START") {
        digitalWrite(trigger_output_pin, HIGH);
        startStreaming();
      }
      else if (cmd_buffer == "STOP") {
        digitalWrite(trigger_output_pin, LOW);
        streaming = false;
      }
      cmd_buffer = ""; // reset after each command
    } 
    else {
      cmd_buffer += c; // accumulate characters
    }
  }
  
  if (streaming) { 
    static unsigned long 
    last_sample_time = 0; 
    if (micros() - last_sample_time >= 4000) { 
      addADCSampleToBuffer(); 
      last_sample_time = micros(); 
    } 
  } 
}


