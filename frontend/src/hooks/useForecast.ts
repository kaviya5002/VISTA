/**
 * useForecast — fetches component-level forecast data (day7/day15/day30)
 * from GET /component_twin/{vehicleId}/forecast
 *
 * Returns interpolated TwinData for any day 0–30 via `interpolate(day)`.
 */

import { useState, useEffect, useRef } from "react";
import api from "../services/api";
import type { TwinData, ComponentState } from "../components/DigitalTwin3D";

export interface ForecastPoint {
  health:              number;
  failure_probability: number;
  rul:                 number;
  confidence:          number;
}

export interface ComponentForecast {
  day7:  ForecastPoint;
  day15: ForecastPoint;
  day30: ForecastPoint;
}

export interface ForecastData {
  battery:      ComponentForecast;
  motor:        ComponentForecast;
  cooling:      ComponentForecast;
  brakes:       ComponentForecast;
  electrical:   ComponentForecast;
  transmission: ComponentForecast;
}

const COMP_KEYS = ["battery", "motor", "cooling", "brakes", "electrical", "transmission"] as const;

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function interpPoint(p0: ForecastPoint, p1: ForecastPoint, t: number): ForecastPoint {
  return {
    health:              Math.round(lerp(p0.health, p1.health, t)),
    failure_probability: lerp(p0.failure_probability, p1.failure_probability, t),
    rul:                 Math.round(lerp(p0.rul, p1.rul, t)),
    confidence:          Math.round(lerp(p0.confidence, p1.confidence, t)),
  };
}

/** Interpolate a ComponentForecast at any day 0–30 given the "today" baseline */
function interpComp(
  today: ComponentState,
  fc: ComponentForecast,
  day: number
): ForecastPoint {
  const d0: ForecastPoint = {
    health:              today.health,
    failure_probability: today.failure_probability,
    rul:                 today.rul,
    confidence:          today.confidence,
  };
  if (day <= 0)  return d0;
  if (day <= 7)  return interpPoint(d0, fc.day7,  day / 7);
  if (day <= 15) return interpPoint(fc.day7, fc.day15, (day - 7) / 8);
  return interpPoint(fc.day15, fc.day30, (day - 15) / 15);
}

/** Build a full TwinData snapshot for a given future day */
export function buildForecastSnapshot(
  today: TwinData,
  forecast: ForecastData,
  day: number
): TwinData {
  const comps: Partial<TwinData> = {};
  for (const key of COMP_KEYS) {
    const fp = interpComp(today[key], forecast[key], day);
    comps[key] = {
      ...today[key],
      health:              fp.health,
      failure_probability: fp.failure_probability,
      rul:                 fp.rul,
      confidence:          fp.confidence,
      status:              fp.health >= 75 ? "Healthy" : fp.health >= 45 ? "Warning" : "Critical",
    };
  }

  // Weighted vehicle health (same weights as backend)
  const W = { battery: 0.25, motor: 0.25, cooling: 0.20, brakes: 0.15, electrical: 0.10, transmission: 0.05 };
  const vh = Math.round(
    COMP_KEYS.reduce((s, k) => s + (comps[k]!.health * W[k]), 0)
  );
  const critical = COMP_KEYS
    .filter(k => comps[k]!.health < 45 || comps[k]!.failure_probability > 0.7)
    .map(k => k.charAt(0).toUpperCase() + k.slice(1));

  return {
    ...(comps as Pick<TwinData, typeof COMP_KEYS[number]>),
    vehicle_health:      vh,
    vehicle_status:      vh < 25 || critical.length > 0 ? "Critical" : vh < 60 ? "Warning" : "Healthy",
    critical_components: critical,
  };
}

export function useForecast(vehicleId: number) {
  const [forecast,  setForecast]  = useState<ForecastData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    setLoading(true);
    setForecast(null);
    api.get(`/component_twin/${vehicleId}/forecast`)
      .then(({ data }) => {
        if (!mountedRef.current) return;
        setForecast(data as ForecastData);
      })
      .catch(() => {/* keep null */})
      .finally(() => { if (mountedRef.current) setLoading(false); });
    return () => { mountedRef.current = false; };
  }, [vehicleId]);

  return { forecast, loading };
}
