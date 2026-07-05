/**
 * useTwinState
 *
 * Polls /twin/state, /twin/events, /twin/history for a single vehicle.
 * Refreshes every `interval` ms (default 2 s) so the detail page "breathes."
 */
import { useEffect, useRef, useState } from "react";
import api from "../services/api";

export interface TwinSummary {
  samples:   number;
  min:       number;
  max:       number;
  avg:       number;
  latest:    number;
  slope:     number;
  direction: "Improving" | "Degrading" | "Stable";
}

export interface TwinStateData {
  vehicle_id: number;
  current:    Record<string, any>;
  previous:   Record<string, any> | null;
  summary:    TwinSummary;
  lifecycle:  string;
}

export interface TwinEvent {
  ts:       number;
  kind:     string;
  message:  string;
  severity: "Info" | "Warning" | "Critical";
}

export interface HealthPoint {
  ts:     number;
  health: number;
  status: string;
}

export function useTwinState(vehicleId: number | string, interval = 2000) {
  const [state,   setState]   = useState<TwinStateData | null>(null);
  const [events,  setEvents]  = useState<TwinEvent[]>([]);
  const [history, setHistory] = useState<HealthPoint[]>([]);
  const [ready,   setReady]   = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refresh() {
    try {
      const [stateRes, eventsRes, histRes] = await Promise.all([
        api.get(`/twin/state/${vehicleId}`),
        api.get(`/twin/events/${vehicleId}`),
        api.get(`/twin/history/${vehicleId}`),
      ]);
      setState(stateRes.data);
      setEvents(eventsRes.data.events ?? []);
      setHistory(histRes.data.health_series ?? []);
      setReady(true);
    } catch {
      // Not yet populated — wait for WS to seed it
    }
  }

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, interval);
    return () => { if (timer.current) clearInterval(timer.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleId, interval]);

  return { state, events, history, ready };
}
