"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Beaker,
  Gauge,
  Layers,
  Loader2,
  Ruler,
  Waves,
} from "lucide-react";
import {
  fetchConductivityByFiller,
  fetchConductivityByMatrix,
  fetchConductivityDistribution,
  fetchFillerContentVsConductivity,
  fetchImpactStrengthByMaterial,
  fetchStorageModulusByMaterial,
  fetchTanDeltaByMaterial,
  fetchTensileStrengthByMaterial,
  fetchThermalFillerFrequency,
  fetchThermalFillerTypes,
  fetchViscosityByMaterial,
  fetchYoungsModulusByMaterial,
} from "@/lib/api";
import { ChartContainer } from "@/components/viz/chart-container";

// ─── Types ───────────────────────────────────────────────────────────

interface AnalyticsResult {
  chart_type: string;
  title: string;
  data: Record<string, unknown>[];
  echarts_option: object;
}

// ─── Tab definitions ─────────────────────────────────────────────────

const TABS = [
  { key: "composition", label: "导热材料原料", icon: Layers },
  { key: "thermal", label: "导热率/热阻", icon: Gauge },
  { key: "rheological", label: "流变模量/黏度", icon: Waves },
  { key: "mechanical", label: "力学性质", icon: Ruler },
] as const;

type TabKey = (typeof TABS)[number]["key"];

// ─── Chart buttons inside each tab ────────────────────────────────────

const tabCharts: Record<TabKey, Array<{ key: string; label: string; icon: typeof BarChart3; fetcher: () => Promise<AnalyticsResult> }>> = {
  composition: [
    { key: "fillerTypes", label: "填料类型分布", icon: BarChart3, fetcher: () => fetchThermalFillerTypes({ confidence_min: 0.5 }) },
    { key: "fillerFrequency", label: "填料频次", icon: BarChart3, fetcher: () => fetchThermalFillerFrequency({ confidence_min: 0.5 }) },
    { key: "fillerContentVsCond", label: "填料含量-导热率", icon: BarChart3, fetcher: () => fetchFillerContentVsConductivity({ confidence_min: 0.5 }) },
  ],
  thermal: [
    { key: "condByFiller", label: "填料导热率对比", icon: BarChart3, fetcher: () => fetchConductivityByFiller({ confidence_min: 0.5 }) },
    { key: "condByMatrix", label: "基体导热率对比", icon: BarChart3, fetcher: () => fetchConductivityByMatrix({ confidence_min: 0.5 }) },
    { key: "condDist", label: "导热率分布", icon: BarChart3, fetcher: () => fetchConductivityDistribution({ confidence_min: 0.5 }) },
  ],
  rheological: [
    { key: "viscosity", label: "复合黏度对比", icon: BarChart3, fetcher: () => fetchViscosityByMaterial({ confidence_min: 0.5 }) },
    { key: "storageModulus", label: "储能模量 G'", icon: BarChart3, fetcher: () => fetchStorageModulusByMaterial({ confidence_min: 0.5 }) },
    { key: "tanDelta", label: "Tan δ 对比", icon: BarChart3, fetcher: () => fetchTanDeltaByMaterial({ confidence_min: 0.5 }) },
  ],
  mechanical: [
    { key: "tensile", label: "拉伸强度", icon: BarChart3, fetcher: () => fetchTensileStrengthByMaterial({ confidence_min: 0.5 }) },
    { key: "youngs", label: "杨氏模量", icon: BarChart3, fetcher: () => fetchYoungsModulusByMaterial({ confidence_min: 0.5 }) },
    { key: "impact", label: "冲击强度", icon: BarChart3, fetcher: () => fetchImpactStrengthByMaterial({ confidence_min: 0.5 }) },
  ],
};

// ─── Component ───────────────────────────────────────────────────────

export function ThermalAnalyticsPanel() {
  const [tab, setTab] = useState<TabKey>("composition");
  const [chartKey, setChartKey] = useState<string>(tabCharts.composition[0].key);
  const [result, setResult] = useState<AnalyticsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Reset chart when tab changes
  useEffect(() => {
    const charts = tabCharts[tab];
    setChartKey(charts[0].key);
  }, [tab]);

  // Load chart when chartKey changes
  useEffect(() => {
    const charts = tabCharts[tab];
    const chart = charts.find((c) => c.key === chartKey);
    if (!chart) return;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        setResult(await chart.fetcher());
      } catch {
        setError("加载图表失败");
        setResult(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [tab, chartKey]);

  const charts = tabCharts[tab];

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="shrink-0 border-b border-[#e5e7eb] px-4 pt-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Beaker className="h-4 w-4 text-[#2c5282]" />
          导热高分子结构化数据图表
        </h2>
        <div className="mt-3 flex gap-1 border-b border-transparent">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1 rounded-t-md px-4 py-2 text-xs font-medium transition-colors ${
                  tab === t.key
                    ? "bg-white text-[#1a2744] border border-[#e5e7eb] border-b-white -mb-px"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Chart sub-buttons */}
        <div className="flex flex-wrap gap-2 pb-3 pt-2">
          {charts.map((chart) => {
            const Icon = chart.icon;
            return (
              <button
                key={chart.key}
                onClick={() => setChartKey(chart.key)}
                className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  chartKey === chart.key
                    ? "bg-[#1a2744] text-white"
                    : "border border-[#d1d5db] bg-white text-gray-600 hover:bg-[#fafafa]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {chart.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart content */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-[#2c5282]" />
          </div>
        )}
        {error && <p className="p-4 text-sm text-red-500">{error}</p>}
        {!loading && result && (!result.data || result.data.length === 0) && (
          <div className="flex flex-col items-center justify-center gap-2 py-16">
            <BarChart3 className="h-8 w-8 text-gray-300" />
            <p className="text-sm text-gray-500">暂无数据</p>
            <p className="text-xs text-gray-400">请先在数据挖掘页抽取导热材料性质记录</p>
          </div>
        )}
        {!loading && result && result.data && result.data.length > 0 && (
          <>
            <ChartContainer option={result.echarts_option} title={result.title} />
            <div className="px-4 pb-4">
              <div className="overflow-x-auto rounded border border-[#e5e7eb]">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-[#fafafa]">
                      {Object.keys(result.data[0] || {}).map((key) => (
                        <th key={key} className="px-3 py-2 text-left text-gray-500">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.map((row, index) => (
                      <tr key={index} className="border-t border-[#e5e7eb]">
                        {Object.values(row).map((value, valueIndex) => (
                          <td key={valueIndex} className="px-3 py-2 text-gray-700">
                            {typeof value === "number" ? Number(value.toPrecision(4)) : String(value)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
