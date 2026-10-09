import { useEffect, useRef } from "react";

/** Subscribe to the backend WebSocket with automatic reconnect. */
export function useWebSocket(onMessage: (message: any) => void): void {
  const handler = useRef(onMessage);
  handler.current = onMessage;

  useEffect(() => {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    let socket: WebSocket | null = null;
    let closed = false;
    let retry: number | undefined;

    const connect = () => {
      socket = new WebSocket(`${protocol}://${location.host}/api/ws`);
      socket.onmessage = (event) => {
        try {
          handler.current(JSON.parse(event.data));
        } catch {
          /* ignore malformed */
        }
      };
      socket.onclose = () => {
        if (!closed) retry = window.setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      socket?.close();
    };
  }, []);
}
