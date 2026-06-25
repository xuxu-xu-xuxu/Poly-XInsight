"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Loader2, Pickaxe, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchSolidElectrolytePropertyRecords,
  triggerSolidElectrolytePropertyMining,
} from "@/lib/api";

interface Paper {
  id: string;
  title: string;
  status: string;
}

interface PropertyRecord {
  id: number;
  paper_id: string;
  material_name: string;
  normalized_formula: string | null;
  property_name: string;
  value: number | null;
  value_max: number | null;
  unit: string | null;
  temperature_value: number | null;
  temperature_unit: string | null;
  confidence: number;
  status: string;
  source_chunk_id: string | null;
}

function propertyLabel(name: string) {
  if (name === "ionic_conductivity") return "离子电导率";
  if (name === "electrochemical_window") return "电化学窗口";
  return name;
}

function valueText(record: PropertyRecord) {
  if (record.property_name === "electrochemical_window") {
    const low = record.value ?? 0;
    return `${low}-${record.value_max ?? "-"} ${record.unit || "V"}`;
  }
  if (record.value === null || record.value === undefined) return "-";
  return `${record.value.toExponential(2)} ${record.unit || ""}`;
}

export function DataMiningPanel({ papers }: { papers: Paper[] }) {
  const [records, setRecords] = useState<PropertyRecord[]>([]);
  const [mining, setMining] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await fetchSolidElectrolytePropertyRecords({ confidence_min: 0.6, page_size: 200 });
      setRecords(data.items || []);
    } catch {
      setError("加载结构化性质记录失败");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runMining = async () => {
    setMining(true);
    setMessage("");
    setError("");
    try {
      await triggerSolidElectrolytePropertyMining({ replace: true, limit_per_query: 100 });
      setMessage("已开始读取固态电池领域的入库 chunks，并抽取离子电导率、电化学窗口和材料公式。");
      window.setTimeout(load, 2500);
    } catch {
      setError("启动固态电解质性质抽取失败");
    } finally {
      setMining(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-[#e5e7eb] p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Pickaxe className="h-4 w-4 text-[#1a2744]" />
            固态电解质性质抽取
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
          当前只读取固态电池领域已入库的 ES/Milvus chunks，不重建 embedding。
        </p>
        {message && <p className="mt-2 text-xs text-green-600">{message}</p>}
        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <div className="mb-3 text-xs text-gray-500">
          已入库文献 {papers.filter((paper) => paper.status === "ingested").length} 篇，性质记录 {records.length} 条
        </div>

        <div className="space-y-2">
          {records.map((record) => (
            <div key={record.id} className="rounded border border-[#e5e7eb] bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-gray-900">
                    {record.material_name || "unknown"}
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-gray-500">
                    {propertyLabel(record.property_name)}
                    {record.normalized_formula ? ` · ${record.normalized_formula}` : ""}
                  </div>
                </div>
                <span className="rounded bg-[#eef2f8] px-2 py-1 text-[11px] font-medium text-[#1a2744]">
                  {valueText(record)}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-500">
                <span>置信度 {record.confidence.toFixed(2)}</span>
                <span>状态 {record.status}</span>
                <span>温度 {record.temperature_value ? `${record.temperature_value} ${record.temperature_unit || ""}` : "-"}</span>
                <span className="truncate">chunk {record.source_chunk_id || "-"}</span>
              </div>
            </div>
          ))}

          {records.length === 0 && (
            <div className="py-12 text-center text-sm text-gray-500">
              暂无性质记录。重新导入文献后，点击抽取按钮生成离子电导率和电化学窗口数据。
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
