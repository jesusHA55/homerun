// Homerun Arduino Mega 2560 firmware.
//
// Responsibilities:
//   - IR climate control (Qlima SC-3525) + decoding the physical remote
//   - 5x capacitive soil moisture sensors, tank level, flow meter
//   - gravity-fed solenoid watering valve with safety cap + dead-man switch
//   - line-delimited JSON protocol over USB serial to the Raspberry Pi
#include "config.h"

#include "climate_ir.h"
#include "protocol.h"
#include "sensors.h"
#include "watering.h"

static unsigned long s_lastTelemetry = 0;

void setup() {
  sensors_begin();
  watering_begin();
  climate_begin();
  protocol_begin();
}

void loop() {
  unsigned long now = millis();

  protocol_poll();
  sensors_update(now);
  climate_update(now);
  watering_update(now);

  // Dead-man switch: close the valve if the Pi goes quiet.
  if (!protocol_link_alive() && watering_is_open()) {
    watering_stop();
  }

  if (now - s_lastTelemetry >= TELEMETRY_INTERVAL_MS) {
    s_lastTelemetry = now;
    protocol_send_telemetry();
  }
}
