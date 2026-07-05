import { useEffect, useRef, useState, useCallback } from "react";
import api from "../services/api";
import { getCached, setCached, CACHE_TTL } from "../store/fleetStore";

export function useAutoRefresh<T>(
  key: string,
  endpoint: string,
  ttl = CACHE_TTL.fleet,
  transform?: (data: any) => T,
): { data: T | null; loading: boolean; refetch: () => void } {
  const [data,    setData]    = useState<T | null>(() => getCached<T>(key, ttl));
  const [loading, setLoading] = useState<boolean>(() => !getCached(key, ttl));
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeRef = useRef(true);

  const doFetch = useCallback(() => {
    const cached = getCached<T>(key, ttl);
    if (cached) {
      setData(cached);
      setLoading(false);
      // Schedule next check when this cache entry expires
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(doFetch, ttl);
      return;
    }
    setLoading(true);
    api.get(endpoint)
      .then(r => {
        if (!activeRef.current) return;
        const value = transform ? transform(r.data) : r.data as T;
        setCached(key, value);
        setData(value);
        setLoading(false);
        // Re-fetch exactly when TTL expires
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(doFetch, ttl);
      })
      .catch(() => {
        if (!activeRef.current) return;
        setLoading(false);
        // Retry after 10s on error
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(doFetch, 10_000);
      });
  }, [key, endpoint, ttl]);

  useEffect(() => {
    activeRef.current = true;
    doFetch();
    return () => {
      activeRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [doFetch]);

  return { data, loading, refetch: doFetch };
}
