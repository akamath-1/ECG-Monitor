
#define PACKET_SIZE 10
#define PACKETS 3

int packets = 0;
int bufferIndex = 0;
int buffer[PACKET_SIZE]; // you MUST either use #define or const in to initialize array size, int packet_size = 10 would not be allowed - 
// C++ requires these kinds of values to be known at compile time, whereas int packet_size is accessed only at runtime
// Other times to use constant values = pin assignment, protocol/hardware parameters (timing, sample rate), registers (?)
bool streaming = false;
int sampleCounter = 0;

void setup() {
  // put your setup code here, to run once:

  Serial.begin(115200); // establishes connection between laptop and MCU, send data bytes at rate of 115200 bits/sec
  delay(1000); // let serial initialize
  Serial.println("Serial test started");
}

int generateData(){
  sampleCounter++;
  return sampleCounter;
}

std::vector<float> p_wave(int n){
    std::vector<float> wave;
    wave.reserve(n);
    for (int i = 0; i < n; i++) {
    float t = M_PI * i / (n - 1);
    wave.push_back(0.25 * sin(t));  // mV
  }
  return wave;
    

def qrs_complex(n):
    q = int(n * 0.25)
    r = int(n * 0.5)
    s = n - q - r
    return np.concatenate([
        -0.1 * np.linspace(0, 1, q),
        np.linspace(-0.1, 1.0, r),
        np.linspace(1.0, 0, s)
    ])

def t_wave(n):
    t = np.linspace(0, np.pi, n)
    return 0.35 * np.sin(t)

# Flat segments
def flat(n):
    return np.zeros(n)

# Analog to Digital Conversion of voltage

def voltage_ADC(ecg):
    ecg_amplified_mV = ecg * 100 #amplify mV by 100x
    ecg_adjusted = ecg_amplified_mV/1000 + 1.5 #convert to V from mV, then add 1.5V to bring to baseline
    return ecg_adjusted

# --- Combine all segments ---
ecg = np.concatenate([
    p_wave(durations["P"]),
    flat(durations["PR"]),
    qrs_complex(durations["QRS"]),
    flat(durations["ST"]),
    t_wave(durations["T"]),
    flat(durations["TP"])
])
}
void addToPacket(int sample){
  buffer[bufferIndex] = sample;   // store in RAM buffer
  bufferIndex++;

  if (bufferIndex >= PACKET_SIZE) {
    // Buffer full → packet ready
    sendPacket();
    bufferIndex = 0; // reset for next packet
  }
}

void sendPacket(){
  //int num_of_packets = 1;
  String packetNum = String(packets);
  Serial.print("Packet " + packetNum + ": ");

  for (int i = 0; i < PACKET_SIZE; i++) {
    Serial.print(buffer[i]);
    Serial.print(" ");
  }
  Serial.println();
  //num_of_packets++;
  packets++;
}
void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available()){
    String cmd = Serial.readStringUntil('\n');  // read until newline
    cmd.trim();                                 // remove extra whitespace

    if (cmd == "START") {
      streaming = true;
      packets = 1;
      bufferIndex = 0;
      sampleCounter = 0;
      Serial.println("Streaming started");
    } 
    else if (cmd == "STOP") {
      streaming = false;
      Serial.println("Streaming stopped");
    }

  }  

  if (streaming) {

    if (packets < PACKETS){
      int sample = generateData();
      // Store it in a packet buffer
      addToPacket(sample);
      // Simple wait to slow down generation for testing
      delay(100);  // 10 Hz; you can adjust later
    }
    else {
      streaming = false;
      Serial.println("Finished printing all packets.");

    }
  }


}
