"use client";

import { useMemo, useState } from "react";
import { Check, Pencil, Plus, RefreshCw, Settings2, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LibraryDomainSummary } from "@/components/library/domain-matrix";

const COLORS = ["#1a2744", "#2c5282", "#059669", "#b45309", "#7c3aed", "#be123c", "#64748b"];

function slugifyName(name: string) {
  const ascii = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (/^[a-z0-9][a-z0-9-]*$/.test(ascii)) return ascii;
  return `domain-${Date.now().toString(36)}`;
}

interface Props {
  domains: LibraryDomainSummary[];
  onCreate: (payload: { id: string; name: string; description?: string; color?: string; sort_order?: number }) => Promise<void>;
  onUpdate: (domainId: string, payload: { name?: string; description?: string; color?: string; sort_order?: number }) => Promise<void>;
  onDelete: (domainId: string) => Promise<void>;
  onRefresh: () => Promise<unknown>;
}

export function DomainManager({ domains, onCreate, onUpdate, onDelete, onRefresh }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sortedDomains = useMemo(() => [...domains].sort((a, b) => a.sort_order - b.sort_order), [domains]);
  const editingDomain = sortedDomains.find((domain) => domain.id === editingId) || null;

  const resetForm = () => {
    setName("");
    setDescription("");
    setColor(COLORS[0]);
    setEditingId(null);
    setError("");
  };

  const startEdit = (domain: LibraryDomainSummary) => {
    setEditingId(domain.id);
    setName(domain.name);
    setDescription(domain.description || "");
    setColor(domain.color || COLORS[0]);
    setError("");
  };

  const submit = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("请输入领域名称");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (editingDomain) {
        await onUpdate(editingDomain.id, {
          name: trimmedName,
          description: description.trim() || undefined,
          color,
        });
      } else {
        const nextSort = sortedDomains.reduce((max, domain) => Math.max(max, domain.sort_order || 0), 0) + 1;
        await onCreate({
          id: slugifyName(trimmedName),
          name: trimmedName,
          description: description.trim() || undefined,
          color,
          sort_order: nextSort,
        });
      }
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存领域失败");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (domain: LibraryDomainSummary) => {
    setBusy(true);
    setError("");
    try {
      await onDelete(domain.id);
      if (editingId === domain.id) resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除领域失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setOpen(true)}>
        <Settings2 className="h-3.5 w-3.5" />
        管理领域
      </Button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 px-4">
          <div className="w-full max-w-3xl rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-[#e5e7eb] px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-[#1a2744]">领域管理</h2>
                <p className="mt-1 text-xs text-gray-500">新增或调整领域后，文献导入、聊天范围和下载导入会共享同一套列表。</p>
              </div>
              <button className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-0 md:grid-cols-[280px_1fr]">
              <div className="border-b border-[#e5e7eb] p-5 md:border-b-0 md:border-r">
                <div className="space-y-3">
                  <label className="block text-xs font-medium text-gray-600">
                    领域名称
                    <input
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      className="mt-1 w-full rounded-md border border-[#d1d5db] px-3 py-2 text-sm outline-none focus:border-[#1a2744]"
                      placeholder="例如：钠离子电池"
                    />
                  </label>
                  <label className="block text-xs font-medium text-gray-600">
                    描述
                    <textarea
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      className="mt-1 h-20 w-full resize-none rounded-md border border-[#d1d5db] px-3 py-2 text-sm outline-none focus:border-[#1a2744]"
                      placeholder="可选"
                    />
                  </label>
                  <div>
                    <div className="text-xs font-medium text-gray-600">颜色</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {COLORS.map((item) => (
                        <button
                          key={item}
                          onClick={() => setColor(item)}
                          className={`h-7 w-7 rounded-full border-2 ${color === item ? "border-[#1a2744]" : "border-white"}`}
                          style={{ backgroundColor: item }}
                          aria-label={item}
                        >
                          {color === item && <Check className="mx-auto h-3.5 w-3.5 text-white" />}
                        </button>
                      ))}
                    </div>
                  </div>
                  {error && <p className="text-xs text-red-500">{error}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" className="gap-1.5 bg-[#1a2744] text-white hover:bg-[#24395f]" onClick={submit} disabled={busy}>
                      {editingDomain ? <Pencil className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                      {editingDomain ? "保存修改" : "新增领域"}
                    </Button>
                    {editingDomain && (
                      <Button size="sm" variant="outline" onClick={resetForm} disabled={busy}>
                        取消
                      </Button>
                    )}
                  </div>
                </div>
              </div>

              <div className="max-h-[520px] overflow-y-auto p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-gray-500">当前领域</h3>
                  <Button size="xs" variant="ghost" className="gap-1" onClick={() => onRefresh()} disabled={busy}>
                    <RefreshCw className="h-3 w-3" />
                    刷新
                  </Button>
                </div>
                <div className="space-y-2">
                  {sortedDomains.map((domain) => (
                    <div key={domain.id} className="flex items-center gap-3 rounded-md border border-[#e5e7eb] px-3 py-2">
                      <span className="h-8 w-8 shrink-0 rounded-md" style={{ backgroundColor: domain.color || "#1a2744" }} />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-gray-800">{domain.name}</div>
                        <div className="truncate text-xs text-gray-500">
                          {domain.id} · {domain.paper_count} 篇
                          {domain.is_default ? " · 默认领域" : ""}
                        </div>
                      </div>
                      <button
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-[#1a2744]"
                        onClick={() => startEdit(domain)}
                        disabled={busy}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-30"
                        onClick={() => remove(domain)}
                        disabled={busy || domain.is_default}
                        title={domain.is_default ? "默认领域不可删除" : "删除领域"}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
