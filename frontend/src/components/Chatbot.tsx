import { useState, useRef, useEffect, FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useStoreChat, ChatAction, ChatSuggestion } from "../hooks/useStoreChat";
import ChatDataBlock from "./chat/ChatDataBlock";
import "./Chatbot.css";

const QUICK_COMMANDS = [
  { label: "Hi", command: "hi" },
  { label: "Make bill", command: "make bill for" },
  { label: "Sell 2 milk", command: "sell 2 milk" },
  { label: "Today's sales", command: "today's sales" },
  { label: "Sales report", command: "sales report this week" },
  { label: "Store overview", command: "store overview report" },
  { label: "Low stock", command: "low stock" },
  { label: "Help", command: "help" },
];

function renderResultCard(result: Record<string, unknown>) {
  const invoiceNumber = result.invoice_number as string | undefined;
  const total = result.total as number | undefined;
  const saleId = result.sale_id ?? result.transaction_id;
  if (!invoiceNumber && !saleId && total == null) return null;

  return (
    <div className="chat-result-card">
      {invoiceNumber && (
        <div className="chat-result-row">
          <span>Invoice</span>
          <strong>{invoiceNumber}</strong>
        </div>
      )}
      {saleId != null && (
        <div className="chat-result-row">
          <span>Sale #</span>
          <strong>{String(saleId)}</strong>
        </div>
      )}
      {total != null && (
        <div className="chat-result-row">
          <span>Total</span>
          <strong>₹{Number(total).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</strong>
        </div>
      )}
      {result.status != null && (
        <div className="chat-result-row">
          <span>Status</span>
          <strong>{String(result.status)}</strong>
        </div>
      )}
    </div>
  );
}

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
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

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  const handleAction = (action: ChatAction) => {
    if (action.href) {
      navigate(action.href);
      setOpen(false);
    } else if (action.command) {
      sendCommand(action.command);
    }
  };

  const handleSuggestion = (s: ChatSuggestion) => {
    sendSuggestion(s);
  };

  const lastBot = [...messages].reverse().find((m) => m.role === "bot");
  const showConfirmBar = pendingConfirm && lastBot?.status === "confirm";

  return (
    <>
      <motion.button
        className="chatbot-fab"
        onClick={() => setOpen(!open)}
        whileTap={{ scale: 0.92 }}
        aria-label="Open chat assistant"
      >
        {open ? "✕" : "💬"}
        {!open && <span className="chatbot-fab-badge" />}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="chatbot-panel"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            <div className="chatbot-header">
              <div className="chatbot-header-left">
                <div className="chatbot-header-avatar">🤖</div>
                <div>
                  <h3>ShelfMind Assistant</h3>
                  <small>Create bills, record sales, check stock...</small>
                </div>
              </div>
              <button className="chatbot-close" onClick={() => setOpen(false)}>
                ✕
              </button>
            </div>

            <div className="chatbot-messages" ref={scrollRef}>
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <div className="chat-welcome-icon">🤖</div>
                  <h4>Hi! I'm your store assistant</h4>
                  <p>Ask anything — bills, sales, stock, or just say hi:</p>
                  <div className="chat-welcome-commands">
                    {QUICK_COMMANDS.map((cmd) => (
                      <button
                        key={cmd.command}
                        className="chat-action-btn"
                        onClick={() => sendCommand(cmd.command)}
                      >
                        {cmd.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  className={`chat-msg chat-msg-${msg.role}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {msg.text}
                  {msg.result && renderResultCard(msg.result)}
                  {msg.data && <ChatDataBlock data={msg.data} />}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="chat-suggestions">
                      {msg.suggestions.map((s, i) => (
                        <button
                          key={i}
                          className="chat-suggestion-chip"
                          onClick={() => handleSuggestion(s)}
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
                          className="chat-action-btn"
                          onClick={() => handleAction(a)}
                        >
                          {a.label}
                        </button>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}

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

            <form className="chatbot-input-area" onSubmit={handleSubmit}>
              <input
                ref={inputRef}
                className="chatbot-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Create bills, record sales, check stock..."
                disabled={loading}
              />
              <button
                type="submit"
                className="chatbot-send"
                disabled={!input.trim() || loading}
              >
                ↑
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
