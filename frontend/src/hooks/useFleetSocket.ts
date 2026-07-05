import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL        = "ws://127.0.0.1:8001/ws/fleet";
const RECONNECT_MS  = 1000;

export interface LiveVehicle {
  vehicle_id:          number;
  health:              number;
  failure_probability: number;
  temperature:         number;
  battery_voltage:     number;
  rpm:                 number;
  rul:                 number;
  status:              "Healthy" | "Warning" | "Critical";
}

// vehicle_id → LiveVehicle map — O(1) lookup
export type FleetMap = Map<number, LiveVehicle>;

export function useFleetSocket() {
  const [fleetMap,   setFleetMap]   = useState<FleetMap>(new Map());
  const [connected,  setConnected]  = useState(false);
  const wsRef    = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mapRef   = useRef<FleetMap>(new Map());

  const applySnapshot = useCallback((data: LiveVehicle[]) => {
    const m = new Map<number, LiveVehicle>();
    data.forEach(v => m.set(v.vehicle_id, v));
    mapRef.current = m;
    setFleetMap(new Map(m));
  }, []);

  const applyPatch = useCallback((data: LiveVehicle[]) => {
    // Only update changed vehicles — no full re-render of unchanged cards
    const m = new Map(mapRef.current);
    data.forEach(v => m.set(v.vehicle_id, v));
    mapRef.current = m;
    setFleetMap(new Map(m));
  }, []);

  useEffect(() => {
    let active = true;

    function connect() {
      if (!active) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen    = () => { if (active) setConnected(true); };
      ws.onclose   = () => {
        if (active) {
          setConnected(false);
          timerRef.current = setTimeout(connect, RECONNECT_MS);
        }
      };
      ws.onerror   = () => ws.close();
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if      (msg.type === "snapshot") applySnapshot(msg.data);
          else if (msg.type === "patch")    applyPatch(msg.data);
        } catch { /* ignore malformed */ }
      };
    }

    connect();
    return () => {
      active = false;
      clearTimeout(timerRef.current!);
      wsRef.current?.close();
    };
  }, [applySnapshot, applyPatch]);

  return { fleetMap, connected };
}
