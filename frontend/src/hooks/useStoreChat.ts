import { useCallback, useRef, useState } from "react";
import { storeApi, StoreChatResponse } from "../api/store";

export interface ChatAction {
  label: string;
  command?: string;
  href?: string;
}

export interface ChatSuggestion {
  label: string;
  value?: string;
  command?: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "bot";
  text: string;
  intent?: string;
  status?: StoreChatResponse["status"];
  data?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  actions?: ChatAction[] | null;
  suggestions?: ChatSuggestion[] | null;
}

export interface SendMessageOptions {
  fresh?: boolean;
}

const SESSION_KEY = "shelfmind_chat_session";

let _msgId = 0;

function loadSessionId(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function saveSessionId(id: string | null) {
  try {
    if (id) sessionStorage.setItem(SESSION_KEY, id);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function useStoreChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionIdRef = useRef<string | null>(loadSessionId());
  const [sessionId, setSessionId] = useState<string | null>(sessionIdRef.current);
  const [pendingConfirm, setPendingConfirm] = useState(false);
  const loadingRef = useRef(false);

  const appendBot = useCallback((res: StoreChatResponse) => {
    if (res.session_id) {
      sessionIdRef.current = res.session_id;
      setSessionId(res.session_id);
      saveSessionId(res.session_id);
    }
    setPendingConfirm(res.status === "confirm");
    const botMsg: ChatMessage = {
      id: ++_msgId,
      role: "bot",
      text: res.reply,
      intent: res.intent,
      status: res.status,
      data: res.data,
      result: res.result,
      actions: res.actions,
      suggestions: res.suggestions,
    };
    setMessages((prev) => [...prev, botMsg]);
    return botMsg;
  }, []);

  const sendMessage = useCallback(
    async (text: string, options?: SendMessageOptions) => {
      const trimmed = text.trim();
      if (!trimmed || loadingRef.current) return null;

      loadingRef.current = true;
      setLoading(true);
      setMessages((prev) => [...prev, { id: ++_msgId, role: "user", text: trimmed }]);

      try {
        const res = await storeApi.chat(trimmed, sessionIdRef.current, options?.fresh ?? false);
        return appendBot(res);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : "Something went wrong";
        setMessages((prev) => [
          ...prev,
          { id: ++_msgId, role: "bot", text: `Error: ${errMsg}. Try again.` },
        ]);
        return null;
      } finally {
        loadingRef.current = false;
        setLoading(false);
      }
    },
    [appendBot]
  );

  const sendCommand = useCallback(
    (text: string) => sendMessage(text, { fresh: true }),
    [sendMessage]
  );

  const sendSuggestion = useCallback(
    (suggestion: ChatSuggestion) => {
      const text = suggestion.command || suggestion.value || suggestion.label;
      return sendMessage(text);
    },
    [sendMessage]
  );

  const confirmAction = useCallback(() => sendMessage("yes"), [sendMessage]);
  const cancelAction = useCallback(() => sendMessage("cancel", { fresh: true }), [sendMessage]);

  const resetChat = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = null;
    setSessionId(null);
    setPendingConfirm(false);
    saveSessionId(null);
  }, []);

  return {
    messages,
    loading,
    sessionId,
    pendingConfirm,
    sendMessage,
    sendCommand,
    sendSuggestion,
    confirmAction,
    cancelAction,
    resetChat,
  };
}
