"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Neologismo } from "@/types";
import { fetchNeologismosPage, darLike, darDeslike } from "@/lib/api";

interface UseNeologismosOptions {
  search?: string;
  tag?: string;
}

export function useNeologismos(options: UseNeologismosOptions = {}) {
  const { search, tag } = options;
  const [data, setData] = useState<Neologismo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageRef = useRef(1);

  // Recarrega do zero sempre que os filtros de busca/tag mudarem.
  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      pageRef.current = 1;
      // Home pública mostra apenas neologismos aprovados.
      const result = await fetchNeologismosPage({ status: "aprovado", page: 1, search, tag });
      setData(result.results);
      setHasMore(Boolean(result.next));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [search, tag]);

  useEffect(() => {
    load();
  }, [load]);

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return;
    try {
      setLoadingMore(true);
      const nextPage = pageRef.current + 1;
      const result = await fetchNeologismosPage({ status: "aprovado", page: nextPage, search, tag });
      setData((prev) => [...prev, ...result.results]);
      setHasMore(Boolean(result.next));
      pageRef.current = nextPage;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar mais itens");
    } finally {
      setLoadingMore(false);
    }
  }, [loading, loadingMore, hasMore, search, tag]);

  const handleLike = useCallback(async (id: number) => {
    try {
      const result = await darLike(id);
      setData((prev) =>
        prev.map((n) =>
          n.id === id
            ? { ...n, total_likes: result.likes ?? n.total_likes, total_deslikes: result.deslikes ?? n.total_deslikes }
            : n
        )
      );
    } catch {
      // silently fail — optimistic update could be added
    }
  }, []);

  const handleDeslike = useCallback(async (id: number) => {
    try {
      const result = await darDeslike(id);
      setData((prev) =>
        prev.map((n) =>
          n.id === id
            ? { ...n, total_likes: result.likes ?? n.total_likes, total_deslikes: result.deslikes ?? n.total_deslikes }
            : n
        )
      );
    } catch {
      // silently fail
    }
  }, []);

  return {
    data,
    loading,
    loadingMore,
    hasMore,
    error,
    refetch: load,
    loadMore,
    onLike: handleLike,
    onDeslike: handleDeslike,
  };
}

