"use client";

import { useEffect, useState } from "react";
import { BarChart3, BatteryCharging, FlaskConical, Loader2, Sigma } from "lucide-react";
import {
  fetchElectrochemicalWindowByMaterial,
  fetchPropertyConductivityByElement,
  fetchPropertyConductivityByMaterial,
  fetchPropertyElementFrequency,
} from "@/lib/api";
import { ChartContainer } from "@/components/viz/chart-container";

type ChartKind = "elementFrequency" | "elementConductivity" | "materialConductivity" | "electrochemicalWindow";

interface AnalyticsResult {
  chart_type: string;
  title: string;
  data: Record<string, unknown>[];
  echarts_option: object;
}

const chartButtons: Array<{ kind: ChartKind; label: string; icon: typeof BarChart3 }> = [
  { kind: "elementFrequency", label: "元素频次", icon: Sigma },
  { kind: "elementConductivity", label: "元素电导率", icon: BarChart3 },
  { kind: "materialConductivity", label: "材料电导率", icon: BatteryCharging },
  { kind: "electrochemicalWindow", label: "电化学窗口", icon: FlaskConical },
];

export function AnalyticsPanel() {
  const [kind, setKind] = useState<ChartKind>("elementFrequency");
  const [metric, setMetric] = useState<"avg" | "median">("avg");
  const [result, setResult] = useState<AnalyticsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        if (kind === "elementFrequency") {
          setResult(await fetchPropertyElementFrequency({ confidence_min: 0.5 }));
        } else if (kind === "elementConductivity") {
          setResult(await fetchPropertyConductivityByElement({ metric, confidence_min: 0.5 }));
        } else if (kind === "materialConductivity") {
          setResult(await fetchPropertyConductivityByMaterial({ confidence_min: 0.5 }));
        } else {
          setResult(await fetchElectrochemicalWindowByMaterial({ confidence_min: 0.5 }));
        }
      } catch {
        setError("加载统计图失败");
        setResult(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [kind, metric]);

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-[#e5e7eb] p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <BarChart3 className="h-4 w-4 text-[#2c5282]" />
          固态电解质结构化数据图表
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {chartButtons.map((button) => {
            const Icon = button.icon;
            return (
              <button
                key={button.kind}
                onClick={() => setKind(button.kind)}
                className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  kind === button.kind
                    ? "bg-[#1a2744] text-white"
                    : "border border-[#d1d5db] bg-white text-gray-600 hover:bg-[#fafafa]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {button.label}
              </button>
            );
          })}
        </div>
        {kind === "elementConductivity" && (
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => setMetric("avg")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                metric === "avg"
                  ? "bg-[#1a2744] text-white"
                  : "border border-[#d1d5db] bg-white text-gray-600 hover:bg-[#fafafa]"
              }`}
            >
              平均值
            </button>
            <button
              onClick={() => setMetric("median")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                metric === "median"
                  ? "bg-[#1a2744] text-white"
                  : "border border-[#d1d5db] bg-white text-gray-600 hover:bg-[#fafafa]"
              }`}
            >
              中位数
            </button>
          </div>
        )}
      </div>

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
            <p className="text-xs text-gray-400">请先在数据挖掘页重新抽取固态电解质性质记录</p>
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
                            {String(value)}
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
