"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Archive, Loader2, Pause, Play, Search, Trash2, Upload, X } from "lucide-react";
import {
  cancelIngestionJob,
  deletePaper,
  deletePapers,
  fetchIngestionJobs,
  fetchPapers,
  pauseIngestionJob,
  resumeIngestionJob,
  uploadBatchZip,
  uploadPDF,
} from "@/lib/api";
import { DomainMatrix } from "@/components/library/domain-matrix";
import { DomainManager } from "@/components/domains/domain-manager";
import { useDomains } from "@/hooks/use-domains";

interface Paper {
  id: string;
  title: string;
  authors: string | null;
  year: number | null;
  status: string;
}

interface IngestionJob {
  id: string;
  status: string;
  total: number;
  succeeded: number;
  failed: number;
  duplicate: number;
  current_file: string | null;
}

const PAGE_SIZE = 20;

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [uploadDomainId, setUploadDomainId] = useState<string>("unclassified");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [totalPapers, setTotalPapers] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "error" | "info" } | null>(null);
  const pdfRef = useRef<HTMLInputElement>(null);
  const zipRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { domains, loadDomains, addDomain, editDomain, removeDomain } = useDomains();

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchIngestionJobs();
      setJobs(data.items || []);
    } catch {
      setJobs([]);
    }
  }, []);

  const loadPapers = useCallback(async () => {
    try {
      const data = await fetchPapers({
        page,
        page_size: PAGE_SIZE,
        keyword: keyword || undefined,
        domain_id: selectedDomainId || undefined,
      });
      setPapers(data.items || []);
      setTotalPapers(data.total || 0);
    } catch {
      setMessage({ text: "加载文献列表失败", type: "error" });
    }
  }, [keyword, page, selectedDomainId]);

  useEffect(() => {
    loadJobs();
  }, [loadDomains, loadJobs]);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  useEffect(() => {
    setPage(1);
  }, [selectedDomainId]);

  useEffect(() => {
    if (domains.length === 0) return;
    if (!domains.some((domain) => domain.id === uploadDomainId)) {
      setUploadDomainId(domains.find((domain) => domain.id === "unclassified")?.id || domains[0].id);
    }
    if (selectedDomainId && !domains.some((domain) => domain.id === selectedDomainId)) {
      setSelectedDomainId(null);
    }
  }, [domains, selectedDomainId, uploadDomainId]);

  useEffect(() => {
    const hasActiveJob = jobs.some((job) => ["extracting", "queued", "running", "paused"].includes(job.status));
    const hasProcessingPaper = papers.some((paper) => paper.status === "processing");

    if ((hasActiveJob || hasProcessingPaper) && !pollRef.current) {
      pollRef.current = setInterval(() => {
        loadPapers();
        loadJobs();
        loadDomains();
      }, 3000);
    } else if (!hasActiveJob && !hasProcessingPaper && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobs, papers, loadDomains, loadJobs, loadPapers]);

  const selectedDomain = useMemo(() => {
    return domains.find((domain) => domain.id === selectedDomainId) || null;
  }, [domains, selectedDomainId]);

  const activeSummary = useMemo(() => {
    if (selectedDomain) return selectedDomain;
    return {
      id: "all",
      name: "全部领域",
      paper_count: domains.reduce((sum, domain) => sum + domain.paper_count, 0),
      ingested_count: domains.reduce((sum, domain) => sum + domain.ingested_count, 0),
      processing_count: domains.reduce((sum, domain) => sum + domain.processing_count, 0),
      failed_count: domains.reduce((sum, domain) => sum + domain.failed_count, 0),
    } as const;
  }, [domains, selectedDomain]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setMessage(null);
    try {
      const result = await uploadPDF(file, uploadDomainId);
      if (result.status === "duplicate") {
        setMessage({ text: "这篇文献已经存在，已跳过", type: "info" });
      }
      await loadPapers();
      await loadDomains();
      await loadJobs();
    } catch {
      setMessage({ text: "上传失败", type: "error" });
    } finally {
      setUploading(false);
    }
  };

  const handleBatchUpload = async (file: File) => {
    setUploading(true);
    setMessage(null);
    try {
      await uploadBatchZip(file, false, uploadDomainId);
      await loadPapers();
      await loadDomains();
      await loadJobs();
    } catch {
      setMessage({ text: "批量导入失败", type: "error" });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (paperId: string) => {
    if (!window.confirm("确定要删除这篇文献吗？")) return;
    try {
      setDeleting(true);
      await deletePaper(paperId);
      setMessage({ text: "已删除 1 篇文献", type: "info" });
    } catch (error: unknown) {
      setMessage({ text: error instanceof Error ? error.message : "删除失败", type: "error" });
    } finally {
      setDeleting(false);
      await loadPapers();
      await loadDomains();
    }
  };

  const toggleSelect = (paperId: string) => {
    setSelectedPapers((prev) => {
      const next = new Set(prev);
      if (next.has(paperId)) next.delete(paperId);
      else next.add(paperId);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedPapers.size === papers.length) {
      setSelectedPapers(new Set());
    } else {
      setSelectedPapers(new Set(papers.map((p) => p.id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedPapers.size === 0) return;
    if (!window.confirm(`确定要删除选中的 ${selectedPapers.size} 篇文献吗？此操作不可撤销。`)) return;
    setDeleting(true);
    try {
      const result = await deletePapers(Array.from(selectedPapers));
      setSelectedPapers(new Set());
      setMessage({ text: `已删除 ${result.deleted} 篇文献`, type: "info" });
    } catch (error: unknown) {
      setMessage({ text: error instanceof Error ? error.message : "批量删除失败", type: "error" });
    } finally {
      setDeleting(false);
      await loadPapers();
      await loadDomains();
    }
  };

  const handlePauseJob = async (jobId: string) => {
    try {
      await pauseIngestionJob(jobId);
      await loadJobs();
    } catch {
      setMessage({ text: "暂停任务失败", type: "error" });
    }
  };

  const handleResumeJob = async (jobId: string) => {
    try {
      await resumeIngestionJob(jobId);
      await loadJobs();
    } catch {
      setMessage({ text: "恢复任务失败", type: "error" });
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelIngestionJob(jobId);
      await loadJobs();
    } catch {
      setMessage({ text: "删除任务失败", type: "error" });
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case "extracting":
        return "解压中";
      case "queued":
        return "排队中";
      case "running":
        return "处理中";
      case "paused":
        return "已暂停";
      case "cancelled":
        return "已取消";
      case "done":
        return "已完成";
      case "failed":
        return "失败";
      case "partial_failed":
        return "部分失败";
      default:
        return status;
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-heading text-[#1a2744]">文献库</h1>
            <p className="mt-1 text-sm text-gray-500">
              领域矩阵 + 导入统计 + 文献列表
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              导入领域
              <select
                value={uploadDomainId}
                onChange={(e) => setUploadDomainId(e.target.value)}
                className="rounded-md border border-[#d1d5db] bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#1a2744] focus:outline-none"
              >
                {domains.map((domain) => (
                  <option key={domain.id} value={domain.id}>
                    {domain.name}
                  </option>
                ))}
              </select>
            </label>

            <DomainManager
              domains={domains}
              onCreate={async (payload) => {
                const nextDomains = await addDomain(payload);
                const created = nextDomains.find((domain) => domain.id === payload.id);
                if (created) setUploadDomainId(created.id);
                await loadPapers();
              }}
              onUpdate={async (domainId, payload) => {
                await editDomain(domainId, payload);
                await loadPapers();
              }}
              onDelete={async (domainId) => {
                await removeDomain(domainId);
                if (selectedDomainId === domainId) setSelectedDomainId(null);
                if (uploadDomainId === domainId) setUploadDomainId("unclassified");
                await loadPapers();
              }}
              onRefresh={loadDomains}
            />

            <input
              ref={zipRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleBatchUpload(file);
                e.target.value = "";
              }}
            />
            <button
              onClick={() => zipRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-2 rounded-md border border-[#1a2744] px-4 py-2 text-sm font-medium text-[#1a2744] transition-colors hover:bg-[#eef2f8] disabled:opacity-50"
            >
              <Archive className="h-4 w-4" />
              批量导入
            </button>

            <input
              ref={pdfRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
                e.target.value = "";
              }}
            />
            <button
              onClick={() => pdfRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-2 rounded-md bg-[#1a2744] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#24395f] disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {uploading ? "上传中..." : "上传 PDF"}
            </button>
          </div>
        </div>

        {message && (
          <div
            className={`mt-4 rounded-md border px-4 py-3 text-sm ${
              message.type === "error"
                ? "border-red-200 bg-red-50 text-red-600"
                : "border-blue-200 bg-blue-50 text-blue-600"
            }`}
          >
            {message.text}
          </div>
        )}

        <section className="mt-6">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#1a2744]">领域矩阵</h2>
              <p className="mt-1 text-xs text-gray-500">
                点击方块筛选对应领域的文献，上传时会默认写入你选中的导入领域。
              </p>
            </div>
            <button
              onClick={() => setSelectedDomainId(null)}
              className="text-xs font-medium text-[#2c5282] hover:text-[#1a2744]"
            >
              查看全部
            </button>
          </div>

          <DomainMatrix
            domains={domains}
            selectedDomainId={selectedDomainId}
            onSelectDomain={(domainId) => {
              setSelectedDomainId(domainId);
              if (domainId) setUploadDomainId(domainId);
            }}
          />
        </section>

        <section className="mt-6 border-t border-[#e5e7eb] pt-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#1a2744]">
                当前领域: {activeSummary.name}
              </h2>
              <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
                <span>总数 {activeSummary.paper_count}</span>
                <span>已入库 {activeSummary.ingested_count}</span>
                <span>处理中 {activeSummary.processing_count}</span>
                <span>失败 {activeSummary.failed_count}</span>
              </div>
            </div>

            <div className="relative w-full max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <input
                value={keyword}
                onChange={(e) => {
                  setKeyword(e.target.value);
                  setPage(1);
                }}
                placeholder="搜索标题..."
                className="w-full rounded-md border border-[#d1d5db] py-2 pl-9 pr-3 text-sm text-gray-700 placeholder:text-gray-400 focus:border-[#1a2744] focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-4 overflow-hidden rounded-lg border border-[#e5e7eb]">
            {/* Batch delete toolbar */}
            {selectedPapers.size > 0 && (
              <div className="flex items-center gap-3 bg-red-50 border-b border-red-200 px-5 py-2.5">
                <span className="text-sm text-red-700 font-medium">
                  已选 {selectedPapers.size} 篇
                </span>
                <button
                  onClick={handleBatchDelete}
                  disabled={deleting}
                  className="inline-flex items-center gap-1.5 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-50"
                >
                  {deleting ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                  {deleting ? "删除中..." : "批量删除"}
                </button>
                <button
                  onClick={() => setSelectedPapers(new Set())}
                  disabled={deleting}
                  className="text-xs text-red-600 hover:text-red-800 disabled:opacity-50"
                >
                  取消选择
                </button>
              </div>
            )}

            <div className="grid grid-cols-[36px_1fr_140px_80px_90px] gap-4 bg-[#fafafa] px-5 py-2.5 text-xs font-medium uppercase tracking-wider text-gray-500">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={papers.length > 0 && selectedPapers.size === papers.length}
                  onChange={selectAll}
                  className="h-3.5 w-3.5 rounded border-gray-300"
                />
              </div>
              <span>标题</span>
              <span>作者</span>
              <span>年份</span>
              <span>状态</span>
            </div>

            {papers.length === 0 && (
              <div className="px-5 py-12 text-center text-sm text-gray-400">
                当前领域暂无文献
              </div>
            )}

            {papers.map((paper) => (
              <div
                key={paper.id}
                className="group grid grid-cols-[36px_1fr_140px_80px_90px] gap-4 border-b border-[#f3f4f6] px-5 py-3 text-sm text-gray-700 last:border-b-0 hover:bg-[#fafafa]"
              >
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedPapers.has(paper.id)}
                    onChange={() => toggleSelect(paper.id)}
                    disabled={deleting}
                    className="h-3.5 w-3.5 rounded border-gray-300"
                  />
                </div>
                <span className="truncate font-medium">{paper.title}</span>
                <span className="truncate text-gray-500">{paper.authors || "未知"}</span>
                <span className="text-gray-500">{paper.year || "-"}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-[10px] font-medium ${
                      paper.status === "ingested"
                        ? "bg-[#eef2f8] text-[#2c5282]"
                        : paper.status === "processing"
                          ? "bg-green-50 text-green-600"
                          : "bg-red-50 text-red-600"
                    }`}
                  >
                    {paper.status === "ingested" ? "已入库" : paper.status === "processing" ? "处理中" : "失败"}
                  </span>
                  <button
                    onClick={() => handleDelete(paper.id)}
                    disabled={deleting}
                    className="rounded p-1 text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 disabled:opacity-30"
                    aria-label="删除文献"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {totalPapers > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-600">
              <button
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={page <= 1}
                className="rounded-md border border-[#e5e7eb] px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-30"
              >
                上一页
              </button>
              <span className="text-gray-500">
                第 {page} 页 / 共 {Math.ceil(totalPapers / PAGE_SIZE)} 页（{totalPapers} 篇）
              </span>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={page >= Math.ceil(totalPapers / PAGE_SIZE)}
                className="rounded-md border border-[#e5e7eb] px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-30"
              >
                下一页
              </button>
            </div>
          )}
        </section>

        <section className="mt-8">
          <h2 className="text-sm font-semibold text-[#1a2744]">批量导入任务</h2>
          <div className="mt-3 space-y-3">
            {jobs.map((job) => {
              const active = ["extracting", "queued", "running", "paused"].includes(job.status);
              return (
                <div key={job.id} className="rounded-lg border border-[#e5e7eb] p-4">
                  <div className="mb-2 flex items-center justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-2">
                      {job.status === "extracting" && <Loader2 className="h-4 w-4 animate-spin text-[#1a2744]" />}
                      {job.status === "running" && <Loader2 className="h-4 w-4 animate-spin text-[#1a2744]" />}
                      {job.status === "paused" && <Pause className="h-4 w-4 text-amber-500" />}
                      {job.status === "failed" && <X className="h-4 w-4 text-red-500" />}
                      <span className="text-sm font-medium text-gray-700">{statusLabel(job.status)}</span>
                      <span className="text-xs text-gray-500">
                        {job.succeeded + job.failed + job.duplicate}/{job.total || "?"}
                        {job.succeeded > 0 ? ` 成功${job.succeeded}` : ""}
                        {job.failed > 0 ? ` 失败${job.failed}` : ""}
                        {job.duplicate > 0 ? ` 重复${job.duplicate}` : ""}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      {job.status === "paused" ? (
                        <button
                          onClick={() => handleResumeJob(job.id)}
                          className="flex items-center gap-1 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-600 hover:bg-emerald-100"
                        >
                          <Play className="h-3 w-3" />
                          继续
                        </button>
                      ) : active ? (
                        <button
                          onClick={() => handlePauseJob(job.id)}
                          className="rounded bg-amber-50 px-2 py-1 text-xs text-amber-600 hover:bg-amber-100"
                        >
                          暂停
                        </button>
                      ) : null}
                      <button
                        onClick={() => handleCancelJob(job.id)}
                        className="rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100"
                      >
                        删除
                      </button>
                    </div>
                  </div>

                  {active && job.total > 0 && (
                    <div className="h-2 overflow-hidden rounded-full bg-[#e5e7eb]">
                      <div
                        className="h-full rounded-full bg-[#1a2744] transition-all duration-500"
                        style={{
                          width: `${((job.succeeded + job.failed + job.duplicate) / job.total) * 100}%`,
                        }}
                      />
                    </div>
                  )}

                  {job.current_file && <div className="mt-2 truncate text-xs text-gray-500">{job.current_file}</div>}
                </div>
              );
            })}
            {jobs.length === 0 && <div className="text-sm text-gray-400">暂无批量导入任务</div>}
          </div>
        </section>
      </div>
    </div>
  );
}
