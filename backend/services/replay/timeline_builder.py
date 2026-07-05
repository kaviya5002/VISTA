"""
Timeline Builder
================
Scans a sequence of history rows and detects significant events:
  - Temperature spikes
  - Health drops (sudden or sustained)
  - Failure probability surges
  - RUL crossing critical thresholds
  - Status transitions (Healthy → Warning → Critical)
  - Maintenance recommendation triggers

Returns a list of Event dicts and a human-readable summary, both
optimised for frontend timeline rendering.
"""
from __future__ import annotations

from datetime import datetime

# ── Thresholds ────────────────────────────────────────────────────────────────
_TEMP_SPIKE        = 15.0   # °C rise between consecutive frames
_TEMP_CRITICAL     = 90.0
_HEALTH_DROP_FRAME = 8.0    # % drop in one frame
_HEALTH_DROP_TOTAL = 20.0   # % drop over the whole window
_FAIL_SURGE        = 15.0   # pp rise between consecutive frames
_FAIL_CRITICAL     = 75.0
_RUL_THRESHOLDS    = [14, 7, 3]   # days — each crossing fires an event

_SEVERITY_COLOR = {
    "Info":     "#60A5FA",
    "Warning":  "#FBBF24",
    "Critical": "#EF4444",
    "Success":  "#34D399",
}

_SEVERITY_ICON = {
    "Info":     "ℹ️",
    "Warning":  "⚠️",
    "Critical": "🔴",
    "Success":  "✅",
}


