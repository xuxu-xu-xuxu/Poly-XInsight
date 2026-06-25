"use client";
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";

interface Props {
  option: object;
  title: string;
}

const lightThemeDefaults = {
  backgroundColor: "transparent",
  textStyle: { color: "#374151" },
};

export function ChartContainer({ option, title }: Props) {
  const mergedOption = useMemo(() => {
    const backendOption = (option && typeof option === "object" ? option : {}) as Record<string, unknown>;
    // Only apply light theme defaults if backend didn't already set them
    const result: Record<string, unknown> = {
      ...lightThemeDefaults,
      ...backendOption,
    };
    // Ensure grid has sensible defaults if not provided
    if (!result.grid) {
      result.grid = { left: "3%", right: "7%", bottom: "12%", containLabel: true };
    }
    return result;
  }, [option]);

  if (!option || Object.keys(option as object).length === 0) {
    return (
      <div className="p-4">
        <h3 className="text-sm font-heading font-semibold mb-3 text-[#1a2744]">{title}</h3>
        <div className="bg-white border border-[#e5e7eb] rounded-lg p-2 flex items-center justify-center" style={{ height: "280px" }}>
          <span className="text-sm text-gray-400">暂无图表数据</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-sm font-heading font-semibold mb-3 text-[#1a2744]">
        {title}
      </h3>
      <div className="bg-white border border-[#e5e7eb] rounded-lg p-2">
        <ReactECharts
          option={mergedOption}
          style={{ height: "280px" }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </div>
  );
}
