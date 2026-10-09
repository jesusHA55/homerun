import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Card } from "../components/ui";
import type { SystemStatus } from "../types";

type Props = { system: SystemStatus | null; refresh: () => void };
type MotionEvent = { id: number; ts: number; snapshot_path: string | null; clip_path: string | null; area: number };

export default function Camera({ system, refresh }: Props) {
  const [events, setEvents] = useState<MotionEvent[]>([]);
  const mode = system?.camera.mode ?? "manual";
  const camera = system?.camera;

  useEffect(() => {
    api
      .events()
      .then((e) => setEvents(((e as { motion: MotionEvent[] }).motion) || []))
      .catch(() => {});
  }, [mode]);

  const switchMode = async (next: string) => {
    await api.setCameraMode(next);
    refresh();
  };

  return (
    <div className="grid">
      <Card
        title="Live view"
        action={
          <div className="row tight">
            <Button small active={mode === "manual"} onClick={() => switchMode("manual")}>
              manual
            </Button>
            <Button small active={mode === "motion"} onClick={() => switchMode("motion")}>
              motion
            </Button>
          </div>
        }
      >
        <img className="cam" src={api.streamUrl()} alt="live" />
        <div className="row between" style={{ marginTop: 12 }}>
          <span className="muted mono">
            {camera?.backend ?? "none"} · {camera?.available ? "streaming" : camera?.last_error ?? "unavailable"}
          </span>
          <Button small onClick={() => window.open(api.snapshotUrl(true), "_blank")}>
            Save snapshot
          </Button>
        </div>
      </Card>

      <Card title="Motion events">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Area</th>
              <th>Snapshot</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td className="muted">{new Date(event.ts * 1000).toLocaleString()}</td>
                <td className="mono">{Math.round(event.area)}</td>
                <td className="mono">{event.snapshot_path ? event.snapshot_path.split("/").pop() : "—"}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
                  no motion events yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      {!camera?.motion_available && (
        <p className="muted">
          Motion detection needs OpenCV on the backend (install the backend with its
          dependencies). Manual streaming works regardless.
        </p>
      )}
    </div>
  );
}
