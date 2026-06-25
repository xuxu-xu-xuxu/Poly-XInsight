import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@/contexts/auth";

function randomUUID(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for non-HTTPS environments (e.g. internal IP access)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

interface Citation {
  paper_id: string;
  title: string;
  author: string;
  year: number;
  section: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

interface ChatScope {
  paperIds?: string[];
  domainId?: string;
}

export function useChat(conversationId: string | null) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load messages when conversation changes
  useEffect(() => {
    if (!conversationId || !token) {
      setMessages([]);
      return;
    }
    setLoading(true);
    fetch(`/api/conversations/${conversationId}/messages`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setMessages(
          (data || []).map((m: { id: number; role: string; content: string; citations?: Citation[] }) => ({
            id: String(m.id),
            role: m.role as "user" | "assistant",
            content: m.content,
            citations: m.citations,
          }))
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [conversationId, token]);

  const sendMessage = useCallback(
    async (query: string, scope: ChatScope = {}, overrideConvoId?: string) => {
      const effectiveConvoId = overrideConvoId || conversationId;
      if (!effectiveConvoId || !token) return;

      const userMsg: Message = { id: randomUUID(), role: "user", content: query };
      const assistantMsg: Message = { id: randomUUID(), role: "assistant", content: "" };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout
      try {
        const resp = await fetch(`/api/conversations/${effectiveConvoId}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            query,
            scope_paper_ids: scope.paperIds || [],
            scope_domain_id: scope.domainId,
          }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          clearTimeout(timeoutId);
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: `[请求失败: ${resp.status} ${resp.statusText}]` }
                : m
            )
          );
          return;
        }

        const reader = resp.body?.getReader();
        if (!reader) { clearTimeout(timeoutId); setIsStreaming(false); return; }

        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (!data) continue;
              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsg.id ? { ...m, content: m.content + parsed.content } : m
                    )
                  );
                } else if (parsed.refs) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsg.id ? { ...m, citations: parsed.refs } : m
                    )
                  );
                }
              } catch {
                if (data.length > 0 && !/^[🔍📚✅]/.test(data)) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsg.id ? { ...m, content: m.content + data } : m
                    )
                  );
                }
              }
            }
          }
        }
      } catch (err: unknown) {
        clearTimeout(timeoutId);
        const errorMsg = err instanceof DOMException && err.name === "AbortError"
          ? "\n[请求超时，请重试]"
          : "\n[回答出错，请重试]";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id ? { ...m, content: m.content + errorMsg } : m
          )
        );
      } finally {
        clearTimeout(timeoutId);
        setIsStreaming(false);
      }
    },
    [conversationId, token]
  );

  return { messages, isStreaming, loading, sendMessage };
}
