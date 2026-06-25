"use client";
import { Folder, FolderOpen, Sparkles, Library } from "lucide-react";

interface CategoryData {
  tag: string;
  count: number;
  category: string;
}

interface Props {
  categories: CategoryData[];
  selectedTag: string | null;
  onSelectTag: (tag: string | null) => void;
  onClassify: () => void;
  onCluster: () => void;
  classifying: boolean;
  clustering: boolean;
  totalPapers: number;
}

const SECTION_ORDER = ["研究领域", "材料类型", "方法类型", "聚类结果"];

export function CategorySidebar({
  categories,
  selectedTag,
  onSelectTag,
  onClassify,
  onCluster,
  classifying,
  clustering,
  totalPapers,
}: Props) {
  // Group categories by section
  const sections: Record<string, CategoryData[]> = {};
  for (const cat of categories) {
    const section = cat.category || "其他";
    if (!sections[section]) sections[section] = [];
    sections[section].push(cat);
  }

  const hasAnyTags = categories.length > 0;

  return (
    <div className="w-56 shrink-0 border-r border-[#e5e7eb] bg-[#fafafa] flex flex-col select-none">
      {/* Header */}
      <div className="p-3 border-b border-[#e5e7eb]">
        <div className="flex items-center gap-1.5 text-xs font-medium text-[#1a2744] mb-2">
          <Folder className="w-3.5 h-3.5" />
          文献分类
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={onClassify}
            disabled={classifying}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-[10px] font-medium rounded-md bg-[#1a2744] text-white hover:bg-[#2d3f5e] disabled:opacity-50 transition-colors"
          >
            <Sparkles className="w-3 h-3" />
            {classifying ? "分类中..." : "AI 分类"}
          </button>
          <button
            onClick={onCluster}
            disabled={clustering}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-[10px] font-medium rounded-md border border-[#d1d5db] text-gray-600 hover:bg-gray-100 disabled:opacity-50 transition-colors"
          >
            {clustering ? "聚类中..." : "聚类"}
          </button>
        </div>
      </div>

      {/* Scrollable folder list */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* Root folder: 全部文献 */}
        <button
          onClick={() => onSelectTag(null)}
          className={`w-full flex items-center gap-2 px-3 py-2 mx-1 rounded-md text-xs transition-colors ${
            selectedTag === null
              ? "bg-[#eef2f8] text-[#1a2744] font-medium"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          <Library className="w-4 h-4 shrink-0" />
          <span className="truncate flex-1 text-left">全部文献</span>
          <span className="text-[10px] text-gray-400 shrink-0 tabular-nums">{totalPapers}</span>
        </button>

        {!hasAnyTags && !classifying && !clustering && (
          <p className="text-[11px] text-gray-400 text-center py-6 px-3 leading-relaxed">
            点击上方「AI 分类」<br />为文献自动打标签
          </p>
        )}
        {(classifying || clustering) && (
          <p className="text-[11px] text-gray-400 text-center py-4 px-3">
            {classifying ? "AI 正在逐篇分析文献..." : "正在计算聚类..."}
          </p>
        )}

        {/* Category folders grouped by section */}
        {SECTION_ORDER.map((sectionName) => {
          const items = sections[sectionName];
          if (!items || items.length === 0) return null;
          return (
            <div key={sectionName} className="mt-3">
              <div className="px-3 py-1 text-[10px] font-medium text-gray-400 uppercase tracking-wider">
                {sectionName}
              </div>
              {items.map((cat) => {
                const isSelected = selectedTag === cat.tag;
                return (
                  <button
                    key={cat.tag}
                    onClick={() => onSelectTag(cat.tag)}
                    className={`w-full flex items-center gap-2 px-3 py-2 mx-1 rounded-md text-xs transition-colors ${
                      isSelected
                        ? "bg-[#eef2f8] text-[#1a2744] font-medium"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {isSelected ? (
                      <FolderOpen className="w-4 h-4 shrink-0 text-[#1a2744]" />
                    ) : (
                      <Folder className="w-4 h-4 shrink-0 text-gray-400" />
                    )}
                    <span className="truncate flex-1 text-left">{cat.tag}</span>
                    <span className="text-[10px] text-gray-400 shrink-0 tabular-nums">{cat.count}</span>
                  </button>
                );
              })}
            </div>
          );
        })}

        {/* Remaining sections */}
        {Object.entries(sections).map(([sectionName, items]) => {
          if (SECTION_ORDER.includes(sectionName)) return null;
          return (
            <div key={sectionName} className="mt-3">
              <div className="px-3 py-1 text-[10px] font-medium text-gray-400 uppercase tracking-wider">
                {sectionName}
              </div>
              {items.map((cat) => {
                const isSelected = selectedTag === cat.tag;
                return (
                  <button
                    key={cat.tag}
                    onClick={() => onSelectTag(cat.tag)}
                    className={`w-full flex items-center gap-2 px-3 py-2 mx-1 rounded-md text-xs transition-colors ${
                      isSelected
                        ? "bg-[#eef2f8] text-[#1a2744] font-medium"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {isSelected ? (
                      <FolderOpen className="w-4 h-4 shrink-0 text-[#1a2744]" />
                    ) : (
                      <Folder className="w-4 h-4 shrink-0 text-gray-400" />
                    )}
                    <span className="truncate flex-1 text-left">{cat.tag}</span>
                    <span className="text-[10px] text-gray-400 shrink-0 tabular-nums">{cat.count}</span>
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
