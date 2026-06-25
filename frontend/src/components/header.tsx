"use client";
import { useRef } from "react";
import { Archive, BookOpen, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  onUpload: (file: File) => void;
  onBatchUpload: (file: File) => void;
  uploading: boolean;
}

export function Header({ onUpload, onBatchUpload, uploading }: Props) {
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);

  return (
    <header className="h-14 border-b border-slate-800 bg-slate-950 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <BookOpen className="w-5 h-5 text-blue-400" />
        <span className="font-semibold text-base">Poly XInsight</span>
        <span className="text-xs text-slate-500 bg-slate-900 px-2 py-0.5 rounded">Polymer Composite RAG</span>
      </div>
      <input
        ref={pdfInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            onUpload(file);
            e.target.value = "";
          }
        }}
      />
      <input
        ref={zipInputRef}
        type="file"
        accept=".zip"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            onBatchUpload(file);
            e.target.value = "";
          }
        }}
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          className="gap-2 bg-slate-800 hover:bg-slate-700 text-white"
          onClick={() => zipInputRef.current?.click()}
          disabled={uploading}
        >
          <Archive className="w-4 h-4" />
          ZIP 批量导入
        </Button>
        <Button
          size="sm"
          className="gap-2 bg-blue-600 hover:bg-blue-500 text-white"
          onClick={() => pdfInputRef.current?.click()}
          disabled={uploading}
        >
          <Upload className="w-4 h-4" />
          {uploading ? "上传中..." : "上传 PDF"}
        </Button>
      </div>
    </header>
  );
}
