import io
import uuid
import sys
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0D1B2A")
BLUE    = colors.HexColor("#1565C0")
LBLUE   = colors.HexColor("#1E88E5")
ACCENT  = colors.HexColor("#42A5F5")
LIGHT   = colors.HexColor("#E3F2FD")
WHITE   = colors.white
MUTED   = colors.HexColor("#78909C")
GREEN   = colors.HexColor("#2E7D32")
LGREEN  = colors.HexColor("#E8F5E9")
ORANGE  = colors.HexColor("#E65100")
LORANGE = colors.HexColor("#FFF3E0")
RED     = colors.HexColor("#C62828")
LRED    = colors.HexColor("#FFEBEE")
YELLOW  = colors.HexColor("#F57F17")
LYELLOW = colors.HexColor("#FFFDE7")
ROW_A   = colors.HexColor("#F5F9FF")
ROW_B   = WHITE

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 3.6 * cm   # left+right margins = 1.8 cm each

# ── Styles ────────────────────────────────────────────────────────────────────
def _s():
    return {
        "h1":      ParagraphStyle("h1",  fontSize=28, fontName="Helvetica-Bold",  textColor=WHITE,  spaceAfter=6, leading=34),
        "h2":      ParagraphStyle("h2",  fontSize=13, fontName="Helvetica-Bold",  textColor=WHITE,  spaceAfter=4),
        "h3":      ParagraphStyle("h3",  fontSize=11, fontName="Helvetica-Bold",  textColor=BLUE,   spaceAfter=6, spaceBefore=14),
        "cover":   ParagraphStyle("cov", fontSize=11, fontName="Helvetica",       textColor=ACCENT, spaceAfter=4),
        "body":    ParagraphStyle("bod", fontSize=9,  fontName="Helvetica",       textColor=NAVY,   spaceAfter=3, leading=14),
        "bold":    ParagraphStyle("bld", fontSize=9,  fontName="Helvetica-Bold",  textColor=NAVY),
        "small":   ParagraphStyle("sm",  fontSize=8,  fontName="Helvetica",       textColor=MUTED),
        "rec":     ParagraphStyle("rec", fontSize=9,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#1A237E"), leading=15),
        "card_v":  ParagraphStyle("cv",  fontSize=20, fontName="Helvetica-Bold",  textColor=NAVY,   alignment=1),
        "card_l":  ParagraphStyle("cl",  fontSize=8,  fontName="Helvetica-Bold",  textColor=MUTED,  alignment=1, spaceAfter=2),
        "footer":  ParagraphStyle("ft",  fontSize=7,  fontName="Helvetica",       textColor=MUTED,  alignment=1),
    }


# ── Footer callback ───────────────────────────────────────────────────────────
class _Footer:
    def __init__(self, report_id: str):
        self.report_id = report_id

    def __call__(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        y = 0.8 * cm
        canvas.drawString(1.8 * cm, y, "VISTA AI Platform  |  Generated Automatically")
        canvas.drawRightString(PAGE_W - 1.8 * cm, y, f"Page {doc.page}")
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(0.5)
        canvas.line(1.8 * cm, y + 0.35 * cm, PAGE_W - 1.8 * cm, y + 0.35 * cm)
        canvas.restoreState()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _section(title: str, s: dict):
    return [
        Spacer(1, 0.2 * cm),
        HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=4),
        Paragraph(title, s["h3"]),
    ]


def _std_table(data: list, col_widths: list, header_bg=BLUE) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [ROW_A, ROW_B]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#BBDEFB")),
        ("PADDING",       (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
    ]
    t.setStyle(TableStyle(style))
    return t


def _status_color(status: str):
    return {"Healthy": GREEN, "Warning": ORANGE, "Critical": RED}.get(status, MUTED)


def _status_bg(status: str):
    return {"Healthy": LGREEN, "Warning": LORANGE, "Critical": LRED}.get(status, colors.HexColor("#ECEFF1"))


def _pct_color(pct: float, invert=False) -> colors.Color:
    """Green=good, Red=bad. invert=True for failure % (high = bad)."""
    if invert:
        return RED if pct > 60 else (ORANGE if pct > 30 else GREEN)
    return GREEN if pct >= 70 else (ORANGE if pct >= 40 else RED)


# ── Cover Page ────────────────────────────────────────────────────────────────
def _cover(vehicle: dict, report_id: str, s: dict) -> list:
    elems = []

    # Full-width navy header block
    header = Table(
        [[Paragraph("VISTA", s["h1"]), Paragraph("AI PREDICTIVE MAINTENANCE REPORT", s["h2"])]],
        colWidths=[8 * cm, CONTENT_W - 8 * cm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("PADDING",    (0, 0), (-1, -1), 18),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",      (1, 0), (1, 0),   "RIGHT"),
    ]))
    elems.append(header)
    elems.append(Spacer(1, 1.2 * cm))

    # Cover meta card
    now = datetime.now()
    meta = [
        ["Vehicle ID",    str(vehicle["vehicle_id"])],
        ["VIN",           vehicle.get("vin", "N/A")],
        ["Make / Model",  f"{vehicle.get('make', '')} {vehicle.get('model', '')} {vehicle.get('year', '')}".strip() or "N/A"],
        ["Generated",     now.strftime("%d %B %Y  %H:%M:%S")],
        ["Report ID",     report_id],
        ["Data Source",   vehicle.get("data_source", "Workshop OBD-II")],
        ["Scanner",       vehicle.get("scanner", "N/A")],
        ["Collected",     vehicle.get("collected_at", "N/A")],
        ["Status",        vehicle.get("status", "N/A")],
    ]
    rows = []
    for label, value in meta:
        color = _status_color(value) if label == "Status" else NAVY
        rows.append([
            Paragraph(label, s["small"]),
            Paragraph(value, ParagraphStyle("mv", fontSize=11, fontName="Helvetica-Bold", textColor=color)),
        ])
    cover_t = Table(rows, colWidths=[5 * cm, CONTENT_W - 5 * cm])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, ACCENT),
        ("PADDING",       (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(cover_t)
    elems.append(PageBreak())
    return elems


# ── Executive Summary Cards ───────────────────────────────────────────────────
def _exec_summary(vehicle: dict, s: dict) -> list:
    elems = _section("Executive Summary", s)

    health   = vehicle.get("health_score", 0)
    fail_p   = vehicle.get("failure_probability", 0)
    rul      = vehicle.get("remaining_useful_life_days", 0)
    conf     = vehicle.get("confidence_score", 0)
    status   = vehicle.get("status", "N/A")

    def _card(label, value, bg, text_color=NAVY):
        inner = Table(
            [[Paragraph(str(value), ParagraphStyle("cv2", fontSize=18, fontName="Helvetica-Bold", textColor=text_color, alignment=1))],
             [Paragraph(label,      ParagraphStyle("cl2", fontSize=7,  fontName="Helvetica-Bold", textColor=MUTED, alignment=1))]],
            colWidths=[(CONTENT_W - 0.8 * cm) / 5],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("PADDING",    (0, 0), (-1, -1), 10),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("ROUNDEDCORNERS", [4]),
        ]))
        return inner

    card_w = (CONTENT_W - 0.4 * cm) / 5
    cards_data = [[
        _card("Health Score",        f"{health}%",   LGREEN,  _pct_color(health)),
        _card("Failure Probability", f"{fail_p}%",   LRED,    _pct_color(fail_p, invert=True)),
        _card("Remaining Useful Life", f"{rul}d",    LIGHT,   LBLUE),
        _card("AI Confidence",       f"{conf}%",     LYELLOW, YELLOW),
        _card("Overall Status",      status,         _status_bg(status), _status_color(status)),
    ]]
    row_t = Table(cards_data, colWidths=[card_w] * 5)
    row_t.setStyle(TableStyle([
        ("PADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",   (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(row_t)
    return elems


# ── Vehicle Information ───────────────────────────────────────────────────────
def _vehicle_info(vehicle: dict, s: dict) -> list:
    elems = _section("Vehicle Information", s)
    fields = [
        ("Vehicle ID",       vehicle.get("vehicle_id", "N/A")),
        ("Status",           vehicle.get("status", "N/A")),
        ("Priority",         vehicle.get("priority", "N/A")),
        ("Fleet Action",     vehicle.get("fleet_action", "N/A")),
        ("Priority Score",   vehicle.get("priority_score", "N/A")),
        ("Failure Risk",     vehicle.get("failure_risk", "N/A")),
    ]
    half = len(fields) // 2
    rows = []
    for i in range(half):
        l_label, l_val = fields[i]
        r_label, r_val = fields[i + half]
        rows.append([
            Paragraph(l_label, s["small"]), Paragraph(str(l_val), s["bold"]),
            Paragraph(r_label, s["small"]), Paragraph(str(r_val), s["bold"]),
        ])
    cw = CONTENT_W / 4
    t = Table(rows, colWidths=[cw] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, ACCENT),
        ("PADDING",       (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(t)
    return elems


# ── Component Health ──────────────────────────────────────────────────────────
def _compute_components(vehicle: dict) -> dict:
    """Run each component AI class and return per-component health/failure."""
    # Lazy import to avoid circular deps at module load time
    _be = os.path.dirname(os.path.dirname(__file__))
    if _be not in sys.path:
        sys.path.insert(0, _be)
    from services.component_ai.battery_ai      import BatteryAI
    from services.component_ai.motor_ai        import MotorAI
    from services.component_ai.cooling_ai      import CoolingAI
    from services.component_ai.brake_ai        import BrakeAI
    from services.component_ai.electrical_ai   import ElectricalAI
    from services.component_ai.transmission_ai import TransmissionAI

    v   = vehicle.get("battery_voltage", 12.0)
    t   = vehicle.get("temperature", 75.0)
    rpm = vehicle.get("rpm", 3000)
    spd = vehicle.get("speed", 60.0)

    return {
        "Battery":      BatteryAI(v, t, rpm).run(),
        "Motor":        MotorAI(rpm, t, v).run(),
        "Cooling":      CoolingAI(t, rpm, v).run(),
        "Brakes":       BrakeAI(spd, t, rpm, v).run(),
        "Electrical":   ElectricalAI(v, rpm, t).run(),
        "Transmission": TransmissionAI(rpm, spd, t, v).run(),
    }


def _component_health(vehicle: dict, s: dict) -> list:
    elems = _section("Component Health", s)

    comp_map = _compute_components(vehicle)

    def _row(name, comp):
        h  = round(comp.get("health", 0), 1)
        f  = round(comp.get("failure_probability", 0), 1)
        st = "Healthy" if h >= 70 else ("Warning" if h >= 40 else "Critical")
        sc = _status_color(st)
        return [
            Paragraph(name, s["bold"]),
            Paragraph(f"{h}%", ParagraphStyle("ch", fontSize=9, fontName="Helvetica-Bold", textColor=_pct_color(h), alignment=1)),
            Paragraph(f"{f}%", ParagraphStyle("cf", fontSize=9, fontName="Helvetica-Bold", textColor=_pct_color(f, invert=True), alignment=1)),
            Paragraph(st,      ParagraphStyle("cs", fontSize=9, fontName="Helvetica-Bold", textColor=sc, alignment=1)),
        ]

    header = [Paragraph(h, ParagraphStyle("th", fontSize=9, fontName="Helvetica-Bold", textColor=WHITE, alignment=1))
              for h in ["Component", "Health %", "Failure %", "Status"]]
    cw = [5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm]

    data = [header] + [_row(name, comp) for name, comp in comp_map.items()]
    t = _std_table(data, cw)
    elems.append(t)
    return elems


# ── Sensor Summary ────────────────────────────────────────────────────────────
def _sensor_summary(vehicle: dict, s: dict) -> list:
    elems = _section("Sensor Summary", s)

    sensors = [
        ("Voltage",     f"{vehicle.get('battery_voltage', 'N/A')} V",   vehicle.get("battery_voltage", 12), 10, 14),
        ("Temperature", f"{vehicle.get('temperature', 'N/A')} °C",      vehicle.get("temperature", 80),     0,  100),
        ("RPM",         str(vehicle.get("rpm", "N/A")),                  vehicle.get("rpm", 3000),           0,  6500),
        ("Speed",       f"{vehicle.get('speed', 'N/A')} km/h",          vehicle.get("speed", 60),           0,  120),
        ("Torque",      f"{vehicle.get('torque', 'N/A')} Nm",           vehicle.get("torque", 150),         0,  400),
    ]

    def _status_for(val, lo, hi):
        if val <= lo or val >= hi:
            return "Critical"
        margin = (hi - lo) * 0.15
        if val <= lo + margin or val >= hi - margin:
            return "Warning"
        return "Normal"

    header = [Paragraph(h, ParagraphStyle("th", fontSize=9, fontName="Helvetica-Bold", textColor=WHITE, alignment=1))
              for h in ["Sensor", "Reading", "Status"]]
    rows = [header]
    for name, reading, raw, lo, hi in sensors:
        st = _status_for(raw, lo, hi)
        sc = {"Normal": GREEN, "Warning": ORANGE, "Critical": RED}.get(st, MUTED)
        rows.append([
            Paragraph(name,    s["bold"]),
            Paragraph(reading, ParagraphStyle("sr", fontSize=9, fontName="Helvetica", textColor=NAVY, alignment=1)),
            Paragraph(st,      ParagraphStyle("ss", fontSize=9, fontName="Helvetica-Bold", textColor=sc, alignment=1)),
        ])
    cw = [5 * cm, 5 * cm, 5.5 * cm]
    elems.append(_std_table(rows, cw))
    return elems


# ── AI Prediction ─────────────────────────────────────────────────────────────
def _ai_prediction(vehicle: dict, s: dict) -> list:
    elems = _section("AI Prediction", s)

    root_causes = ", ".join(vehicle.get("root_cause", [])) or "None detected"
    rows = [
        ("Failure Probability",  f"{vehicle.get('failure_probability', 'N/A')}%"),
        ("Root Cause",           root_causes),
        ("Remaining Useful Life",f"{vehicle.get('remaining_useful_life_days', 'N/A')} days"),
        ("Maintenance Priority", vehicle.get("priority", "N/A")),
    ]
    data = [[Paragraph(k, s["small"]), Paragraph(str(v), s["bold"])] for k, v in rows]
    t = Table(data, colWidths=[6 * cm, CONTENT_W - 6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, ACCENT),
        ("PADDING",       (0, 0), (-1, -1), 9),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(t)
    return elems


# ── AI Recommendation ─────────────────────────────────────────────────────────
def _ai_recommendation(vehicle: dict, s: dict) -> list:
    elems = _section("AI Recommendation", s)

    rec  = vehicle.get("maintenance_recommendation", "No recommendation available.")
    action = vehicle.get("fleet_action", "")
    conf   = vehicle.get("confidence_score", "N/A")

    box_data = [[Paragraph(
        f"<b>Recommended Action:</b> {rec}<br/><br/>"
        f"<b>Fleet Action:</b> {action}<br/>"
        f"<b>AI Confidence:</b> {conf}%",
        s["rec"]
    )]]
    box = Table(box_data, colWidths=[CONTENT_W])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
        ("BOX",          (0, 0), (-1, -1), 2, BLUE),
        ("LINEAFTER",    (0, 0), (0, -1),  4, ACCENT),
    ]))
    elems.append(box)

    reasoning = vehicle.get("reasoning", [])
    if reasoning:
        elems.append(Spacer(1, 0.2 * cm))
        for r in reasoning:
            elems.append(Paragraph(f"• {r}", s["body"]))
    return elems


# ── Cost Analysis ─────────────────────────────────────────────────────────────
def _cost_analysis(vehicle: dict, s: dict) -> list:
    elems = _section("Cost Analysis", s)

    repair  = vehicle.get("repair_now_cost", 0)
    failure = vehicle.get("failure_cost", 0)
    savings = vehicle.get("potential_savings", 0)

    header = [Paragraph(h, ParagraphStyle("th", fontSize=9, fontName="Helvetica-Bold", textColor=WHITE, alignment=1))
              for h in ["Item", "Amount (₹)"]]
    rows = [
        header,
        [Paragraph("Estimated Repair Cost",   s["bold"]), Paragraph(f"₹{repair:,}",  ParagraphStyle("ca", fontSize=9, fontName="Helvetica", textColor=ORANGE, alignment=1))],
        [Paragraph("Estimated Failure Cost",  s["bold"]), Paragraph(f"₹{failure:,}", ParagraphStyle("ca", fontSize=9, fontName="Helvetica", textColor=RED,    alignment=1))],
        [Paragraph("Potential Savings",       s["bold"]), Paragraph(f"₹{savings:,}", ParagraphStyle("ca", fontSize=9, fontName="Helvetica-Bold", textColor=GREEN, alignment=1))],
    ]
    cw = [10 * cm, CONTENT_W - 10 * cm]
    elems.append(_std_table(rows, cw))
    return elems


# ── Main entry point ──────────────────────────────────────────────────────────
def generate_vehicle_report(vehicle: dict) -> bytes:
    buffer = io.BytesIO()
    report_id = f"RPT-{vehicle['vehicle_id']}-{uuid.uuid4().hex[:8].upper()}"
    footer_cb = _Footer(report_id)

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.6 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )

    s = _s()
    elems = []

    elems += _cover(vehicle, report_id, s)
    elems += _exec_summary(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _vehicle_info(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _component_health(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _sensor_summary(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _ai_prediction(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _ai_recommendation(vehicle, s)
    elems.append(Spacer(1, 0.4 * cm))
    elems += _cost_analysis(vehicle, s)

    doc.build(elems, onFirstPage=footer_cb, onLaterPages=footer_cb)
    return buffer.getvalue()
