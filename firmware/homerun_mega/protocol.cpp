#include "config.h"
#include "protocol.h"

#include "climate_ir.h"
#include "sensors.h"
#include "watering.h"

#include <ArduinoJson.h>
#include <string.h>

static unsigned long s_lastRxMs = 0;
static char s_buf[192];
static uint8_t s_len = 0;

static void sendJson(JsonDocument& doc) {
  serializeJson(doc, Serial);
  Serial.write('\n');
}

static void sendAck(long id, bool ok, const char* err = nullptr) {
  JsonDocument d;
  d["type"] = ok ? "ack" : "error";
  d["id"] = id;
  if (!ok && err) d["message"] = err;
  sendJson(d);
}

static void handleClimate(long id, JsonVariant params) {
  bool power;
  if (params["power"].is<bool>()) {
    power = params["power"].as<bool>();
  } else {
    const char* p = params["power"] | "on";
    power = strcmp(p, "off") != 0;
  }
  const char* mode = params["mode"] | "cool";
  uint8_t temp = params["temp"] | 24;
  const char* fan = params["fan"] | "auto";

  char err[48];
  if (climate_set(power, mode, temp, fan, err, sizeof(err))) {
    sendAck(id, true);
  } else {
    sendAck(id, false, err);
  }
}

static void handleLine(char* line) {
  JsonDocument doc;
  if (deserializeJson(doc, line)) return;  // ignore malformed lines

  const char* cmd = doc["cmd"] | "";
  long id = doc["id"] | -1L;
  JsonVariant params = doc["params"];

  if (!strcmp(cmd, "ping") || !strcmp(cmd, "sensor.read")) {
    sendAck(id, true);
  } else if (!strcmp(cmd, "climate.set")) {
    handleClimate(id, params);
  } else if (!strcmp(cmd, "valve.set")) {
    const char* state = params["state"] | "closed";
    watering_set_valve(strcmp(state, "open") == 0);
    sendAck(id, true);
  } else if (!strcmp(cmd, "water.run")) {
    if (sensors_tank_low()) {
      sendAck(id, false, "tank level too low");
    } else {
      unsigned long duration = params["duration_ms"] | 30000UL;
      watering_start(duration);
      sendAck(id, true);
    }
  } else if (!strcmp(cmd, "water.stop")) {
    watering_stop();
    sendAck(id, true);
  } else {
    sendAck(id, false, "unknown command");
  }
}

void protocol_begin() {
  Serial.begin(SERIAL_BAUD);
  s_lastRxMs = millis();
}

bool protocol_link_alive() { return (millis() - s_lastRxMs) < LINK_TIMEOUT_MS; }

void protocol_send_telemetry() {
  SensorReadings r = sensors_get();
  ClimateState c = climate_get();

  JsonDocument d;
  d["type"] = "telemetry";

  JsonArray soil = d["soil"].to<JsonArray>();
  for (uint8_t i = 0; i < SOIL_COUNT; i++) soil.add(r.soil[i]);

  d["tank_level"] = r.tank;
  d["flow_lpm"] = round(r.flow_lpm * 100.0f) / 100.0f;
  d["flow_total_l"] = round(r.flow_total_l * 100.0f) / 100.0f;
  d["valve"] = watering_is_open() ? 1 : 0;
  d["valve_remaining_ms"] = watering_remaining_ms();

  JsonObject cl = d["climate"].to<JsonObject>();
  cl["power"] = c.power ? "on" : "off";
  cl["mode"] = c.mode;
  cl["temp"] = c.temp;
  cl["fan"] = c.fan;

  d["uptime_ms"] = millis();
  sendJson(d);
}

static void pollRemote() {
  ClimateState c;
  if (!climate_take_remote_change(&c)) return;

  JsonDocument d;
  d["type"] = "climate_remote";
  JsonObject p = d["params"].to<JsonObject>();
  p["power"] = c.power ? "on" : "off";
  p["mode"] = c.mode;
  p["temp"] = c.temp;
  p["fan"] = c.fan;
  sendJson(d);
}

void protocol_poll() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (s_len > 0) {
        s_buf[s_len] = '\0';
        s_lastRxMs = millis();
        handleLine(s_buf);
        s_len = 0;
      }
    } else if (s_len < sizeof(s_buf) - 1) {
      s_buf[s_len++] = ch;
    } else {
      s_len = 0;  // drop overlong line
    }
  }
  pollRemote();
}
