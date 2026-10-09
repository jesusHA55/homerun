// Standalone IR probe.
//
//  1. Wire a TSOP38238 (or similar 38 kHz demodulator) to pin 19, VCC=5V, GND.
//  2. Flash this sketch and open the Serial Monitor at 115200.
//  3. Point the Qlima remote at the receiver and press On/Off, then change
//     the temperature / mode.
//
// The sketch prints the raw edge durations (microseconds) and a best-effort
// decode of the Qlima/Carrier MCA format. If a frame shows
// "QCDF ok" with sane values, the Homerun firmware can drive the A/C
// dynamically. If not, fall back to raw-code replay.

#include <Arduino.h>

#define PIN_IR_RECV 19
#define IR_MAX_EDGES 260
#define IR_FRAME_GAP_US 20000UL

static volatile uint16_t s_dur[IR_MAX_EDGES];
static volatile uint16_t s_len = 0;
static volatile unsigned long s_lastMicros = 0;
static volatile bool s_ready = false;

static uint16_t s_frame[IR_MAX_EDGES];
static uint16_t s_frameLen = 0;

static void irISR() {
  if (s_ready) return;
  unsigned long now = micros();
  if (s_len == 0) {
    if (digitalRead(PIN_IR_RECV) != LOW) return;
    s_lastMicros = now;
    return;
  }
  unsigned long d = now - s_lastMicros;
  s_lastMicros = now;
  if (s_len < IR_MAX_EDGES) {
    s_dur[s_len++] = (uint16_t)(d > 65000UL ? 65000UL : d);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_IR_RECV, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_IR_RECV), irISR, CHANGE);
  Serial.println(F("Homerun IR probe ready. Point the remote at the receiver."));
}

static const uint8_t kTemps[15] = {0, 8, 12, 4, 6, 14, 10, 2, 3, 11, 9, 1, 5, 13, 7};

static int tempFromNibble(uint8_t nibble) {
  for (int i = 0; i < 15; i++) {
    if (kTemps[i] == nibble) return i + 17;
  }
  return -1;
}

static void decode() {
  const uint16_t* d = s_frame;
  uint16_t len = s_frameLen;
  Serial.print(F("hdr="));
  Serial.print(d[0]);
  Serial.print(F(" "));
  if (len < 2 + 96) {
    Serial.println(F("QCDF: frame too short"));
    return;
  }
  uint16_t idx = 2;
  uint8_t data[6];
  for (int b = 0; b < 6; b++) {
    uint8_t v = 0;
    for (int bit = 0; bit < 8; bit++) {
      if ((uint16_t)(idx + 1) >= len) {
        Serial.println(F("QCDF: truncated"));
        return;
      }
      idx += 2;  // skip mark, use space below
      uint16_t space = d[idx - 1];
      v = (uint8_t)((v << 1) | (space > 1000 ? 1 : 0));
    }
    data[b] = v;
  }
  Serial.print(F("bytes="));
  for (int i = 0; i < 6; i++) {
    if (data[i] < 16) Serial.print('0');
    Serial.print(data[i], HEX);
    Serial.print(' ');
  }
  bool ok = data[0] == 0x4D && data[1] == 0xB2 &&
            (uint8_t)~data[2] == data[3] && (uint8_t)~data[4] == data[5];
  if (!ok) {
    Serial.println(F("-> not Qlima/Carrier MCA"));
    return;
  }
  bool power = (data[2] & 0x20) != 0;
  const char* mode = "cool";
  switch (data[4] & 0xF0) {
    case 0x10: mode = "auto"; break;
    case 0x30: mode = "heat"; break;
    case 0x20: mode = "dry"; break;
    case 0x00: mode = "cool"; break;
  }
  int t = tempFromNibble(data[4] & 0x0F);
  Serial.print(F("QCDF ok power="));
  Serial.print(power ? F("on") : F("off"));
  Serial.print(F(" mode="));
  Serial.print(mode);
  Serial.print(F(" temp="));
  Serial.println(t);
}

void loop() {
  if (!s_ready && s_len > 4 && (micros() - s_lastMicros) > IR_FRAME_GAP_US) {
    noInterrupts();
    s_frameLen = s_len;
    for (uint16_t i = 0; i < s_frameLen; i++) s_frame[i] = s_dur[i];
    s_len = 0;
    s_ready = true;
    interrupts();
  }

  if (s_ready) {
    Serial.print(F("RAW["));
    Serial.print(s_frameLen);
    Serial.print(F("]: "));
    for (uint16_t i = 0; i < s_frameLen; i++) {
      Serial.print(s_frame[i]);
      if (i + 1 < s_frameLen) Serial.print(',');
    }
    Serial.println();
    decode();
    s_ready = false;
    s_len = 0;
  }
}
