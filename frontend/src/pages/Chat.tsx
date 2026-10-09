import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Button, Card } from "../components/ui";
import type { ChatMessage } from "../types";

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .chatHistory()
      .then((h) =>
        setMessages(
          (h as { role: ChatMessage["role"]; content: string }[]).map((m) => ({
            role: m.role,
            content: m.content,
          }))
        )
      )
      .catch(() => {});
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, busy]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = (await api.chat(text)) as { reply: string; actions: ChatMessage["actions"] };
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, actions: res.actions }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ ${(err as Error).message}` },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Assistant">
      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && (
          <p className="muted">
            Ask things like “set the AC to 22 degrees” or “water the plants for 15 seconds”.
          </p>
        )}
        {messages.map((message, index) => (
          <div key={index} className={`msg ${message.role}`}>
            {message.content}
            {message.actions && message.actions.length > 0 && (
              <div className="actions">
                {message.actions.map((action, actionIndex) => (
                  <div key={actionIndex}>
                    → {action.tool}({JSON.stringify(action.args)})
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant muted">thinking…</div>}
      </div>
      <div className="row" style={{ marginTop: 14 }}>
        <input
          style={{ flex: 1 }}
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <Button kind="primary" onClick={send} disabled={busy}>
          Send
        </Button>
      </div>
    </Card>
  );
}
