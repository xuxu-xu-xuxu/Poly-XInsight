"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Database, Loader2, Network, Pickaxe, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchEntities, triggerClustering, triggerEntityMining } from "@/lib/api";
import { useDomains } from "@/hooks/use-domains";

interface TopicSignal {
  label: string;
  count: number;
}

interface TopicPaper {
  id: string;
  title: string;
  year?: number | null;
  journal?: string | null;
}

interface TopicCard {
  id: string;
  label: string;
  domain_id: string;
  domain_name?: string;
  is_fallback_topic?: boolean;
  paper_count: number;
  papers: TopicPaper[];
  highlights: {
    materials: TopicSignal[];
    methods: TopicSignal[];
    problems: TopicSignal[];
    properties: TopicSignal[];
  };
}

interface TopicPayload {
  items: TopicCard[];
  stats?: {
    topic_count: number;
    paper_count: number;
    domain_count: number;
    fallback_topic_count?: number;
  };
}

const sectionMeta: Array<{
  key: keyof TopicCard["highlights"];
  label: string;
  tone: string;
}> = [
  { key: "problems", label: "关键问题", tone: "bg-rose-50 text-rose-700 border-rose-200" },
  { key: "methods", label: "常用方法", tone: "bg-sky-50 text-sky-700 border-sky-200" },
  { key: "materials", label: "核心材料", tone: "bg-violet-50 text-violet-700 border-violet-200" },
  { key: "properties", label: "关注性质", tone: "bg-amber-50 text-amber-700 border-amber-200" },
];

