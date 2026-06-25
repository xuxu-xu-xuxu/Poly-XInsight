"use client";
import { Search, X, Filter } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PaperCard } from "./paper-card";

export interface Paper {
  id: string;
  title: string;
  authors: string | null;
  year: number | null;
  status: string;
}

interface Props {
  onClose: () => void;
  papers?: Paper[];
  onDelete: (id: string) => void;
  onExtract: (id: string) => void;
}

export function LiteratureSidebar({ onClose, papers = [], onDelete, onExtract }: Props) {
  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Filter className="w-4 h-4" /> 文献库
        </h2>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7">
          <X className="w-4 h-4" />
        </Button>
      </div>
      <div className="p-3 border-b border-slate-800">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-500" />
          <Input placeholder="搜索文献..." className="pl-8 h-9 text-sm bg-slate-900 border-slate-700" />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {papers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} onDelete={onDelete} onExtract={onExtract} />
        ))}
        {papers.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-8">暂无文献，请先上传 PDF</p>
        )}
      </div>
    </div>
  );
}
