import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

try:
    import qrcode
    from reportlab.platypus import Image as RLImage
    QR_ENABLED = True
except ImportError:
    QR_ENABLED = False

# ── Colour palette ────────────────────────────────────────────────────────────
DARK   = colors.HexColor("#0F172A")
ACCENT = colors.HexColor("#38BDF8")
GREEN  = colors.HexColor("#34D399")
YELLOW = colors.HexColor("#FBBF24")
RED    = colors.HexColor("#EF4444")
ORANGE = colors.HexColor("#F97316")
LIGHT  = colors.HexColor("#F1F5F9")
MUTED  = colors.HexColor("#64748B")
WHITE  = colors.white

PRIORITY_COLORS = {
    "Critical": RED,
    "High":     ORANGE,
    "Medium":   YELLOW,
    "Routine":  GREEN,
}

# ── Styles ────────────────────────────────────────────────────────────────────
def _styles():
    return {
        "title":   ParagraphStyle("title",   fontSize=22, fontName="Helvetica-Bold",  textColor=LIGHT,  spaceAfter=4),
        "sub":     ParagraphStyle("sub",     fontSize=10, fontName="Helvetica",       textColor=MUTED,  spaceAfter=2),
        "section": ParagraphStyle("section", fontSize=12, fontName="Helvetica-Bold",  textColor=ACCENT, spaceAfter=6, spaceBefore=12),
        "body":    ParagraphStyle("body",    fontSize=9,  fontName="Helvetica",       textColor=LIGHT,  spaceAfter=3, leading=14),
        "check":   ParagraphStyle("check",   fontSize=9,  fontName="Helvetica",       textColor=LIGHT,  spaceAfter=2, leftIndent=8),
        "bold":    ParagraphStyle("bold",    fontSize=9,  fontName="Helvetica-Bold",  textColor=LIGHT),
        "small":   ParagraphStyle("small",   fontSize=8,  fontName="Helvetica",       textColor=MUTED),
        "ai":      ParagraphStyle("ai",      fontSize=9,  fontName="Helvetica-Oblique", textColor=colors.HexColor("#CBD5E1"), leading=15),
    }


def _kv_table(rows: list[tuple], col_w=(5*cm, 10*cm)) -> Table:
    data = [[Paragraph(k, _styles()["small"]), Paragraph(str(v), _styles()["bold"])] for k, v in rows]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#0F172A"), colors.HexColor("#111827")]),
        ("GRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#1E293B")),
        ("PADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _list_table(items: list[str], tick="✓") -> Table:
    data = [[Paragraph(f"{tick}  {item}", _styles()["check"])] for item in items]
    t = Table(data, colWidths=[15*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#0F172A"), colors.HexColor("#111827")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#1E293B")),
        ("PADDING",       (0, 0), (-1, -1), 5),
    ]))
    return t


def _two_col_list(items: list[str]) -> Table:
    mid = (len(items) + 1) // 2
    left, right = items[:mid], items[mid:]
    rows = []
    for i in range(mid):
        l = Paragraph(f"✓  {left[i]}", _styles()["check"]) if i < len(left) else Paragraph("", _styles()["check"])
        r = Paragraph(f"✓  {right[i]}", _styles()["check"]) if i < len(right) else Paragraph("", _styles()["check"])
        rows.append([l, r])
    t = Table(rows, colWidths=[7.5*cm, 7.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#0F172A"), colors.HexColor("#111827")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#1E293B")),
        ("PADDING",       (0, 0), (-1, -1), 5),
    ]))
    return t


def _qr_image(data: str, size: float = 3*cm):
    if not QR_ENABLED:
        return None
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=size, height=size)


