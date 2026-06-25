import ReactMarkdown from "react-markdown";

interface Props {
  role: "user" | "assistant";
  content: string;
  citations?: { paper_id: string; title: string; author: string; year: number }[];
}

export function ChatMessage({ role, content, citations }: Props) {
  const isUser = role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} px-4 py-2`}
    >
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {/* Bubble */}
        <div
          className={`px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "text-white rounded-bubble rounded-br-[2px]"
              : "text-gray-700 bg-[#f8f9fb] border border-[#e5e7eb] rounded-bubble rounded-bl-[2px]"
          }`}
          style={isUser ? { backgroundColor: "#1a2744" } : {}}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap break-words">{content}</span>
          ) : (
            <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed
              [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_strong]:text-gray-900
              [&_code]:bg-gray-100 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-100
              [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:overflow-x-auto
              [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5
              [&_blockquote]:border-l-2 [&_blockquote]:border-gray-300 [&_blockquote]:pl-3 [&_blockquote]:text-gray-500
              [&_a]:text-[#2c5282] [&_a]:underline [&_hr]:border-gray-200
              [&_table]:border-collapse [&_th]:border [&_th]:border-gray-300 [&_th]:px-2 [&_th]:py-1
              [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1">
              <ReactMarkdown>{content || "思考中..."}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations for AI responses */}
        {!isUser && citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {citations.map((c, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] text-[#2c5282] bg-[#eef2f8] rounded"
              >
                {c.title} · {c.author} ({c.year})
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
