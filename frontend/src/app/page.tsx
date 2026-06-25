"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  Library,
} from "lucide-react";
import { ChatPanel } from "@/components/chat/chat-panel";
import { fetchPapers } from "@/lib/api";
import { useDomains } from "@/hooks/use-domains";

interface Paper {
  id: string;
  title: string;
}

type ScopeType = "all" | "domain" | "paper";

export default function ChatPage() {
  const [allPapers, setAllPapers] = useState<Paper[]>([]);
  const { domains, loadDomains } = useDomains();
  const [domainPapers, setDomainPapers] = useState<Record<string, Paper[]>>({});
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set());
  const [scopeType, setScopeType] = useState<ScopeType>("all");
  const [scopeDomainId, setScopeDomainId] = useState("");
  const [scopePaperId, setScopePaperId] = useState("");

  const loadAll = useCallback(async () => {
    try {
      const paperData = await fetchPapers({ page_size: 100 });
      setAllPapers(paperData.items || []);
    } catch {}
  }, []);

  useEffect(() => {
    loadAll();
    loadDomains();
  }, [loadAll, loadDomains]);

  useEffect(() => {
    if (scopeDomainId && !domains.some((domain) => domain.id === scopeDomainId)) {
      selectAll();
    }
  }, [domains, scopeDomainId]);

  const allCount = useMemo(() => {
    const domainTotal = domains.reduce((sum, domain) => sum + domain.paper_count, 0);
    return domainTotal || allPapers.length;
  }, [allPapers.length, domains]);

  const loadDomainPapers = async (domainId: string) => {
    if (Object.prototype.hasOwnProperty.call(domainPapers, domainId)) return;
    try {
      const data = await fetchPapers({ domain_id: domainId, page_size: 100 });
      setDomainPapers((prev) => ({ ...prev, [domainId]: data.items || [] }));
    } catch {}
  };

  const toggleDomain = async (domainId: string) => {
    setExpandedDomains((prev) => {
      const next = new Set(prev);
      if (next.has(domainId)) {
        next.delete(domainId);
      } else {
        next.add(domainId);
      }
      return next;
    });

    await loadDomainPapers(domainId);
  };

  const selectAll = () => {
    setScopeType("all");
    setScopeDomainId("");
    setScopePaperId("");
  };

  const selectDomain = (domainId: string) => {
    if (scopeType === "domain" && scopeDomainId === domainId) {
      selectAll();
      return;
    }
    setScopeType("domain");
    setScopeDomainId(domainId);
    setScopePaperId("");
  };

  const selectPaper = (paperId: string) => {
    if (scopeType === "paper" && scopePaperId === paperId) {
      selectAll();
      return;
    }
    setScopeType("paper");
    setScopePaperId(paperId);
    setScopeDomainId("");
  };

  const scopedPaperIds = scopeType === "paper" && scopePaperId ? [scopePaperId] : undefined;
  const scopedDomainId = scopeType === "domain" && scopeDomainId ? scopeDomainId : undefined;

  return (
    <div className="h-full flex">
      <div className="flex-1 flex flex-col min-w-0">
        <ChatPanel scopePaperIds={scopedPaperIds} scopeDomainId={scopedDomainId} />
      </div>

      <div className="w-56 shrink-0 border-l border-[#e5e7eb] bg-[#fafafa] flex flex-col select-none">
        <div className="p-3 border-b border-[#e5e7eb]">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider">提问范围</p>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          <button
            onClick={selectAll}
            className={`w-full flex items-center gap-2 px-3 py-2 mx-1 rounded-md text-xs transition-colors ${
              scopeType === "all"
                ? "bg-[#dce3f0] text-[#1a2744] font-semibold border-l-2 border-[#1a2744]"
                : "text-gray-600 hover:bg-gray-100 border-l-2 border-transparent"
            }`}
          >
            <Library className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate flex-1 text-left">全部文献</span>
            <span className="text-[10px] text-gray-400 shrink-0">{allCount}</span>
          </button>

          <div className="mt-2">
            <div className="px-3 py-1 text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              领域模块
            </div>

            {domains.map((domain) => {
              const isDomainSelected = scopeType === "domain" && scopeDomainId === domain.id;
              const isExpanded = expandedDomains.has(domain.id);
              const papers = domainPapers[domain.id] || [];
              const hasLoadedPapers = Object.prototype.hasOwnProperty.call(domainPapers, domain.id);

              return (
                <div key={domain.id}>
                  <div
                    className={`flex items-center gap-1 px-1 mx-1 rounded-md text-xs transition-colors ${
                      isDomainSelected
                        ? "bg-[#dce3f0] border-l-2 border-[#1a2744]"
                        : "hover:bg-gray-100 border-l-2 border-transparent"
                    }`}
                  >
                    <button
                      onClick={() => toggleDomain(domain.id)}
                      className="p-1 rounded hover:bg-gray-200 shrink-0"
                      aria-label={isExpanded ? "收起领域" : "展开领域"}
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3 h-3 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-3 h-3 text-gray-400" />
                      )}
                    </button>
                    <button
                      onClick={() => selectDomain(domain.id)}
                      className="flex items-center gap-2 flex-1 py-2 pr-2 text-left min-w-0"
                    >
                      {isDomainSelected ? (
                        <FolderOpen className="w-3.5 h-3.5 shrink-0 text-[#1a2744]" />
                      ) : (
                        <Folder className="w-3.5 h-3.5 shrink-0 text-gray-400" />
                      )}
                      <span
                        className={`truncate flex-1 ${
                          isDomainSelected ? "font-medium text-[#1a2744]" : "text-gray-600"
                        }`}
                      >
                        {domain.name}
                      </span>
                      <span className="text-[10px] text-gray-400 shrink-0">
                        {domain.paper_count}
                      </span>
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="ml-4 border-l border-[#e5e7eb] pl-2">
                      {papers.map((paper) => {
                        const isPaperSelected = scopeType === "paper" && scopePaperId === paper.id;
                        const title =
                          paper.title.length > 28 ? `${paper.title.slice(0, 28)}...` : paper.title;

                        return (
                          <button
                            key={paper.id}
                            onClick={() => selectPaper(paper.id)}
                            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[11px] text-left transition-colors ${
                              isPaperSelected
                                ? "bg-[#dce3f0] text-[#1a2744] font-semibold border-l-2 border-[#1a2744]"
                                : "text-gray-500 hover:bg-gray-100 hover:text-gray-700 border-l-2 border-transparent"
                            }`}
                          >
                            <span className="truncate">{title}</span>
                          </button>
                        );
                      })}
                      {papers.length === 0 && (
                        <p className="text-[10px] text-gray-400 px-2 py-1">
                          {hasLoadedPapers ? "暂无文献" : "加载中..."}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
