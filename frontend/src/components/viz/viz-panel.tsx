"use client";
import { useState } from "react";
import { BarChart3, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChartContainer } from "./chart-container";
import { visualizeQuery } from "@/lib/api";

export function VizPanel() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    chart_type: string;
    title: string;
    explanation: string;
    echarts_option: object;
    data: unknown[];
  } | null>(null);
  const [error, setError] = useState("");

  const handleVisualize = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await visualizeQuery(query.trim());
      setResult(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "可视化生成失败，请重试";
      setError(msg);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-[#e5e7eb] shrink-0">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-[#2c5282]" />
          分析面板
        </h2>
      </div>

      {/* Input area */}
      <div className="p-3 border-b border-[#e5e7eb] shrink-0">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleVisualize()}
            placeholder="描述你想要的可视化，例如：比较不同材料的疲劳强度..."
            className="flex-1 bg-white border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm text-gray-800 placeholder:text-gray-500 focus:outline-none focus:border-[#2c5282]/50"
          />
          <Button
            size="sm"
            onClick={handleVisualize}
            disabled={loading || !query.trim()}
            className="shrink-0 gap-1.5 bg-[#1a2744] hover:bg-[#2d3f5e] text-white border-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            智能可视化
          </Button>
        </div>
        {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
      </div>

      {/* Result area */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="w-6 h-6 text-[#2c5282] animate-spin" />
            <p className="text-sm text-gray-500">正在分析数据并生成图表...</p>
          </div>
        )}

        {!loading && !result && (
          <div className="flex flex-col items-center justify-center py-16 px-4 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-[#eef2f8] flex items-center justify-center">
              <BarChart3 className="w-8 h-8 text-[#1a2744]/40" />
            </div>
            <p className="text-sm text-gray-500 text-center">
              输入自然语言描述，AI 将自动查询数据库并生成图表
            </p>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {["比较不同材料的疲劳强度", "各类型实体数量统计", "材料性能分布图"].map(
                (hint) => (
                  <button
                    key={hint}
                    onClick={() => setQuery(hint)}
                    className="text-xs px-2.5 py-1 rounded-full bg-white text-gray-500 hover:text-gray-800 hover:bg-[#eef2f8] transition-colors"
                  >
                    {hint}
                  </button>
                )
              )}
            </div>
          </div>
        )}

        {result && (
          <div>
            <ChartContainer option={result.echarts_option} title={result.title} />
            {result.explanation && (
              <div className="px-4 pb-4">
                <p className="text-xs text-gray-400 leading-relaxed bg-[#fafafa]/50 rounded-lg p-3 border border-[#e5e7eb]">
                  {result.explanation}
                </p>
              </div>
            )}
            {result.data && result.data.length > 0 && (
              <div className="px-4 pb-4">
                <div className="overflow-x-auto rounded-lg border border-[#e5e7eb]">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[#fafafa]">
                        {Object.keys(result.data[0] as object).map((key) => (
                          <th key={key} className="px-3 py-2 text-left text-gray-400 font-medium">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(result.data as Record<string, unknown>[]).map((row, i) => (
                        <tr key={i} className="border-t border-[#e5e7eb] hover:bg-[#fafafa]/50">
                          {Object.values(row).map((val, j) => (
                            <td key={j} className="px-3 py-2 text-gray-700">
                              {String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
