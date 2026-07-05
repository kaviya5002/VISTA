/**
 * useTimelineState
 * ─────────────────────────────────────────────────────────────────────────────
 * Single source of truth for the AI Timeline Forecast feature.
 *
 * Responsibilities
 *   • Fetch forecast snapshots from GET /component_twin/{id}/forecast
 *   • Interpolate every TwinData field smoothly between day-0 → day-7 → day-15 → day-30
 *   • Drive play / pause / reset / drag-slider controls
 *   • Expose `displayData` — the interpolated TwinData that replaces live data
 *     when day > 0, so every downstream component (Hotspot, HUDOverlay,
 *     FloatingLabels, ComponentPopup, sidebar bars) updates automatically
 *
 * Interpolation strategy
 *   The backend returns three forecast snapshots: day7, day15, day30.
 *   We treat them as keyframes and linearly interpolate between them.
 *   Segment 0→7 : lerp(today, day7, t)
 *   Segment 7→15: lerp(day7,  day15, t)
 *   Segment 15→30: lerp(day15, day30, t)
 */

import { useState, useEffect, useRef, useCallback } from "react";
import api from "../services/api";
import type { TwinData, ComponentState } from "../DigitalTwin3D";

// ─── Types ────────────────────────────────────────────────────────────────────

/** One component's forecast at a single day snapshot */
interface ForecastSnapshot {
  health:              number;
  failure_probability: number;
  rul:                 number;
  confidence:          number;
}

/** Backend response shape for /component_twin/{id}/forecast */
interface ComponentForecast {
  day7:  ForecastSnapshot;
  day15: ForecastSnapshot;
  day30: ForecastSnapshot;
}

interface ForecastData {
  battery:      ComponentForecast;
  motor:        ComponentForecast;
  cooling:      ComponentForecast;
  brakes:       ComponentForecast;
  electrical:   ComponentForecast;
  transmission: ComponentForecast;
}

