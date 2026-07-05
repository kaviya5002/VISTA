/**
 * useLiveTwin — centralized hook for live AI Digital Twin data.
 *
 * Polls  GET /digital_twin/component/{vehicleId}  every POLL_MS milliseconds.
 * All hotspots, labels, popups, and animations consume this single state.
 *
 * Returns:
 *   twinData    — normalized TwinData (null while loading)
 *   loading     — true only on the very first fetch
 *   isStale     — true if the last fetch failed (showing cached data)
 *   lastUpdated — Date of the last successful fetch
 *   error       — last error message, or null
 */

import { useState, useEffect, useRef, useCallback } from "react";
import api from "../services/api";
import type { TwinData, ComponentState } from "../components/DigitalTwin3D";

const POLL_MS = 4000;

// ─── Response normalizer ──────────────────────────────────────────────────────

function normalizeComponent(c: any): ComponentState {
  return {
    health:              Number(c?.health              ?? 100),
    failure_probability: Number(c?.failure_probability ?? 0),
    rul:                 Number(c?.rul                 ?? 365),
    confidence:          Number(c?.confidence          ?? 100),
    status:              String(c?.status              ?? "Healthy"),
    sensors:             (c?.sensors && typeof c.sensors === "object") ? c.sensors : {},
  };
}

function normalizeResponse(raw: any): TwinData {
  return {
    vehicle_health:      Number(raw.vehicle_health      ?? 100),
    vehicle_status:      String(raw.vehicle_status      ?? "Healthy"),
    critical_components: Array.isArray(raw.critical_components) ? raw.critical_components : [],
    battery:      normalizeComponent(raw.battery),
    motor:        normalizeComponent(raw.motor),
    cooling:      normalizeComponent(raw.cooling),
    brakes:       normalizeComponent(raw.brakes),
    electrical:   normalizeComponent(raw.electrical),
    transmission: normalizeComponent(raw.transmission),
  };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface LiveTwinState {
  twinData:    TwinData | null;
  loading:     boolean;
  isStale:     boolean;
  lastUpdated: Date | null;
  error:       string | null;
}

export function useLiveTwin(vehicleId: number): LiveTwinState {
  const [twinData,    setTwinData]    = useState<TwinData | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [isStale,     setIsStale]     = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error,       setError]       = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef  = useRef(true);

  const fetch = useCallback(async (isInitial: boolean) => {
    try {
      const { data } = await api.get(`/digital_twin/component/${vehicleId}`);
      if (!mountedRef.current) return;
      setTwinData(normalizeResponse(data));
      setLastUpdated(new Date());
      setIsStale(false);
      setError(null);
    } catch (err: any) {
      if (!mountedRef.current) return;
      const msg = err?.response?.data?.detail ?? err?.message ?? "Network error";
      setError(msg);
      setIsStale(true);          // keep showing last good data
    } finally {
      if (mountedRef.current && isInitial) setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => {
    mountedRef.current = true;
    setLoading(true);
    setTwinData(null);
    setIsStale(false);
    setError(null);

    fetch(true);

    intervalRef.current = setInterval(() => fetch(false), POLL_MS);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetch]);

  return { twinData, loading, isStale, lastUpdated, error };
}
