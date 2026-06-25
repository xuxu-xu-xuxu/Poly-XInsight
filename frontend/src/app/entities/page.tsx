"use client";

import { EntityBrowser } from "@/components/viz/entity-browser";

export default function EntitiesPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pb-0 pt-8">
        <h1 className="mb-1 text-2xl font-heading text-[#1a2744]">研究导航</h1>
        <p className="text-sm text-gray-500">
          用主题簇组织文献，再沿着问题、方法、材料和性质快速定位当前方向的关键论文。
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <EntityBrowser />
      </div>
    </div>
  );
}
