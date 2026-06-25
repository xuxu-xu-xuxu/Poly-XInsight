import { X, Scan } from "lucide-react";

interface PaperCardProps {
  paper: { id: string; title: string; authors: string | null; year: number | null; status: string };
  onDelete: (id: string) => void;
  onExtract: (id: string) => void;
}

export function PaperCard({ paper, onDelete, onExtract }: PaperCardProps) {
  return (
    <div className="mb-1 p-3 rounded-lg hover:bg-slate-900 cursor-pointer transition-colors border border-transparent hover:border-slate-800 group relative">
      <h3 className="text-sm font-medium line-clamp-2 leading-snug pr-6">{paper.title}</h3>
      <p className="text-xs text-slate-500 mt-1">
        {paper.authors || "未知作者"} · {paper.year || "未知年份"}
        {paper.status === "processing" && (
          <span className="ml-2 text-yellow-500">处理中...</span>
        )}
        {paper.status === "ingested" && (
          <span className="ml-2 text-emerald-500">已入库</span>
        )}
      </p>
      <div className="absolute top-2 right-2 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {paper.status === "ingested" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onExtract(paper.id);
            }}
            title="提取实体"
            className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-blue-400"
          >
            <Scan className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm("确认删除这篇文献？")) {
              onDelete(paper.id);
            }
          }}
          title="删除"
          className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
