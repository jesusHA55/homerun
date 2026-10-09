const TOKEN_KEY = "homerun_token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* not json */
    }
    throw new Error(detail);
  }
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return (await res.json()) as T;
  return res as unknown as T;
}

const post = <T = unknown>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  system: () => request("/api/system"),
  events: () => request("/api/events"),

  climate: () => request("/api/climate"),
  setClimate: (body: unknown) => post("/api/climate", body),

  plants: () => request("/api/plants"),
  water: (seconds: number) => post("/api/plants/water", { seconds }),
  stopWater: () => post("/api/plants/stop", {}),
  setSchedule: (body: unknown) => post("/api/plants/schedule", body),

  cameraStatus: () => request("/api/camera/status"),
  setCameraMode: (mode: string) => post("/api/camera/mode", { mode }),
  snapshotUrl: (save = false) => `/api/camera/snapshot?save=${save}&t=${Date.now()}`,
  streamUrl: () => "/api/camera/stream",

  chat: (message: string) => post("/api/chat", { message }),
  chatHistory: () => request("/api/chat/history"),
};
