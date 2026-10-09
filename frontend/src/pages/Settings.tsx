import { useState } from "react";
import { getToken, setToken } from "../api";
import { Button, Card } from "../components/ui";
import type { SystemStatus } from "../types";

export default function Settings({ system }: { system: SystemStatus | null }) {
  const [token, setLocalToken] = useState(getToken());
  const [saved, setSaved] = useState(false);

  return (
    <div className="grid">
      <Card title="Access token">
        <p className="muted">
          Leave empty while on a trusted LAN. Set the same value as
          <span className="mono"> HOMERUN_AUTH_TOKEN</span> on the backend before exposing
          Homerun beyond your network.
        </p>
        <div className="row" style={{ marginTop: 12 }}>
          <input
            style={{ flex: 1 }}
            placeholder="token"
            value={token}
            onChange={(e) => {
              setLocalToken(e.target.value);
              setSaved(false);
            }}
          />
          <Button
            kind="primary"
            onClick={() => {
              setToken(token.trim());
              setSaved(true);
            }}
          >
            Save
          </Button>
        </div>
        {saved && <p className="muted">saved.</p>}
      </Card>

      <Card title="System">
        <table>
          <tbody>
            <tr>
              <td className="muted">Device</td>
              <td>{system?.device_connected ? "connected" : "offline"}</td>
            </tr>
            <tr>
              <td className="muted">Camera backend</td>
              <td className="mono">{system?.camera.backend ?? "—"}</td>
            </tr>
            <tr>
              <td className="muted">Camera mode</td>
              <td className="mono">{system?.camera.mode ?? "—"}</td>
            </tr>
            <tr>
              <td className="muted">Motion detection</td>
              <td>{system?.camera.motion_available ? "available" : "unavailable"}</td>
            </tr>
            <tr>
              <td className="muted">Ollama</td>
              <td className="mono">
                {system?.ollama.enabled ? system.ollama.model : "disabled"}
              </td>
            </tr>
            <tr>
              <td className="muted">Flow total</td>
              <td className="mono">{system?.state.flow_total_l ?? 0} L</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
}