export interface TimelineState {
  /** Current slider day (0 = live, 1–30 = forecast) */
  day:          number;
  /** Is the timeline auto-playing forward */
  playing:      boolean;
  /** Forecast data loaded from backend */
  forecastData: ForecastData | null;
  /** Loading state for forecast fetch */
  forecastLoading: boolean;
  /** The interpolated TwinData at `day` — null when day === 0 */
  displayData:  TwinData | null;
  /** Controls */
  setDay:       (day: number) => void;
  play:         () => void;
  pause:        () => void;
  reset:        () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function interpolateSensors(
  liveSensors: Record<string, number | string> | undefined,
  healthNow: number,
  healthFuture: number,
  t: number,
): Record<string, number | string> {
  if (!liveSensors) return {};
  const out: Record<string, number | string> = {};
  for (const [key, val] of Object.entries(liveSensors)) {
    const n = Number(val);
    if (isNaN(n)) { out[key] = val; continue; }
    // Voltage degrades proportionally with health loss
    if (key === "voltage") {
      const degraded = n * (1 - (healthNow - healthFuture) / 100 * t * 0.12);
      out[key] = parseFloat(degraded.toFixed(2));
    // Temperature rises as cooling/motor health drops
    } else if (key === "temperature") {
      const rise = (healthNow - healthFuture) / 100 * t * 35;
      out[key] = parseFloat((n + rise).toFixed(1));
    // RPM drifts down slightly with motor health
    } else if (key === "rpm") {
      const drop = (healthNow - healthFuture) / 100 * t * 400;
      out[key] = Math.round(n - drop);
    } else {
      out[key] = val;
    }
  }
  return out;
}

function lerpComponent(
  a: ComponentState,
  b: ForecastSnapshot,
  t: number,
): ComponentState {
  const healthFuture = Math.round(lerp(a.health, b.health, t));
  return {
    health:              healthFuture,
    failure_probability: parseFloat(lerp(a.failure_probability, b.failure_probability, t).toFixed(3)),
    rul:                 Math.round(lerp(a.rul,                 b.rul,                 t)),
    confidence:          Math.round(lerp(a.confidence,          b.confidence,          t)),
    status:              deriveStatus(healthFuture),
    sensors:             interpolateSensors(a.sensors, a.health, b.health, t),
  };
}

function lerpBetweenSnapshots(
  a: ForecastSnapshot,
  b: ForecastSnapshot,
  t: number,
): ForecastSnapshot {
  return {
    health:              Math.round(lerp(a.health,              b.health,              t)),
    failure_probability: parseFloat(lerp(a.failure_probability, b.failure_probability, t).toFixed(3)),
    rul:                 Math.round(lerp(a.rul,                 b.rul,                 t)),
    confidence:          Math.round(lerp(a.confidence,          b.confidence,          t)),
  };
}

function deriveStatus(health: number): string {
  if (health >= 75) return "Healthy";
  if (health >= 45) return "Warning";
  return "Critical";
}

function deriveVehicleHealth(components: Record<string, ComponentState>): number {
  const weights: Record<string, number> = {
    battery: 0.25, motor: 0.25, cooling: 0.20,
    brakes: 0.15, electrical: 0.10, transmission: 0.05,
  };
  return Math.round(
    Object.entries(weights).reduce(
      (sum, [key, w]) => sum + (components[key]?.health ?? 100) * w,
      0,
    ),
  );
}

function deriveCritical(components: Record<string, ComponentState>): string[] {
  const nameMap: Record<string, string> = {
    battery: "Battery", motor: "Motor", cooling: "Cooling",
    brakes: "Brakes", electrical: "Electrical", transmission: "Transmission",
  };
  return Object.entries(components)
    .filter(([, c]) => c.health < 45 || c.failure_probability > 0.70)
    .map(([k]) => nameMap[k] ?? k);
}

/**
 * Given a day (0–30), the live TwinData, and the forecast keyframes,
 * return the fully interpolated TwinData.
 */
function interpolateTwinData(
  day: number,
  live: TwinData,
  forecast: ForecastData,
): TwinData {
  const COMP_KEYS = ["battery", "motor", "cooling", "brakes", "electrical", "transmission"] as const;

  const interpolated: Record<string, ComponentState> = {};

  for (const key of COMP_KEYS) {
    const liveComp = live[key];
    const fc       = forecast[key];

    let snap: ComponentState;

    if (day <= 7) {
      const t = day / 7;
      snap = lerpComponent(liveComp, fc.day7, t);
    } else if (day <= 15) {
      const t = (day - 7) / 8;
      const a = lerpBetweenSnapshots(fc.day7, fc.day15, t);
      snap = {
        health:              a.health,
        failure_probability: a.failure_probability,
        rul:                 a.rul,
        confidence:          a.confidence,
        status:              deriveStatus(a.health),
        sensors:             interpolateSensors(liveComp.sensors, fc.day7.health, fc.day15.health, t),
      };
    } else {
      const t = (day - 15) / 15;
      const a = lerpBetweenSnapshots(fc.day15, fc.day30, t);
      snap = {
        health:              a.health,
        failure_probability: a.failure_probability,
        rul:                 a.rul,
        confidence:          a.confidence,
        status:              deriveStatus(a.health),
        sensors:             interpolateSensors(liveComp.sensors, fc.day15.health, fc.day30.health, t),
      };
    }

    interpolated[key] = snap;
  }

  const vehicleHealth = deriveVehicleHealth(interpolated);
  const critical      = deriveCritical(interpolated);

  return {
    vehicle_health:      vehicleHealth,
    vehicle_status:      deriveStatus(vehicleHealth),
    critical_components: critical,
    battery:      interpolated.battery,
    motor:        interpolated.motor,
    cooling:      interpolated.cooling,
    brakes:       interpolated.brakes,
    electrical:   interpolated.electrical,
    transmission: interpolated.transmission,
  };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

const PLAY_INTERVAL_MS = 600; // advance 1 day every 600ms during playback

export function useTimelineState(
  vehicleId: number,
  liveTwinData: TwinData | null,
): TimelineState {
  const [day,             setDayRaw]       = useState(0);
  const [playing,         setPlaying]      = useState(false);
  const [forecastData,    setForecastData] = useState<ForecastData | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  const playRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // ── Fetch forecast when vehicleId changes ──────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    setForecastData(null);
    setForecastLoading(true);

    api.get(`/component_twin/${vehicleId}/forecast`)
      .then(({ data }) => {
        if (!mountedRef.current) return;
        setForecastData(data as ForecastData);
      })
      .catch(() => {
        // Forecast unavailable — timeline will stay at day 0
      })
      .finally(() => {
        if (mountedRef.current) setForecastLoading(false);
      });

    return () => { mountedRef.current = false; };
  }, [vehicleId]);

  // ── Playback ticker ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!playing) {
      if (playRef.current) clearInterval(playRef.current);
      return;
    }
    playRef.current = setInterval(() => {
      setDayRaw(prev => {
        if (prev >= 30) {
          setPlaying(false);
          return 30;
        }
        return prev + 1;
      });
    }, PLAY_INTERVAL_MS);

    return () => { if (playRef.current) clearInterval(playRef.current); };
  }, [playing]);

  // ── Controls ───────────────────────────────────────────────────────────────
  const setDay = useCallback((d: number) => {
    setDayRaw(Math.max(0, Math.min(30, d)));
  }, []);

  const play  = useCallback(() => { if (day >= 30) setDayRaw(0); setPlaying(true);  }, [day]);
  const pause = useCallback(() => setPlaying(false), []);
  const reset = useCallback(() => { setPlaying(false); setDayRaw(0); }, []);

  // ── Interpolated display data ──────────────────────────────────────────────
  const displayData: TwinData | null =
    day === 0 || !liveTwinData || !forecastData
      ? null
      : interpolateTwinData(day, liveTwinData, forecastData);

  return {
    day,
    playing,
    forecastData,
    forecastLoading,
    displayData,
    setDay,
    play,
    pause,
    reset,
  };
}
