"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Plus, Trash2, MessageSquare } from "lucide-react";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import { useChat } from "@/hooks/use-chat";
import { useAuth } from "@/contexts/auth";

interface Props {
  scopePaperIds?: string[];
  scopeDomainId?: string;
}

export function ChatPanel({ scopePaperIds, scopeDomainId }: Props) {
  const { token } = useAuth();
  const [convoId, setConvoId] = useState<string | null>(null);
  const [convos, setConvos] = useState<{ id: string; title: string }[]>([]);
  const { messages, isStreaming, loading, sendMessage } = useChat(convoId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const creatingRef = useRef(false);

  // Load conversation list
  const loadConvos = useCallback(async () => {
    if (!token) return;
    try {
      const resp = await fetch("/api/conversations", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setConvos(data || []);
      }
    } catch {}
  }, [token]);

  useEffect(() => { loadConvos(); }, [loadConvos]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleNewConvo = async () => {
    if (!token) return;
    const resp = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ title: "新对话" }),
    });
    if (resp.ok) {
      const data = await resp.json();
      await loadConvos();
      setConvoId(data.id);
    }
  };

  const handleDeleteConvo = async (id: string) => {
    if (!token) return;
    await fetch(`/api/conversations/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (convoId === id) setConvoId(null);
    loadConvos();
  };

  const handleSend = (query: string) => {
    if (!convoId) {
      // Auto-create conversation on first message
      if (!token || creatingRef.current) return;
      creatingRef.current = true;
      fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ title: "新对话" }),
      })
        .then((r) => r.json())
        .then((data) => {
          setConvoId(data.id);
          loadConvos();
          sendMessage(query, { paperIds: scopePaperIds || [], domainId: scopeDomainId }, data.id);
        })
        .catch(() => {})
        .finally(() => { creatingRef.current = false; });
      return;
    }
    sendMessage(query, { paperIds: scopePaperIds || [], domainId: scopeDomainId });
  };

  return (
    <div className="h-full flex">
      {/* Conversation sidebar */}
      <div className="w-48 shrink-0 border-r border-[#e5e7eb] bg-[#fafafa] flex flex-col">
        <div className="p-3 border-b border-[#e5e7eb]">
          <button
            onClick={handleNewConvo}
            className="flex items-center gap-1.5 w-full px-3 py-2 text-xs font-medium rounded-lg bg-[#1a2744] text-white hover:bg-[#2d3f5e]"
          >
            <Plus className="w-3.5 h-3.5" />
            新建对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {convos.map((c) => (
            <div
              key={c.id}
              onClick={() => setConvoId(c.id)}
              className={`group flex items-center gap-2 px-2 py-2 rounded text-xs cursor-pointer transition-colors ${
                convoId === c.id
                  ? "bg-[#eef2f8] text-[#1a2744] font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <MessageSquare className="w-3 h-3 shrink-0" />
              <span className="truncate flex-1">{c.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteConvo(c.id); }}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
          {convos.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-8">暂无对话</p>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-400">加载中...</div>
        ) : messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-heading text-[#1a2744] mb-1">聚合物复合材料智能助手</p>
              <p className="text-sm text-gray-500">
                {convoId ? "开始提问，基于文献获取专业回答" : "点击「新建对话」开始"}
              </p>
            </div>
          </div>
        ) : (
          <div ref={scrollRef} className="flex-1 overflow-y-auto py-4">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                citations={msg.citations}
              />
            ))}
          </div>
        )}
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