def generate_work_order_pdf(wo: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
    )
    s = _styles()
    pc = PRIORITY_COLORS.get(wo["priority"], YELLOW)
    elems = []

    # ── Header bar ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("TwinGuard AI", ParagraphStyle("hdr", fontSize=18, fontName="Helvetica-Bold", textColor=ACCENT)),
        Paragraph("MAINTENANCE WORK ORDER", ParagraphStyle("hdr2", fontSize=11, fontName="Helvetica-Bold", textColor=LIGHT, alignment=2)),
    ]]
    ht = Table(header_data, colWidths=[9*cm, 8*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("PADDING",    (0, 0), (-1, -1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(ht)
    elems.append(HRFlowable(width="100%", thickness=2, color=pc, spaceAfter=8))

    # ── Work order meta ───────────────────────────────────────────────────────
    priority_cell = Paragraph(
        wo["priority"],
        ParagraphStyle("pri", fontSize=13, fontName="Helvetica-Bold", textColor=pc)
    )
    meta_data = [[
        _kv_table([
            ("Work Order ID", wo["work_order_id"]),
            ("Generated",     wo["generated_at"][:16].replace("T", "  ")),
            ("Scheduled",     wo["scheduled_date"]),
        ], col_w=(4*cm, 6*cm)),
        _kv_table([
            ("Vehicle ID",    str(wo["vehicle_id"])),
            ("Model",         wo["vehicle_model"]),
            ("Priority",      wo["priority"]),
        ], col_w=(4*cm, 3*cm)),
    ]]
    mt = Table(meta_data, colWidths=[10.5*cm, 7*cm])
    mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 0)]))
    elems.append(mt)
    elems.append(Spacer(1, 0.3*cm))

    # ── Diagnostics ───────────────────────────────────────────────────────────
    elems.append(Paragraph("Diagnostics", s["section"]))
    diag_rows = [
        ("Health Score",     f"{wo['health_score']}%"),
        ("Failure Risk",     f"{wo['failure_risk']}%"),
        ("Remaining Life",   f"{wo['rul_days']} days"),
        ("Risk Level",       wo["estimated_risk"]),
        ("AI Confidence",    f"{wo['confidence_score']}%"),
        ("Root Causes",      ", ".join(wo["root_causes"]) or "None detected"),
    ]
    elems.append(_kv_table(diag_rows, col_w=(5*cm, 10*cm)))
    elems.append(Spacer(1, 0.2*cm))

    # ── Repair details ────────────────────────────────────────────────────────
    elems.append(Paragraph("Repair Details", s["section"]))
    repair_rows = [
        ("Task",             wo["task"]),
        ("Duration",         wo["duration"]),
        ("Technician",       wo["technician"]),
        ("Skill Required",   wo["technician_skill"]),
        ("Estimated Cost",   f"₹{wo['estimated_cost']:,}"),
        ("Failure Cost",     f"₹{wo['failure_cost']:,}"),
        ("Potential Savings",f"₹{wo['potential_savings']:,}"),
    ]
    elems.append(_kv_table(repair_rows, col_w=(5*cm, 10*cm)))
    elems.append(Spacer(1, 0.2*cm))

    # ── Parts + Tools side by side ────────────────────────────────────────────
    elems.append(Paragraph("Required Parts & Tools", s["section"]))
    parts_col = [Paragraph("Parts Required", s["bold"])] + [
        Paragraph(f"✓  {p}", s["check"]) for p in wo["parts"]
    ]
    tools_col = [Paragraph("Tools Required", s["bold"])] + [
        Paragraph(f"🔧  {t}", s["check"]) for t in wo["tools"]
    ]
    max_rows = max(len(parts_col), len(tools_col))
    parts_col += [Paragraph("", s["check"])] * (max_rows - len(parts_col))
    tools_col += [Paragraph("", s["check"])] * (max_rows - len(tools_col))
    pt_data = [[p, t] for p, t in zip(parts_col, tools_col)]
    pt = Table(pt_data, colWidths=[8.5*cm, 8.5*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#0F172A"), colors.HexColor("#111827")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#1E293B")),
        ("PADDING",       (0, 0), (-1, -1), 5),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elems.append(pt)
    elems.append(Spacer(1, 0.2*cm))

    # ── Checklist ─────────────────────────────────────────────────────────────
    elems.append(Paragraph("Repair Checklist", s["section"]))
    elems.append(_two_col_list(wo["checklist"]))
    elems.append(Spacer(1, 0.2*cm))

    # ── Technician instructions ───────────────────────────────────────────────
    elems.append(Paragraph("Technician Instructions", s["section"]))
    instr = wo.get("instructions", {})
    for phase, label in [("before", "Before Repair"), ("during", "During Repair"), ("after", "After Repair")]:
        steps = instr.get(phase, [])
        if steps:
            elems.append(Paragraph(label, s["bold"]))
            elems.append(_list_table(steps, tick="→"))
            elems.append(Spacer(1, 0.15*cm))

    # ── AI Summary ────────────────────────────────────────────────────────────
    elems.append(Paragraph("AI Analysis Summary", s["section"]))
    elems.append(Paragraph(wo["ai_summary"], s["ai"]))
    if wo.get("reasoning"):
        elems.append(Spacer(1, 0.15*cm))
        for r in wo["reasoning"][:3]:
            elems.append(Paragraph(f"• {r}", s["ai"]))
    elems.append(Spacer(1, 0.3*cm))

    # ── QR + Signature ────────────────────────────────────────────────────────
    qr_img = _qr_image(wo["qr_data"])
    sig_block = [
        [Paragraph("Technician Signature", s["small"]), Paragraph("Supervisor Approval", s["small"]), Paragraph("Date Completed", s["small"])],
        [Paragraph("\n\n_______________________", s["body"]), Paragraph("\n\n_______________________", s["body"]), Paragraph("\n\n_______________________", s["body"])],
    ]
    sig_t = Table(sig_block, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    sig_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("PADDING",    (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#1E293B")),
    ]))

    if qr_img:
        bottom_data = [[qr_img, sig_t]]
        bt = Table(bottom_data, colWidths=[3.5*cm, 14*cm])
        bt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 0)]))
        elems.append(bt)
    else:
        elems.append(sig_t)

    # ── Footer ────────────────────────────────────────────────────────────────
    elems.append(HRFlowable(width="100%", thickness=0.5, color=MUTED, spaceBefore=8))
    elems.append(Paragraph(
        f"TwinGuard AI — Predictive Maintenance Platform  |  {wo['work_order_id']}  |  Generated {wo['generated_at'][:10]}",
        ParagraphStyle("footer", fontSize=7, fontName="Helvetica", textColor=MUTED, alignment=1)
    ))

    doc.build(elems)
    return buffer.getvalue()