def _ts_label(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M")
    except Exception:
        return iso


def _event(kind: str, severity: str, message: str, recorded_at: str, value: float | None = None) -> dict:
    return {
        "kind":        kind,
        "severity":    severity,
        "color":       _SEVERITY_COLOR.get(severity, "#94A3B8"),
        "icon":        _SEVERITY_ICON.get(severity, "⬤"),
        "message":     message,
        "recorded_at": recorded_at,
        "time_label":  _ts_label(recorded_at),
        "value":       value,
    }


def detect_events(rows: list[dict]) -> list[dict]:
    """
    Scan history rows (oldest → newest) and return a list of significant events.
    Each row must have at minimum: recorded_at, health_score, failure_prob,
    temperature, rul_days, status.
    """
    if not rows:
        return []

    events: list[dict] = []
    prev = rows[0]

    # Track which RUL thresholds have already fired to avoid duplicates
    fired_rul: set[int] = set()
    # Track last known status for transition detection
    last_status = prev.get("status", "Healthy")

    for row in rows[1:]:
        ts  = row.get("recorded_at", "")
        h   = row.get("health_score")   or 0.0
        fp  = row.get("failure_prob")   or 0.0
        tmp = row.get("temperature")    or 0.0
        rul = row.get("rul_days")       or 99.0
        st  = row.get("status", "Healthy")

        ph  = prev.get("health_score")  or 0.0
        pfp = prev.get("failure_prob")  or 0.0
        pt  = prev.get("temperature")   or 0.0

        # ── Temperature spike ─────────────────────────────────────────────
        if tmp - pt >= _TEMP_SPIKE:
            events.append(_event(
                "temp_spike", "Warning",
                f"Temperature spiked +{round(tmp - pt, 1)}°C to {round(tmp, 1)}°C",
                ts, tmp,
            ))
        if tmp >= _TEMP_CRITICAL and pt < _TEMP_CRITICAL:
            events.append(_event(
                "temp_critical", "Critical",
                f"Temperature crossed critical threshold: {round(tmp, 1)}°C",
                ts, tmp,
            ))

        # ── Health drop ───────────────────────────────────────────────────
        if ph - h >= _HEALTH_DROP_FRAME:
            events.append(_event(
                "health_drop", "Warning",
                f"Health dropped {round(ph - h, 1)}% in one interval (now {round(h, 1)}%)",
                ts, h,
            ))

        # ── Failure surge ─────────────────────────────────────────────────
        if fp - pfp >= _FAIL_SURGE:
            events.append(_event(
                "failure_surge", "Warning",
                f"Failure probability surged +{round(fp - pfp, 1)}pp to {round(fp, 1)}%",
                ts, fp,
            ))
        if fp >= _FAIL_CRITICAL and pfp < _FAIL_CRITICAL:
            events.append(_event(
                "failure_critical", "Critical",
                f"Failure probability exceeded {_FAIL_CRITICAL}%: now {round(fp, 1)}%",
                ts, fp,
            ))

        # ── RUL threshold crossings ───────────────────────────────────────
        for threshold in _RUL_THRESHOLDS:
            if rul <= threshold and threshold not in fired_rul:
                fired_rul.add(threshold)
                sev = "Critical" if threshold <= 3 else "Warning"
                events.append(_event(
                    "rul_threshold", sev,
                    f"Remaining useful life dropped to ≤{threshold} day(s): {round(rul, 1)} days",
                    ts, rul,
                ))

        # ── Status transition ─────────────────────────────────────────────
        if st != last_status:
            sev = "Critical" if st == "Critical" else "Warning" if st == "Warning" else "Success"
            events.append(_event(
                "status_change", sev,
                f"Vehicle status changed: {last_status} → {st}",
                ts,
            ))
            last_status = st

        prev = row

    # ── Whole-window health drop ──────────────────────────────────────────────
    first_h = rows[0].get("health_score") or 0.0
    last_h  = rows[-1].get("health_score") or 0.0
    if first_h - last_h >= _HEALTH_DROP_TOTAL:
        events.append(_event(
            "sustained_degradation", "Critical",
            f"Health degraded {round(first_h - last_h, 1)}% over the replay window "
            f"({round(first_h, 1)}% → {round(last_h, 1)}%)",
            rows[-1].get("recorded_at", ""),
            last_h,
        ))

    # Sort chronologically
    events.sort(key=lambda e: e["recorded_at"])
    return events


def build_summary(rows: list[dict], events: list[dict]) -> dict:
    """
    Produce a concise summary dict from the history rows and detected events.
    """
    if not rows:
        return {"message": "No history available for this window."}

    healths  = [r["health_score"]  for r in rows if r.get("health_score")  is not None]
    failures = [r["failure_prob"]  for r in rows if r.get("failure_prob")  is not None]
    temps    = [r["temperature"]   for r in rows if r.get("temperature")   is not None]

    critical_events = [e for e in events if e["severity"] == "Critical"]
    warning_events  = [e for e in events if e["severity"] == "Warning"]

    trend = "Stable"
    if healths:
        delta = healths[-1] - healths[0]
        if delta <= -_HEALTH_DROP_TOTAL:
            trend = "Rapidly Degrading"
        elif delta <= -5:
            trend = "Degrading"
        elif delta >= 5:
            trend = "Recovering"

    return {
        "frames":           len(rows),
        "time_start":       rows[0].get("recorded_at", ""),
        "time_end":         rows[-1].get("recorded_at", ""),
        "health_start":     round(healths[0],  1) if healths  else None,
        "health_end":       round(healths[-1], 1) if healths  else None,
        "health_min":       round(min(healths), 1) if healths else None,
        "health_avg":       round(sum(healths) / len(healths), 1) if healths else None,
        "failure_max":      round(max(failures), 1) if failures else None,
        "failure_avg":      round(sum(failures) / len(failures), 1) if failures else None,
        "temp_max":         round(max(temps), 1) if temps else None,
        "critical_events":  len(critical_events),
        "warning_events":   len(warning_events),
        "total_events":     len(events),
        "trend":            trend,
        "insight": _insight(trend, critical_events, rows[-1] if rows else {}),
    }


def _insight(trend: str, critical_events: list[dict], last_row: dict) -> str:
    if critical_events:
        return (
            f"{len(critical_events)} critical event(s) detected. "
            f"Latest: {critical_events[-1]['message']}."
        )
    if trend == "Rapidly Degrading":
        h = last_row.get("health_score", 0)
        return f"Vehicle health has degraded significantly — currently at {round(h, 1)}%."
    if trend == "Degrading":
        return "Gradual degradation detected. Schedule preventive maintenance."
    if trend == "Recovering":
        return "Vehicle condition is improving — continue monitoring."
    return "Vehicle operating within normal parameters over this window."
