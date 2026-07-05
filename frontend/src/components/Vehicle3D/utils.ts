/**
 * Shared utilities for Vehicle3D components.
 * healthToColor   — maps 0–100 health to a THREE hex color
 * healthToEmissive — dim glow for warning/critical
 */
export function healthToColor(health: number): string {
  if (health >= 75) return "#22c55e";   // green
  if (health >= 45) return "#f97316";   // orange
  if (health >= 25) return "#ef4444";   // red
  return "#7f1d1d";                      // dark red / critical
}

export function healthToEmissive(health: number): string {
  if (health >= 75) return "#000000";
  if (health >= 45) return "#7c2d00";
  return "#5c0a0a";
}

export type ComponentKey =
  | "battery" | "motor" | "cooling"
  | "brakes"  | "electrical" | "transmission";

export const COMPONENT_LABELS: Record<ComponentKey, string> = {
  battery:      "🔋 Battery",
  motor:        "⚙️ Motor",
  cooling:      "❄️ Cooling",
  brakes:       "🛑 Brakes",
  electrical:   "⚡ Electrical",
  transmission: "🔧 Transmission",
};
