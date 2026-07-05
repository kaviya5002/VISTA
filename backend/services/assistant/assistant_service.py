"""
Assistant Service
=================
Rule-based response engine with a pluggable LLM interface.

LLM integration
---------------
Set the environment variable  ASSISTANT_LLM=openai  (or any key) and provide
OPENAI_API_KEY / OPENAI_BASE_URL to route answers through an OpenAI-compatible
endpoint.  The frontend contract never changes — only the answer source does.
"""
from __future__ import annotations
import os

from services.assistant.intent_classifier  import classify, Intent
from services.assistant.context_builder    import build_context
from services.assistant.prompt_builder     import build_prompt_context, build_llm_messages
from services.assistant.response_formatter import format_response


# ── LLM backend (optional) ────────────────────────────────────────────────────
_LLM_BACKEND = os.getenv("ASSISTANT_LLM", "").lower()   # "openai" | "" (rule-based)


def _call_llm(messages: list[dict]) -> str | None:
    """
    Pluggable LLM call.  Returns the assistant reply string, or None on failure.
    Swap the body here to use any OpenAI-compatible provider (Azure, Bedrock, etc.)
    without touching the rest of the pipeline.
    """
    if _LLM_BACKEND != "openai":
        return None
    try:
        import openai  # type: ignore
        client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=400,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[assistant] LLM call failed: {e}")
        return None


# ── Rule-based answer generator ───────────────────────────────────────────────

def _rule_answer(intent: Intent, ctx: dict, context_text: str) -> str:
    if ctx.get("error"):
        return ctx["error"]

    cat = intent.category
    v   = ctx.get("vehicle")
    vid = intent.vehicle_id

    if cat == "greeting":
        return (
            "Hello! I'm TwinGuard AI. I can help you with fleet health, failure risks, "
            "maintenance scheduling, technician assignments, spare parts, and more. "
            "Try asking: 'What's the status of vehicle 5?' or 'Show me critical vehicles.'"
        )

    if cat == "fleet_summary":
        f = ctx.get("fleet", {})
        return (
            f"Fleet overview: {f.get('total', 0)} vehicles monitored. "
            f"{f.get('critical_count', 0)} are in critical condition. "
            f"Average fleet health is {f.get('avg_health', 0)}%."
        )

    if cat == "alerts":
        f = ctx.get("fleet", {})
        critical = f.get("top_critical", [])
        if not critical:
            return "No critical alerts at this time. All vehicles are within safe operating parameters."
        ids = ", ".join(f"#{v['vehicle_id']}" for v in critical)
        return f"{len(critical)} vehicle(s) require immediate attention: {ids}. Check the Alerts dashboard."

    if v is None and vid is not None:
        return f"Vehicle {vid} was not found in the fleet database."

    if v is None:
        return "Please specify a vehicle ID, e.g. 'What is the health of vehicle 12?'"

    if cat == "vehicle_health":
        return (
            f"Vehicle {vid} health score is {v.get('health_score')}% — status: {v.get('status')}. "
            f"Recommendation: {v.get('maintenance_recommendation', 'N/A')}."
        )

    if cat == "failure_risk":
        prob = v.get("failure_probability", 0)
        severity = "critically high" if prob > 75 else "elevated" if prob > 40 else "low"
        return (
            f"Vehicle {vid} has a {prob}% failure probability ({severity}). "
            f"Root cause: {', '.join(v.get('root_cause', [])) or 'None identified'}. "
            f"Next service: {v.get('next_service', 'N/A')}."
        )

    if cat == "rul":
        rul = v.get("remaining_useful_life_days", 0)
        urgency = (
            "Failure is imminent — service immediately." if rul <= 3 else
            "Service window is closing — act within the week." if rul <= 7 else
            "Schedule service within two weeks." if rul <= 14 else
            "Routine monitoring is sufficient."
        )
        return f"Vehicle {vid} has {rul} day(s) of useful life remaining. {urgency}"

    if cat == "root_cause":
        causes = v.get("root_cause", [])
        if not causes or causes == ["No Failure"]:
            return f"No root cause identified for vehicle {vid} — all systems nominal."
        return (
            f"Root cause analysis for vehicle {vid}: {', '.join(causes)}. "
            f"Source: {v.get('root_cause_source', 'Formula Engine')}."
        )

    if cat == "maintenance":
        return (
            f"Vehicle {vid} maintenance recommendation: {v.get('maintenance_recommendation', 'N/A')}. "
            f"Next service: {v.get('next_service', 'N/A')}. "
            f"Estimated repair cost: ₹{v.get('repair_now_cost', 0):,}."
        )

    if cat == "cost":
        return (
            f"Vehicle {vid} cost analysis — "
            f"Repair now: ₹{v.get('repair_now_cost', 0):,} | "
            f"Failure cost: ₹{v.get('failure_cost', 0):,} | "
            f"Potential savings: ₹{v.get('potential_savings', 0):,}."
        )

    if cat == "technician":
        a = ctx.get("assignment")
        if a:
            return (
                f"Recommended technician for vehicle {vid}: {a['technician']} "
                f"(score: {a['score']}, skills: {', '.join(a.get('technician_skills', [])[:2])}). "
                f"Estimated start: {a['estimated_start']}."
            )
        techs = ctx.get("technicians", [])
        avail = [t["name"] for t in techs if t["available"]][:3]
        return f"Available technicians: {', '.join(avail) or 'None currently available'}."

    if cat == "inventory":
        items = ctx.get("inventory", [])
        low = [i for i in items if i["current_stock"] <= i["min_stock"]]
        if not low:
            return "All spare parts inventory levels are healthy."
        names = ", ".join(i["name"] for i in low[:4])
        return f"{len(low)} part(s) are at or below minimum stock: {names}."

    if cat == "calendar":
        cal = ctx.get("calendar", {})
        s = cal.get("ai_summary", {})
        return (
            f"Maintenance calendar: {s.get('total_events', 0)} events scheduled. "
            f"{s.get('this_week_count', 0)} this week, {s.get('critical_count', 0)} critical. "
            f"Estimated savings: ₹{s.get('expected_savings', 0):,}."
        )

    if cat == "explanation":
        exp = ctx.get("explanation")
        if exp:
            return exp.get("summary", "") + " " + exp.get("recommendation", "")
        return f"Run the SHAP explanation for vehicle {vid} via GET /xai/shap/{vid}."

    # Fallback — return the raw context text
    return context_text or "I don't have enough information to answer that. Please try rephrasing."


# ── Public API ────────────────────────────────────────────────────────────────

def chat(message: str) -> dict:
    """
    Main entry point.  Accepts a user message string, returns a formatted
    response dict ready to be serialised as JSON.
    """
    intent       = classify(message)
    ctx          = build_context(intent)
    context_text = build_prompt_context(ctx)

    llm_used = False
    answer   = None

    if _LLM_BACKEND:
        messages = build_llm_messages(message, context_text)
        answer   = _call_llm(messages)
        llm_used = answer is not None

    if answer is None:
        answer = _rule_answer(intent, ctx, context_text)

    return format_response(answer, intent, ctx, llm_used=llm_used)
