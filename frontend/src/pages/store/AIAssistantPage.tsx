import { useState, useRef, useEffect, FormEvent } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import AppShell from "../../components/layout/AppShell";
import { Recommendation } from "../../api/store";
import { useStoreChat, ChatAction } from "../../hooks/useStoreChat";
import ChatDataBlock from "../../components/chat/ChatDataBlock";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./store-theme.css";
import "../../components/QueryChat.css";
import "../../components/Chatbot.css";

const QUICK_COMMANDS = [
  { label: "Hi", command: "hi" },
  { label: "Help", command: "help" },
  { label: "Make bill", command: "make bill for" },
  { label: "Today's sales", command: "today's sales" },
  { label: "Sales report", command: "sales report this week" },
  { label: "Inventory report", command: "inventory report" },
  { label: "Store overview", command: "store overview report" },
  { label: "Low stock", command: "low stock" },
  { label: "Unpaid bills", command: "unpaid invoices" },
];

function actionClass(action: string) {
  if (action === "increase") return "rec-increase";
  if (action === "decrease") return "rec-decrease";
  return "rec-hold";
}

function parseRecommendations(data: Record<string, unknown> | null | undefined): Recommendation[] {
  if (!data || !Array.isArray(data.recommendations)) return [];
  return data.recommendations as Recommendation[];
}

export default function AIAssistantPage() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const {
    messages,
    loading,
    pendingConfirm,
    sendMessage,
    sendCommand,
    sendSuggestion,
    confirmAction,
    cancelAction,
  } = useStoreChat();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  const handleAction = (action: ChatAction) => {
    if (action.href) navigate(action.href);
    else if (action.command) sendCommand(action.command);
  };

  const lastBot = [...messages].reverse().find((m) => m.role === "bot");
  const showConfirmBar = pendingConfirm && lastBot?.status === "confirm";

  return (
    <AppShell
      {...STORE_SHELL}
      title="Store Assistant"
      subtitle="Chat naturally — run operations, check numbers, or get demand advice"
    >
      <AnimatedPanel className="query-chat ai-glow-panel admin-card" hover={false} style={{ maxWidth: 900 }}>
        <p className="query-subtitle">
          Say hi, create bills, record sales, adjust stock, check reports, or ask what to order next
        </p>

        <div className="ai-chat-messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="chat-welcome ai-page-welcome">
              <div className="chat-welcome-icon">🤖</div>
              <h4>Hi! I'm your store assistant</h4>
              <p>Ask anything in plain language — no special syntax needed.</p>
              <div className="chat-welcome-commands">
                {QUICK_COMMANDS.map((cmd) => (
                  <button
                    key={cmd.command}
                    type="button"
                    className="chat-action-btn admin-suggestion-chip"
                        onClick={() => sendCommand(cmd.command)}
                    disabled={loading}
                  >
                    {cmd.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => {
            const recs =
              msg.role === "bot" && msg.intent === "ai_recommendation" && msg.data
                ? parseRecommendations(msg.data)
                : [];

            return (
              <motion.div
                key={msg.id}
                className={`chat-msg chat-msg-${msg.role} ai-page-msg`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {msg.text}

                {msg.result && (
                  <div className="chat-result-card">
                    {msg.result.invoice_number != null && (
                      <div className="chat-result-row">
                        <span>Invoice</span>
                        <strong>{String(msg.result.invoice_number)}</strong>
                      </div>
                    )}
                    {msg.result.total != null && (
                      <div className="chat-result-row">
                        <span>Total</span>
                        <strong>
                          ₹{Number(msg.result.total).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                        </strong>
                      </div>
                    )}
                  </div>
                )}

                {msg.data && msg.intent !== "ai_recommendation" && <ChatDataBlock data={msg.data} />}

                {recs.length > 0 && (
                  <StaggerGrid className="recommendations">
                    {recs.map((rec, i) => (
                      <StaggerItem key={i}>
                        <motion.div
                          className={`rec-card ${actionClass(rec.action)}`}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                        >
                          <div className="rec-header">
                            <strong>{rec.product_name}</strong>
                            <span className="rec-action">{rec.action}</span>
                          </div>
                          <p className="rec-sku">{rec.sku}</p>
                          <p>{rec.rationale}</p>
                          <div className="rec-meta">
                            <span>
                              {rec.delta_pct > 0 ? "+" : ""}
                              {rec.delta_pct}%
                            </span>
                            <span>{Math.round(rec.confidence * 100)}% confidence</span>
                          </div>
                          <div className="confidence-bar">
                            <motion.div
                              className="confidence-bar-fill"
                              initial={{ width: 0 }}
                              animate={{ width: `${rec.confidence * 100}%` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                            />
                          </div>
                        </motion.div>
                      </StaggerItem>
                    ))}
                  </StaggerGrid>
                )}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="chat-suggestions">
                    {msg.suggestions.map((s, i) => (
                      <button
                        key={i}
                        type="button"
                        className="chat-suggestion-chip admin-suggestion-chip"
                        onClick={() => sendSuggestion(s)}
                        disabled={loading}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                )}

                {msg.actions && msg.actions.length > 0 && (
                  <div className="chat-actions">
                    {msg.actions.map((a, i) => (
                      <button
                        key={i}
                        type="button"
                        className="chat-action-btn"
                        onClick={() => handleAction(a)}
                      >
                        {a.label}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            );
          })}

          {loading && (
            <div className="chat-typing">
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
            </div>
          )}
        </div>

        {showConfirmBar && (
          <div className="chat-confirm-bar">
            <span>Confirm this action?</span>
            <div className="chat-confirm-actions">
              <button type="button" className="chat-confirm-yes" onClick={confirmAction} disabled={loading}>
                Confirm
              </button>
              <button type="button" className="chat-confirm-cancel" onClick={cancelAction} disabled={loading}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {messages.length > 0 && (
          <StaggerGrid className="suggestions">
            {QUICK_COMMANDS.map((cmd) => (
              <StaggerItem key={cmd.command}>
                <motion.button
                  type="button"
                  className="suggestion-chip admin-suggestion-chip"
                        onClick={() => sendCommand(cmd.command)}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  disabled={loading}
                >
                  {cmd.label}
                </motion.button>
              </StaggerItem>
            ))}
          </StaggerGrid>
        )}

        <form className="query-form" onSubmit={handleSubmit}>
          <input
            className="query-input"
            placeholder="Say hi, create a bill, check sales, ask anything…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="admin-btn admin-btn-primary" disabled={loading}>
            {loading ? "Working…" : "Send"}
          </button>
        </form>
      </AnimatedPanel>
    </AppShell>
  );
}
