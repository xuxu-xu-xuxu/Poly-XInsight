"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Loader2, Pickaxe, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchThermalConductivePropertyRecords,
  triggerThermalConductivePropertyMining,
} from "@/lib/api";

interface Paper {
  id: string;
  title: string;
  status: string;
}

interface PropertyRecord {
  id: number;
  paper_id: string;
  filler_name: string;
  filler_type: string | null;
  matrix_name: string | null;
  filler_content: number | null;
  filler_content_unit: string | null;
  particle_size: string | null;
  surface_treatment: string | null;
  property_category: string;
  property_name: string;
  value: number | null;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  temperature_value: number | null;
  temperature_unit: string | null;
  frequency: number | null;
  method: string;
  confidence: number;
  status: string;
  source_chunk_id: string | null;
}

function categoryLabel(cat: string) {
  const map: Record<string, string> = {
    thermal: "导热",
    rheological: "流变",
    mechanical: "力学",
    composition: "组成",
  };
  return map[cat] || cat;
}

function categoryColor(cat: string) {
  const map: Record<string, string> = {
    thermal: "bg-orange-100 text-orange-700",
    rheological: "bg-purple-100 text-purple-700",
    mechanical: "bg-blue-100 text-blue-700",
    composition: "bg-green-100 text-green-700",
  };
  return map[cat] || "bg-gray-100 text-gray-700";
}

function propertyLabel(name: string) {
  const map: Record<string, string> = {
    thermal_conductivity: "导热率",
    thermal_resistance: "热阻",
    thermal_diffusivity: "热扩散系数",
    cte: "CTE",
    complex_viscosity: "复合黏度",
    shear_viscosity: "剪切黏度",
    storage_modulus: "储能模量 G'",
    loss_modulus: "损耗模量 G\"",
    tan_delta: "tan δ",
    yield_stress: "屈服应力",
    tensile_strength: "拉伸强度",
    youngs_modulus: "杨氏模量",
    elongation_at_break: "断裂伸长率",
    flexural_strength: "弯曲强度",
    flexural_modulus: "弯曲模量",
    impact_strength: "冲击强度",
    hardness: "硬度",
    compressive_strength: "压缩强度",
    shear_strength: "剪切强度",
    filler_content: "填料含量",
  };
  return map[name] || name;
}

function valueText(record: PropertyRecord) {
  if (record.value === null || record.value === undefined) return "-";
  const v = record.value;
  const u = record.unit ? ` ${record.unit}` : "";
  if (record.property_name === "elongation_at_break" || record.property_name === "tan_delta") {
    return `${v.toFixed(1)}${u}`;
  }
  if (record.property_name === "thermal_conductivity" && v < 1) {
    return `${v.toFixed(3)}${u}`;
  }
  // For scientific notation for large/small values
  if (v > 10000 || (v < 0.001 && v > 0)) {
    return `${v.toExponential(2)}${u}`;
  }
  return `${Number(v.toPrecision(4))}${u}`;
}

export function ThermalMiningPanel({ papers }: { papers: Paper[] }) {
  const [records, setRecords] = useState<PropertyRecord[]>([]);
  const [mining, setMining] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");

  const load = useCallback(async () => {
    setError("");
    try {
      const params: Record<string, unknown> = { confidence_min: 0.5, page_size: 500 };
      if (categoryFilter) params.category = categoryFilter;
      const data = await fetchThermalConductivePropertyRecords(params);
      setRecords(data.items || []);
    } catch {
      setError("加载导热材料性质记录失败");
    }
  }, [categoryFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const runMining = async () => {
    setMining(true);
    setMessage("");
    setError("");
    try {
      await triggerThermalConductivePropertyMining({ replace: false, limit_per_query: 200 });
      setMessage("挖掘任务已启动，后台正在抽取性质数据...");
      // Poll for results: refresh at 5s, 12s, 20s, 30s
      for (const delay of [5000, 12000, 20000, 30000]) {
        window.setTimeout(load, delay);
      }
    } catch {
      setError("启动导热材料性质抽取失败");
    } finally {
      // Keep button disabled for 30s to prevent concurrent mining calls
      window.setTimeout(() => setMining(false), 30000);
    }
  };

  const filtered =
    categoryFilter
      ? records.filter((r) => r.property_category === categoryFilter)
      : records;

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-[#e5e7eb] p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Pickaxe className="h-4 w-4 text-[#1a2744]" />
            导热材料性质抽取
          </h2>
          <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" />
            刷新
          </Button>
        </div>

        <Button
          size="sm"
          className="mt-3 w-full gap-1.5 bg-[#1a2744] text-white hover:bg-[#2d3f5e]"
          onClick={runMining}
          disabled={mining}
        >
          {mining ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
          从已入库 chunks 重新抽取性质
        </Button>
        <p className="mt-2 text-xs text-gray-500">
          当前只读取导热高分子领域已入库的 ES/Milvus chunks，不重建 embedding。
        </p>
        {message && <p className="mt-2 text-xs text-green-600">{message}</p>}
        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}

        {/* Category filter tabs */}
        <div className="mt-3 flex flex-wrap gap-1">
          {["", "thermal", "rheological", "mechanical", "composition"].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
                categoryFilter === cat
                  ? "bg-[#1a2744] text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {cat ? categoryLabel(cat) : "全部"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-3 text-xs text-gray-500">
          已入库文献 {papers.filter((p) => p.status === "ingested").length} 篇，
          性质记录 {records.length} 条
        </div>

        <div className="space-y-2">
          {filtered.map((record) => (
            <div key={record.id} className="rounded border border-[#e5e7eb] bg-white p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${categoryColor(record.property_category)}`}>
                      {categoryLabel(record.property_category)}
                    </span>
                    <span className="truncate text-sm font-medium text-gray-900">
                      {record.filler_name || "unknown"}
                      {record.matrix_name ? ` / ${record.matrix_name}` : ""}
                    </span>
                  </div>
                  <div className="mt-1 text-[12px] text-gray-500">
                    {propertyLabel(record.property_name)}
                    {record.filler_content ? ` · ${record.filler_content} ${record.filler_content_unit || ""}` : ""}
                    {record.temperature_value ? ` · ${record.temperature_value} ${record.temperature_unit || ""}` : ""}
                  </div>
                </div>
                <span className="shrink-0 rounded bg-[#eef2f8] px-2 py-1 text-[11px] font-medium text-[#1a2744]">
                  {valueText(record)}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400">
                <span>置信度 {(record.confidence * 100).toFixed(0)}%</span>
                <span>{record.method || "unknown"}</span>
                <span className="truncate">{record.source_chunk_id || "-"}</span>
              </div>
            </div>
          ))}

          {filtered.length === 0 && records.length === 0 && (
            <div className="py-12 text-center text-sm text-gray-500">
              暂无性质记录。将文献归入导热高分子领域并导入后，点击抽取按钮自动挖掘。
            </div>
          )}

          {filtered.length === 0 && records.length > 0 && (
            <div className="py-12 text-center text-sm text-gray-500">
              该类别暂无记录，尝试切换上方过滤标签。
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
