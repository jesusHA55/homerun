#include "config.h"
#include "climate_ir.h"
#include "ir_recv.h"

#include <HeatpumpIR.h>
#include <CarrierHeatpumpIR.h>
#include <string.h>

static IRSenderBitBang s_sender(PIN_IR_SEND);
static HeatpumpIR* s_hp = nullptr;

static ClimateState s_state = {false, "cool", 24, "auto", false};
static unsigned long s_lastSend = 0;

static volatile bool s_pendingRemote = false;
static ClimateState s_pending;

// Carrier MCA temperature nibble -> temperature (index + 17, 17..31).
static const uint8_t kTemps[15] = {0, 8, 12, 4, 6, 14, 10, 2, 3, 11, 9, 1, 5, 13, 7};

static int tempFromNibble(uint8_t nibble) {
  for (int i = 0; i < 15; i++) {
    if (kTemps[i] == nibble) return i + 17;
  }
  return -1;
}

static uint8_t modeConst(const char* m) {
  if (!strcmp(m, "auto")) return MODE_AUTO;
  if (!strcmp(m, "heat")) return MODE_HEAT;
  if (!strcmp(m, "dry")) return MODE_DRY;
  if (!strcmp(m, "fan")) return MODE_FAN;
  return MODE_COOL;
}

static uint8_t fanConst(const char* f) {
  if (!strcmp(f, "1") || !strcmp(f, "low")) return FAN_1;
  if (!strcmp(f, "2") || !strcmp(f, "med")) return FAN_2;
  if (!strcmp(f, "3") || !strcmp(f, "high")) return FAN_3;
  return FAN_AUTO;
}

void climate_begin() {
#if QLIMA_MODEL == 2
  s_hp = new Qlima2HeatpumpIR();
#else
  s_hp = new Qlima1HeatpumpIR();
#endif
  irrecv_begin();
}

bool climate_set(bool power, const char* mode, uint8_t temp, const char* fan,
                 char* err, size_t errlen) {
  if (temp < 17 || temp > 30) {
    snprintf(err, errlen, "temp out of range (17-30)");
    return false;
  }
  unsigned long now = millis();
  if (s_lastSend != 0 && (now - s_lastSend) < IR_SEND_MIN_GAP_MS) {
    snprintf(err, errlen, "rate limited, try again shortly");
    return false;
  }

  irrecv_suspend();
  s_hp->send(s_sender, power ? POWER_ON : POWER_OFF, modeConst(mode),
             fanConst(fan), temp, VDIR_AUTO, HDIR_AUTO);
  irrecv_unsuspend();

  s_state.power = power;
  strncpy(s_state.mode, mode, sizeof(s_state.mode) - 1);
  s_state.mode[sizeof(s_state.mode) - 1] = '\0';
  s_state.temp = temp;
  strncpy(s_state.fan, fan, sizeof(s_state.fan) - 1);
  s_state.fan[sizeof(s_state.fan) - 1] = '\0';
  s_state.valid = true;
  s_lastSend = now;
  return true;
}

ClimateState climate_get() { return s_state; }

void climate_update(unsigned long now) {
  (void)now;
  irrecv_update();
  if (!irrecv_available()) return;

  ClimateState decoded;
  if (climate_decode(irrecv_buffer(), irrecv_length(), &decoded)) {
    s_state = decoded;
    s_pending = decoded;
    s_pendingRemote = true;
  }
  irrecv_resume();
}

bool climate_take_remote_change(ClimateState* out) {
  if (!s_pendingRemote) return false;
  *out = s_pending;
  s_pendingRemote = false;
  return true;
}

bool climate_decode(const uint16_t* d, uint16_t len, ClimateState* out) {
  // Header mark + space, then 6 bytes (48 bits), mark ~600us, space 500 => 0,
  // 1560 => 1.
  if (len < 2 + 96) return false;
  uint16_t hdr = d[0];
  if (hdr < 3000 || hdr > 6000) return false;  // ~4510us expected

  uint16_t idx = 2;
  uint8_t data[6];
  for (int b = 0; b < 6; b++) {
    uint8_t v = 0;
    for (int bit = 0; bit < 8; bit++) {
      if ((uint16_t)(idx + 1) >= len) return false;
      uint16_t mark = d[idx++];
      uint16_t space = d[idx++];
      if (mark > 2200) return false;
      v = (uint8_t)((v << 1) | (space > 1000 ? 1 : 0));
    }
    data[b] = v;
  }

  // Carrier MCA / Qlima preamble and inverted-byte checksums.
  if (data[0] != 0x4D || data[1] != 0xB2) return false;
  if ((uint8_t)~data[2] != data[3]) return false;
  if ((uint8_t)~data[4] != data[5]) return false;

  out->power = (data[2] & 0x20) != 0;

  switch (data[4] & 0xF0) {
    case 0x00: strcpy(out->mode, "cool"); break;
    case 0x10: strcpy(out->mode, "auto"); break;
    case 0x30: strcpy(out->mode, "heat"); break;
    case 0x20: strcpy(out->mode, "dry"); break;  // dry / fan ambiguous
    default: strcpy(out->mode, "cool"); break;
  }

  int t = tempFromNibble(data[4] & 0x0F);
  out->temp = (t >= 17 && t <= 30) ? (uint8_t)t : 24;

  switch (data[2] & 0x0F) {
    case 0x01: strcpy(out->fan, "1"); break;
    case 0x02: strcpy(out->fan, "2"); break;
    case 0x04: strcpy(out->fan, "3"); break;
    default: strcpy(out->fan, "auto"); break;  // 0x05 auto, 0x00 dry-auto
  }

  out->valid = true;
  return true;
}
