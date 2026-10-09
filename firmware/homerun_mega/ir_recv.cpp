#include "config.h"
#include "ir_recv.h"

// A Qlima/Carrier frame is ~200 edges; leave headroom.
#define IR_MAX_EDGES 260
// End-of-frame detection: receiver idle longer than this (us).
#define IR_FRAME_GAP_US 20000UL

static volatile uint16_t s_dur[IR_MAX_EDGES];
static volatile uint16_t s_len = 0;
static volatile unsigned long s_lastMicros = 0;
static volatile bool s_ready = false;
static volatile bool s_suspended = false;

static uint16_t s_frame[IR_MAX_EDGES];
static uint16_t s_frameLen = 0;

// TSOP demodulator output is idle HIGH and goes LOW for a burst.
static void irISR() {
  if (s_suspended || s_ready) return;

  unsigned long now = micros();
  if (s_len == 0) {
    if (digitalRead(PIN_IR_RECV) != LOW) return;  // not the leading active edge
    s_lastMicros = now;
    return;
  }

  unsigned long d = now - s_lastMicros;
  s_lastMicros = now;
  if (s_len < IR_MAX_EDGES) {
    s_dur[s_len++] = (uint16_t)(d > 65000UL ? 65000UL : d);
  }
}

void irrecv_begin() {
  pinMode(PIN_IR_RECV, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_IR_RECV), irISR, CHANGE);
}

void irrecv_update() {
  if (s_ready || s_len <= 4) return;
  if ((micros() - s_lastMicros) < IR_FRAME_GAP_US) return;

  noInterrupts();
  s_frameLen = s_len;
  for (uint16_t i = 0; i < s_frameLen; i++) s_frame[i] = s_dur[i];
  s_len = 0;
  s_ready = true;
  interrupts();
}

bool irrecv_available() { return s_ready; }
uint16_t irrecv_length() { return s_frameLen; }
const uint16_t* irrecv_buffer() { return s_frame; }

void irrecv_resume() {
  s_ready = false;
  s_len = 0;
}

void irrecv_suspend() {
  s_suspended = true;
  s_len = 0;
}

void irrecv_unsuspend() {
  s_suspended = false;
  s_len = 0;
  s_lastMicros = micros();
}
