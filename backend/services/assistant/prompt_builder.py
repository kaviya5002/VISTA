"""
Prompt Builder
==============
Converts a structured context dict into a compact, readable text block.
Used both as the rule-based answer source and as the LLM system prompt context.
"""
from __future__ import annotations


def _vehicle_block(v: dict) -> str:
    if not v:
        return ""
    lines = [
        f"Vehicle {v['vehicle_id']} | Status: {v.get('status', 'Unknown')}",
        f"  Health: {v.get('health_score')}%  |  Failure Risk: {v.get('failure_probability')}%",
        f"  RUL: {v.get('remaining_useful_life_days')} days  |  Priority: {v.get('priority', 'N/A')}",
        f"  Root Cause: {', '.join(v.get('root_cause', [])) or 'None'}",
        f"  Repair Cost: ₹{v.get('repair_now_cost', 0):,}  |  Failure Cost: ₹{v.get('failure_cost', 0):,}",
        f"  Recommendation: {v.get('maintenance_recommendation', 'N/A')}",
        f"  Next Service: {v.get('next_service', 'N/A')}",
    ]
    return "\n".join(lines)


def _fleet_block(f: dict) -> str:
    lines = [
        f"Fleet: {f['total']} vehicles  |  Critical: {f['critical_count']}  |  Avg Health: {f['avg_health']}%",
    ]
    for v in f.get("top_critical", []):
        lines.append(
            f"  ⚠ Vehicle {v['vehicle_id']}: health={v['health_score']}%, "
            f"failure={v['failure_probability']}%, status={v['status']}"
        )
    return "\n".join(lines)


def _technician_block(techs: list[dict]) -> str:
    available = [t for t in techs if t["available"]]
    lines = [f"Technicians: {len(techs)} total, {len(available)} available"]
    for t in available[:4]:
        lines.append(f"  {t['name']} | Skills: {', '.join(t['skills'][:2])} | Rating: {t['rating']}★")
    return "\n".join(lines)


def _inventory_block(items: list[dict]) -> str:
    critical = [i for i in items if i["current_stock"] <= i["min_stock"]]
    lines = [f"Inventory: {len(items)} parts  |  Low/Critical: {len(critical)}"]
    for i in critical[:4]:
        lines.append(f"  ⚠ {i['name']}: stock={i['current_stock']}, min={i['min_stock']}")
    return "\n".join(lines)


def _calendar_block(cal: dict) -> str:
    events = cal.get("events", [])
    summary = cal.get("ai_summary", {})
    lines = [
        f"Calendar: {summary.get('total_events', 0)} events  |  "
        f"This week: {summary.get('this_week_count', 0)}  |  "
        f"Critical: {summary.get('critical_count', 0)}"
    ]
    for e in events[:3]:
        lines.append(f"  {e['date']} {e['time']} — Vehicle {e['vehicle_id']}: {e['task']} [{e['priority']}]")
    return "\n".join(lines)


def _explanation_block(exp: dict) -> str:
    lines = [exp.get("summary", "")]
    for s in exp.get("factors_text", [])[:3]:
        lines.append(f"  • {s}")
    lines.append(exp.get("recommendation", ""))
    return "\n".join(lines)


def build_prompt_context(ctx: dict) -> str:
    parts: list[str] = []

    if ctx.get("error"):
        return f"Error: {ctx['error']}"

    if ctx.get("fleet"):
        parts.append(_fleet_block(ctx["fleet"]))

    if ctx.get("vehicle"):
        parts.append(_vehicle_block(ctx["vehicle"]))

    if ctx.get("technicians"):
        parts.append(_technician_block(ctx["technicians"]))

    if ctx.get("assignment"):
        a = ctx["assignment"]
        parts.append(
            f"Assigned: {a['technician']} (score {a['score']}) | "
            f"Start: {a['estimated_start']} | Task: {a['task']}"
        )

    if ctx.get("inventory"):
        parts.append(_inventory_block(ctx["inventory"]))

    if ctx.get("calendar"):
        parts.append(_calendar_block(ctx["calendar"]))

    if ctx.get("explanation"):
        parts.append(_explanation_block(ctx["explanation"]))

    return "\n\n".join(parts) if parts else "No relevant data found."


SYSTEM_PROMPT = """\
You are TwinGuard AI, an intelligent fleet maintenance assistant.
You have access to real-time vehicle telemetry, ML predictions, and maintenance data.
Answer concisely and factually. Always cite vehicle IDs and numeric values when available.
If a vehicle is critical, lead with the urgency.
"""


def build_llm_messages(user_message: str, context_text: str) -> list[dict]:
    """Format messages for an OpenAI-compatible chat API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nCurrent Data:\n" + context_text},
        {"role": "user",   "content": user_message},
    ]
