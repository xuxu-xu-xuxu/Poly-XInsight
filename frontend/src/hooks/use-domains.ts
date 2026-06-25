"use client";

import { useCallback, useEffect, useState } from "react";
import { createDomain, deleteDomain, fetchDomains, updateDomain } from "@/lib/api";
import type { LibraryDomainSummary } from "@/components/library/domain-matrix";

export function useDomains() {
  const [domains, setDomains] = useState<LibraryDomainSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadDomains = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = (await fetchDomains()) as LibraryDomainSummary[];
      setDomains(data || []);
      return data || [];
    } catch {
      setDomains([]);
      setError("加载领域失败");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDomains();
  }, [loadDomains]);

  const addDomain = useCallback(async (payload: {
    id: string;
    name: string;
    description?: string;
    color?: string;
    sort_order?: number;
  }) => {
    await createDomain({ ...payload, is_default: false });
    return await loadDomains();
  }, [loadDomains]);

  const editDomain = useCallback(async (domainId: string, payload: {
    name?: string;
    description?: string;
    color?: string;
    sort_order?: number;
  }) => {
    await updateDomain(domainId, payload);
    return await loadDomains();
  }, [loadDomains]);

  const removeDomain = useCallback(async (domainId: string) => {
    await deleteDomain(domainId);
    return await loadDomains();
  }, [loadDomains]);

  return {
    domains,
    loading,
    error,
    loadDomains,
    addDomain,
    editDomain,
    removeDomain,
  };
}
