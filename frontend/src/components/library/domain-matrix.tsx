"use client";

import { Folder, Layers3 } from "lucide-react";

export interface LibraryDomainSummary {
  id: string;
  name: string;
  description?: string | null;
  color?: string | null;
  sort_order: number;
  is_default: boolean;
  paper_count: number;
  ingested_count: number;
  processing_count: number;
  failed_count: number;
  latest_paper_at?: string | null;
}

interface Props {
  domains: LibraryDomainSummary[];
  selectedDomainId: string | null;
  onSelectDomain: (domainId: string | null) => void;
}

const DOMAIN_CARD_BASE =
  "aspect-square rounded-lg border p-4 flex flex-col justify-between transition-all duration-200 text-left";

export function DomainMatrix({ domains, selectedDomainId, onSelectDomain }: Props) {
  const allCount = domains.reduce((sum, domain) => sum + domain.paper_count, 0);
  const allIngested = domains.reduce((sum, domain) => sum + domain.ingested_count, 0);
  const allProcessing = domains.reduce((sum, domain) => sum + domain.processing_count, 0);
  const allFailed = domains.reduce((sum, domain) => sum + domain.failed_count, 0);

  const tiles: Array<LibraryDomainSummary | null> = [null, ...domains];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      {tiles.map((domain) => {
        const active = domain ? selectedDomainId === domain.id : selectedDomainId === null;
        const title = domain ? domain.name : "全部领域";
        const count = domain ? domain.paper_count : allCount;
        const ingested = domain ? domain.ingested_count : allIngested;
        const processing = domain ? domain.processing_count : allProcessing;
        const failed = domain ? domain.failed_count : allFailed;
        const color = domain?.color || "#1a2744";

        return (
          <button
            key={domain?.id || "all"}
            onClick={() => onSelectDomain(domain ? domain.id : null)}
            className={`${DOMAIN_CARD_BASE} ${
              active ? "border-[#1a2744] shadow-sm" : "border-[#e5e7eb] hover:border-[#cbd5e1]"
            }`}
            style={{
              background: active ? "linear-gradient(180deg, rgba(26,39,68,0.08), rgba(26,39,68,0.02))" : "#fff",
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <div
                className="h-10 w-10 rounded-lg flex items-center justify-center text-white shrink-0"
                style={{ backgroundColor: color }}
              >
                {domain ? <Folder className="h-5 w-5" /> : <Layers3 className="h-5 w-5" />}
              </div>
              <span className="text-[11px] text-gray-400 tabular-nums">
                {domain?.latest_paper_at ? new Date(domain.latest_paper_at).toLocaleDateString("zh-CN") : " "}
              </span>
            </div>

            <div className="min-h-0">
              <div className="text-sm font-semibold text-[#1a2744] leading-tight line-clamp-2">{title}</div>
              <div className="mt-1 text-[11px] text-gray-500 line-clamp-2">
                {domain?.description || (domain ? "点击查看该领域文献" : "查看全部导入文献")}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-500">
              <div className="rounded-md bg-[#fafafa] px-2 py-1">
                <div className="text-gray-400">总数</div>
                <div className="font-semibold text-gray-700 tabular-nums">{count}</div>
              </div>
              <div className="rounded-md bg-[#fafafa] px-2 py-1">
                <div className="text-gray-400">已入库</div>
                <div className="font-semibold text-gray-700 tabular-nums">{ingested}</div>
              </div>
              <div className="rounded-md bg-[#fafafa] px-2 py-1">
                <div className="text-gray-400">处理中</div>
                <div className="font-semibold text-gray-700 tabular-nums">{processing}</div>
              </div>
              <div className="rounded-md bg-[#fafafa] px-2 py-1">
                <div className="text-gray-400">失败</div>
                <div className="font-semibold text-gray-700 tabular-nums">{failed}</div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
