"use client";
import { useState, useEffect } from "react";
import { BarChart3, Pickaxe } from "lucide-react";
import { ThermalAnalyticsPanel } from "@/components/analytics/thermal-analytics-panel";
import { ThermalMiningPanel } from "@/components/mining/thermal-mining-panel";
import { fetchPapers } from "@/lib/api";

interface Paper {
  id: string;
  title: string;
  status: string;
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState<"mining" | "charts">("mining");
  const [papers, setPapers] = useState<Paper[]>([]);

  useEffect(() => {
    fetchPapers({ page_size: 500 })
      .then((data) => setPapers(data.items || []))
      .catch(() => {});
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Page header */}
      <div className="px-6 pt-8 pb-0 shrink-0">
        <h1 className="text-2xl font-heading text-[#1a2744] mb-1">数据分析</h1>
        <p className="text-sm text-gray-500">
          导热高分子材料性质抽取 & 统计
        </p>

        {/* Tabs */}
        <div className="flex gap-0 mt-5 border-b-2 border-[#e5e7eb]">
          <button
            onClick={() => setTab("mining")}
            className={`flex items-center gap-1.5 px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-0.5 ${
              tab === "mining"
                ? "text-[#1a2744] border-[#1a2744]"
                : "text-gray-400 border-transparent hover:text-gray-600"
            }`}
          >
            <Pickaxe className="w-4 h-4" />
            数据挖掘
          </button>
          <button
            onClick={() => setTab("charts")}
            className={`flex items-center gap-1.5 px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-0.5 ${
              tab === "charts"
                ? "text-[#1a2744] border-[#1a2744]"
                : "text-gray-400 border-transparent hover:text-gray-600"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            统计图表
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {tab === "charts" && <ThermalAnalyticsPanel />}
        {tab === "mining" && <ThermalMiningPanel papers={papers} />}
      </div>
    </div>
  );
}
