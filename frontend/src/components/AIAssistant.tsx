/**
 * AIAssistant — Phase 4
 *
 * Chat panel wired to POST /assistant/chat.
 * Uses the existing rule-based assistant engine (no LLM required).
 * Generates contextual answers from root cause, timeline, maintenance,
 * and explainability data already in the backend.
 */

import { useState, useRef, useEffect } from "react";
import api from "../../services/api";

interface Message {
  role:    "user" | "assistant";
  text:    string;
  sources?: string[];
  actions?: string[];
  conf?:   number;
}

const SUGGESTIONS = [
  "Why is this vehicle critical?",
  "What is the failure risk?",
  "How many days until failure?",
  "What maintenance is needed?",
  "Show fleet summary",
];

interface Props {
  vehicleId: number;
  onClose:   () => void;
}

export default function AIAssistant({ vehicleId, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    text: `Hello! I'm TwinGuard AI. I'm monitoring Vehicle #${vehicleId}. Ask me anything about its health, failure risk, maintenance needs, or fleet status.`,
    actions: SUGGESTIONS.slice(0, 3),
  }]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      // Inject vehicle context into the message
      const contextualMsg = userMsg.match(/vehicle\s*\d+/i)
        ? userMsg
        : `${userMsg} (vehicle ${vehicleId})`;

      const { data } = await api.post("/assistant/chat", { message: contextualMsg });
      setMessages(prev => [...prev, {
        role:    "assistant",
        text:    data.answer,
        sources: data.sources,
        actions: data.suggested_actions?.slice(0, 3),
        conf:    data.confidence,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "I'm having trouble connecting to the AI engine. Please check the backend is running.",
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      position: "fixed", bottom: 20, right: 20, zIndex: 1000,
      width: 340, maxHeight: 520,
      background: "rgba(5,7,12,0.98)",
      border: "1px solid rgba(56,189,248,0.2)",
      borderRadius: 14,
      display: "flex", flexDirection: "column",
      boxShadow: "0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(56,189,248,0.05)",
      fontFamily: "system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 16px",
        borderBottom: "1px solid rgba(56,189,248,0.1)",
        background: "rgba(56,189,248,0.04)",
        borderRadius: "14px 14px 0 0",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: "linear-gradient(135deg, #38bdf8, #818cf8)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14,
          }}>🤖</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#e2e8f0" }}>TwinGuard AI</div>
            <div style={{ fontSize: 9, color: "#22c55e", display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />
              Online · Vehicle #{vehicleId}
            </div>
          </div>
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "none", color: "#475569",
          cursor: "pointer", fontSize: 16, padding: 4,
        }}>✕</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "88%",
              padding: "9px 12px",
              borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              background: msg.role === "user"
                ? "linear-gradient(135deg, rgba(56,189,248,0.2), rgba(129,140,248,0.15))"
                : "rgba(255,255,255,0.04)",
              border: `1px solid ${msg.role === "user" ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.07)"}`,
              fontSize: 12,
              color: "#e2e8f0",
              lineHeight: 1.5,
            }}>
              {msg.text}
            </div>

            {/* Sources */}
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ display: "flex", gap: 4, marginTop: 4, flexWrap: "wrap" }}>
                {msg.sources.map(s => (
                  <span key={s} style={{
                    fontSize: 9, color: "#475569", padding: "1px 6px",
                    borderRadius: 4, background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                  }}>{s}</span>
                ))}
                {msg.conf && (
                  <span style={{ fontSize: 9, color: "#38bdf8", padding: "1px 6px", borderRadius: 4, background: "rgba(56,189,248,0.06)", border: "1px solid rgba(56,189,248,0.15)" }}>
                    {msg.conf}% conf
                  </span>
                )}
              </div>
            )}

            {/* Suggested actions */}
            {msg.actions && msg.actions.length > 0 && (
              <div style={{ display: "flex", gap: 4, marginTop: 5, flexWrap: "wrap" }}>
                {msg.actions.map(a => (
                  <button key={a} onClick={() => send(a)} style={{
                    fontSize: 9, padding: "3px 8px", borderRadius: 6, cursor: "pointer",
                    background: "rgba(56,189,248,0.06)", border: "1px solid rgba(56,189,248,0.18)",
                    color: "#38bdf8",
                  }}>{a}</button>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#475569", fontSize: 11 }}>
            <div style={{ display: "flex", gap: 3 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 5, height: 5, borderRadius: "50%", background: "#38bdf8",
                  animation: `dotBounce 1s ${i * 0.2}s ease-in-out infinite`,
                }} />
              ))}
            </div>
            <style>{`@keyframes dotBounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}`}</style>
            Analyzing…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: "10px 12px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        display: "flex", gap: 8,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send(input)}
          placeholder="Ask TwinGuard AI…"
          style={{
            flex: 1, background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8, padding: "8px 12px",
            color: "#e2e8f0", fontSize: 12, outline: "none",
          }}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          style={{
            padding: "8px 14px", borderRadius: 8, cursor: "pointer",
            background: loading || !input.trim() ? "rgba(56,189,248,0.1)" : "rgba(56,189,248,0.2)",
            border: "1px solid rgba(56,189,248,0.3)",
            color: "#38bdf8", fontSize: 12, fontWeight: 700,
          }}
        >Ask</button>
      </div>
    </div>
  );
}
