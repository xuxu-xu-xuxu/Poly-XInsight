"use client";
import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (query: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="border-t border-[#e5e7eb] bg-white px-4 py-3">
      <div className="flex gap-2 items-end max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题... (Ctrl+Enter 发送)"
          rows={1}
          className="flex-1 border border-[#d1d5db] rounded-[10px] px-4 py-2.5 text-sm text-gray-700 placeholder:text-gray-400 resize-none focus:outline-none focus:border-[#1a2744] focus:ring-1 focus:ring-[#1a2744]"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="shrink-0 px-5 py-2.5 rounded-[10px] text-sm font-medium text-white disabled:opacity-40"
          style={{ backgroundColor: "#1a2744" }}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
