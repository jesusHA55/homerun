export type Climate = {
  power: "on" | "off";
  mode: "auto" | "cool" | "heat" | "dry" | "fan";
  temp: number;
  fan: "auto" | "1" | "2" | "3";
};

export type DeviceState = {
  connected: boolean;
  last_seen: number | null;
  soil: number[];
  tank: number;
  flow_lpm: number;
  flow_total_l: number;
  valve_open: boolean;
  valve_remaining_ms: number;
  climate: Climate;
  last_watered_ts: number | null;
};

export type SystemStatus = {
  device_connected: boolean;
  state: DeviceState;
  camera: {
    available: boolean;
    backend: string;
    mode: "manual" | "motion";
    motion_available: boolean;
    last_error: string | null;
    has_frame: boolean;
  };
  ollama: { enabled: boolean; model: string };
};

export type PlantState = {
  zone: number;
  name: string;
  plants: number;
  soil: number[];
  soil_avg: number;
  tank: number;
  flow_lpm: number;
  flow_total_l: number;
  valve_open: boolean;
  valve_remaining_ms: number;
  last_watered_ts: number | null;
  threshold: number;
  target: number;
  schedule: {
    enabled: number | boolean;
    every_hours: number;
    duration_s: number;
    min_soil: number;
  };
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  actions?: { tool: string; args: Record<string, unknown>; result: unknown }[];
};
