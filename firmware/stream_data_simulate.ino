// This version of firmware now:
// Receives pre-recorded ECG data from the host device.
// Packetizes the data with the following format: [Header1, Header2, Packet ID, Timestamp, Samples, End Marker]
// Streams the data packet back to the host device. 


#define HEADER_1 0xAA
#define HEADER_2 0x55
#define END_MARKER 0xFF  // placeholder to indicate packet end
#define LED_PIN 2
// #define SAMPLES_PER_PACKET 10
const uint8_t PACKET_SAMPLES = 10;
uint8_t packet_id = 0;  
uint16_t packet_buffer[PACKET_SAMPLES]; // buffer for samples that are being streamed, creates allocation in RAM
uint8_t sample_index = 0;
String cmd_buffer = "";
bool streaming = false;


void startStreaming() {
    packet_id = 1;    // reset packet ID
    sample_index = 0; // reset sample buffer index
    streaming = true;

    // DEBUG: Confirm function was called
    digitalWrite(LED_PIN, HIGH);  // Turn LED on when START received
    delay(500);
    digitalWrite(LED_PIN, LOW);
    delay(500);
    digitalWrite(LED_PIN, HIGH);  // Blink twice
    delay(500);
    digitalWrite(LED_PIN, LOW);
}

// fill temporary 10-sample buffer with values streamed via UART
void fillBufferFromUART() {
    while (Serial.available() >= 2) {  // at least 2 bytes for one sample
        // Read 2 bytes from UART and combine into a 16-bit value
        uint16_t sample = Serial.read();           // LSB
        sample |= (Serial.read() << 8);           // MSB, little-endian

        // Store sample in buffer
        packet_buffer[sample_index++] = sample;

        // when buffer full, build and send packet
        if (sample_index >= PACKET_SAMPLES) {
            sendPacket(packet_buffer);  // send current buffer as a packet
            sample_index = 0;           // reset buffer index for next packet
        }
    }
}


void sendPacket(uint16_t *data) {
  // Calculate total packet size
  // Header (2) + Packet ID (1) + Timestamp (4) + 10 samples (20) + End marker (1) = 28 bytes
  const uint8_t packet_size = 2 + 1 + 4 + (PACKET_SAMPLES * 2) + 1;
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
    memcpy(&packet[index], &data[i], sizeof(uint16_t));
    index += sizeof(uint16_t);
  }

  // assign end marker to last byte, 28
  packet[index++] = END_MARKER;

  // send entire packet at once
  Serial.write(packet, sizeof(packet));

  // ---------- DEBUG PRINT ----------
    // Serial.print("Packet ID: ");
    // Serial.print(packet_id - 1);
    // Serial.print(", Timestamp: ");
    // Serial.print(timestamp);
    // Serial.print(", Samples: ");
    // for (uint8_t i = 0; i < PACKET_SAMPLES; i++) {
    //     Serial.print(data[i]);
    //     Serial.print(" ");
    // }
    // Serial.println();
}

void setup() {
  // put your setup code here, to run once:
  Serial.setRxBufferSize(4096);
  Serial.begin(115200);
   // Set the receive buffer size to 2048 bytes
  pinMode(LED_PIN, OUTPUT);
  //startStreaming();

}

void loop() {
  // put your main code here, to run repeatedly:
  if (!streaming) {
        while (Serial.available()) {
            char c = Serial.read();
            if (c == '\n') {
                if (cmd_buffer == "START") {
                    
                    startStreaming();
                }
                cmd_buffer = "";
                break;  // Exit command reading immediately
            } else {
                cmd_buffer += c;
            }
        }
    }
  

  if (streaming) {
    static unsigned long lastActivity = millis();
        
        if (Serial.available() >= 2) {
            lastActivity = millis();
            fillBufferFromUART();
        } else {
            // If no data for 3 seconds, assume done and reset
            if (millis() - lastActivity > 3000) {
                streaming = false;
                sample_index = 0;
            }
        }
    }
  

  // static unsigned long lastBlink = 0;
  // if (millis() - lastBlink >= 1000) {  // every 1 second
  //   digitalWrite(LED_PIN, !digitalRead(LED_PIN));  // toggle LED
  //   lastBlink = millis();
  // }
}