export function EntityBrowser() {
  const { domains } = useDomains();
  const [payload, setPayload] = useState<TopicPayload>({ items: [] });
  const [loading, setLoading] = useState(false);
  const [clustering, setClustering] = useState(false);
  const [mining, setMining] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [domainId, setDomainId] = useState("");

  const selectedDomain = useMemo(
    () => domains.find((domain) => domain.id === domainId),
    [domains, domainId]
  );

  const loadTopics = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchEntities({
        domain_id: domainId || undefined,
        topic_limit: 10,
        papers_per_topic: 4,
      });
      setPayload({
        items: data.items || [],
        stats: data.stats,
      });
    } catch {
      setError("加载研究导航失败");
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  useEffect(() => {
    loadTopics();
  }, [loadTopics]);

  useEffect(() => {
    if (!polling) return;
    let cancelled = false;
    let timer: number | undefined;
    let attempts = 0;

    const run = async () => {
      attempts += 1;
      await loadTopics();
      if (cancelled) return;
      if (attempts >= 12) {
        setPolling(false);
        return;
      }
      timer = window.setTimeout(run, 4000);
    };

    timer = window.setTimeout(run, 2500);
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [polling, loadTopics]);

  const handleRecluster = async () => {
    setClustering(true);
    setError("");
    setMessage("");
    try {
      await triggerClustering();
      setMessage("主题聚类已启动，页面会自动刷新一段时间，把新的主题簇接进来。");
      setPolling(true);
    } catch {
      setError("启动主题聚类失败");
    } finally {
      setClustering(false);
    }
  };

  const handleMineSignals = async () => {
    setMining(true);
    setError("");
    setMessage("");
    try {
      const result = await triggerEntityMining({
        domain_id: domainId || undefined,
        replace: true,
        chunk_limit: 10000,
      });
      setMessage(`已处理 ${result.paper_count || 0} 篇文献，页面会继续自动刷新，把新的研究信号接入主题导航。`);
      setPolling(true);
      await loadTopics();
    } catch {
      setError("补采研究信号失败");
    } finally {
      setMining(false);
    }
  };

  const stats = payload.stats || {
    topic_count: payload.items.length,
    paper_count: payload.items.reduce((sum, item) => sum + item.paper_count, 0),
    domain_count: payload.items.length ? 1 : 0,
    fallback_topic_count: payload.items.filter((item) => item.is_fallback_topic).length,
  };

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-[#e5e7eb] bg-white px-4 py-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-[#1a2744]">
              <Network className="h-4 w-4" />
              主题导航
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              先按论文主题簇浏览，再沿着问题、方法、材料和性质快速定位相关文献。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={domainId}
              onChange={(event) => setDomainId(event.target.value)}
              className="h-9 min-w-[220px] rounded-md border border-[#d1d5db] bg-white px-3 text-sm text-gray-700 outline-none focus:border-[#1a2744]"
            >
              <option value="">全部领域</option>
              {domains.map((domain) => (
                <option key={domain.id} value={domain.id}>
                  {domain.name}
                </option>
              ))}
            </select>
            <Button size="sm" variant="outline" onClick={loadTopics} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              刷新导航
            </Button>
            <Button size="sm" variant="outline" onClick={handleRecluster} disabled={clustering}>
              {clustering ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              更新主题簇
            </Button>
            <Button size="sm" onClick={handleMineSignals} disabled={mining}>
              {mining ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Pickaxe className="h-3.5 w-3.5" />}
              补采研究信号
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-[#e5e7eb] bg-[#fafafa] px-3 py-3">
            <div className="text-[11px] text-gray-500">主题簇</div>
            <div className="mt-1 text-xl font-semibold text-[#1a2744]">{stats.topic_count}</div>
          </div>
          <div className="rounded-md border border-[#e5e7eb] bg-[#fafafa] px-3 py-3">
            <div className="text-[11px] text-gray-500">覆盖论文</div>
            <div className="mt-1 text-xl font-semibold text-[#1a2744]">{stats.paper_count}</div>
          </div>
          <div className="rounded-md border border-[#e5e7eb] bg-[#fafafa] px-3 py-3">
            <div className="text-[11px] text-gray-500">当前领域</div>
            <div className="mt-1 text-sm font-medium text-[#1a2744]">
              {selectedDomain?.name || "全部领域"}
            </div>
          </div>
        </div>

        {message && <div className="mt-3 text-xs text-emerald-700">{message}</div>}
        {error && <div className="mt-3 text-xs text-rose-600">{error}</div>}
        {!!stats.fallback_topic_count && (
          <div className="mt-3 text-xs text-amber-700">
            当前还有 {stats.fallback_topic_count} 个主题簇在使用兜底命名，通常说明真实聚类标签还没完全接进来。
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-[#fcfcfd] px-4 py-4">
        {!loading && payload.items.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-[#d6d9e0] bg-white py-16">
            <Database className="h-8 w-8 text-gray-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700">还没有可浏览的主题簇</p>
              <p className="mt-1 text-xs text-gray-500">
                先保证文献已入库，再执行主题聚类和研究信号抽取。
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-2">
          {payload.items.map((topic) => (
            <section key={topic.id} className="rounded-lg border border-[#e5e7eb] bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-gray-400">
                    {topic.domain_name || topic.domain_id}
                  </div>
                  <h3 className="mt-1 text-base font-semibold text-[#1a2744]">{topic.label}</h3>
                  {topic.is_fallback_topic && (
                    <div className="mt-1 text-[11px] text-amber-700">当前为兜底主题名，等待真实聚类标签覆盖</div>
                  )}
                </div>
                <div className="rounded-md bg-[#eef2f8] px-2.5 py-1 text-xs font-medium text-[#1a2744]">
                  {topic.paper_count} 篇
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {sectionMeta.map((section) => {
                  const items = topic.highlights[section.key] || [];
                  return (
                    <div key={section.key} className="rounded-md border border-[#eef0f4] p-3">
                      <div className="text-xs font-medium text-gray-600">{section.label}</div>
                      <div className="mt-2 flex min-h-12 flex-wrap gap-1.5">
                        {items.length > 0 ? (
                          items.map((item) => (
                            <span
                              key={`${section.key}-${item.label}`}
                              className={`rounded-md border px-2 py-1 text-xs ${section.tone}`}
                            >
                              {item.label}
                              <span className="ml-1 text-[11px] opacity-70">{item.count}</span>
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400">暂无稳定信号</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4">
                <div className="text-xs font-medium text-gray-600">代表论文</div>
                <div className="mt-2 space-y-2">
                  {topic.papers.map((paper) => (
                    <div key={paper.id} className="rounded-md border border-[#eef0f4] bg-[#fafafa] px-3 py-2">
                      <div className="text-sm font-medium text-gray-800">{paper.title}</div>
                      <div className="mt-1 text-xs text-gray-500">
                        {[paper.year, paper.journal].filter(Boolean).join(" · ") || paper.id}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
