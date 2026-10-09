import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { useWebSocket } from "./useWebSocket";
import type { SystemStatus } from "./types";
import Dashboard from "./pages/Dashboard";
import Climate from "./pages/Climate";
import Plants from "./pages/Plants";
import Camera from "./pages/Camera";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";

const TABS = [
  ["dashboard", "Dashboard"],
  ["climate", "Climate"],
  ["plants", "Plants"],
  ["camera", "Camera"],
  ["chat", "Assistant"],
  ["settings", "Settings"],
] as const;

export default function App() {
  const [tab, setTab] = useState<string>("dashboard");
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setSystem((await api.system()) as SystemStatus);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  useWebSocket((msg) => {
    if (msg.type === "telemetry") {
      setSystem((prev) => (prev ? { ...prev, device_connected: true, state: msg.data } : prev));
    } else {
      refresh();
    }
  });

  const online = !!system?.device_connected;

  return (
    <div className="app">
      <div className="topbar">
        <h1>Homerun</h1>
        <span className="pill">
          <span className={`dot ${online ? "ok" : ""}`} />
          {online ? "device online" : "device offline"}
        </span>
        <span className="spacer" />
        <nav className="nav">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </div>

      {error && <p className="error">API error: {error}</p>}

      {tab === "dashboard" && <Dashboard system={system} refresh={refresh} />}
      {tab === "climate" && <Climate system={system} refresh={refresh} />}
      {tab === "plants" && <Plants system={system} refresh={refresh} />}
      {tab === "camera" && <Camera system={system} refresh={refresh} />}
      {tab === "chat" && <Chat />}
      {tab === "settings" && <Settings system={system} />}
    </div>
  );
}
