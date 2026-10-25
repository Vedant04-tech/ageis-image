"""Report generation for JSON and PDF export formats.

Per architecture.md and rules.md:
- Both JSON and PDF reports are constructed directly from the same AnalysisReport object.
- Original SHA-256 digest appears unchanged across all views and exports.
- Exact GPS coordinates are omitted from default exports.
- Derived artifacts (ELA visualization, histograms) are clearly identified as derived, not original evidence.
- Full educational and non-conclusive disclaimers are prominently displayed.
"""

from datetime import datetime, timezone
import io
import json
from pathlib import PurePath
import re
from typing import Any, Optional
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import html
from src.models import AnalysisReport, MethodStatus


def _safe_escape(text: Any) -> str:
    """Escape text for safe inclusion inside ReportLab Paragraphs."""
    if text is None:
        return ""
    return html.escape(str(text), quote=False)


def export_json(report: AnalysisReport) -> str:
    """Serialize AnalysisReport into schema-versioned formatted JSON string.

    Args:
        report: Populated AnalysisReport object.

    Returns:
        JSON string formatted with 2-space indentation.
    """
    data = report.to_dict()
    return json.dumps(data, indent=2)


def generate_export_filename(
    original_filename_display: str,
    extension: str,
    timestamp_utc: Optional[str] = None,
) -> str:
    """Generate safe, sanitized export filename.

    Args:
        original_filename_display: Sanitized display name of uploaded image.
        extension: Export extension (e.g. 'json' or 'pdf').
        timestamp_utc: Optional UTC timestamp string.

    Returns:
        Clean filesystem-safe filename string.
    """
    clean_stem = PurePath(original_filename_display).stem
    clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", clean_stem)[:40].strip("_")
    if not clean_stem:
        clean_stem = "evidence"

    if timestamp_utc:
        try:
            dt = datetime.fromisoformat(timestamp_utc)
            time_part = dt.strftime("%Y%m%d_%H%M%S")
        except Exception:
            time_part = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    else:
        time_part = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    ext = extension.lstrip(".").lower()
    return f"aegis_report_{clean_stem}_{time_part}.{ext}"


def export_pdf(report: AnalysisReport) -> bytes:
    """Render comprehensive evidence-style PDF report using ReportLab.

    Args:
        report: Populated AnalysisReport object.

    Returns:
        Raw PDF document bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Design palette
    c_accent = colors.HexColor("#087E8B")
    c_ink = colors.HexColor("#14212B")
    c_muted = colors.HexColor("#526371")
    c_line = colors.HexColor("#D8E1E8")
    c_bg = colors.HexColor("#F4F7FA")
    c_warning = colors.HexColor("#8A5A00")

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_ink,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_muted,
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_ink,
    )
    mono_style = ParagraphStyle(
        "Mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=c_ink,
    )
    notice_style = ParagraphStyle(
        "Notice",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=c_muted,
    )
    caption_style = ParagraphStyle(
        "Caption",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=c_muted,
        alignment=1,  # Centered
    )

    story = []

    # 1. Document Header
    story.append(Paragraph(f"{report.application_name} — Forensic Analysis Report", title_style))
    story.append(
        Paragraph(
            f"Version {report.application_version} | Generated: {report.generated_at_utc} | Schema: {report.schema_version}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=4, spaceAfter=8))

    # 2. Normative Notice Block
    notice_box = [
        [
            Paragraph(
                f"<b>EDUCATIONAL NOTICE:</b> {report.overall_notice}",
                notice_style,
            )
        ]
    ]
    notice_table = Table(notice_box, colWidths=[540])
    notice_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c_bg),
                ("BOX", (0, 0), (-1, -1), 1, c_line),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(notice_table)
    story.append(Spacer(1, 10))

    # 3. Evidence Identity (FileFacts)
    facts = report.file_facts
    story.append(Paragraph("Evidence Identity", section_h1))

    facts_data = [
        [
            Paragraph("<b>Original Filename</b>", body_style),
            Paragraph(_safe_escape(facts.original_filename_display), body_style),
            Paragraph("<b>Detected Format</b>", body_style),
            Paragraph(facts.detected_format, body_style),
        ],
        [
            Paragraph("<b>File Size</b>", body_style),
            Paragraph(f"{facts.size_bytes:,} bytes ({facts.size_bytes / 1024:.1f} KB)", body_style),
            Paragraph("<b>Dimensions</b>", body_style),
            Paragraph(f"{facts.width} x {facts.height} px", body_style),
        ],
        [
            Paragraph("<b>Color Mode</b>", body_style),
            Paragraph(facts.mode, body_style),
            Paragraph("<b>Frame Count</b>", body_style),
            Paragraph(str(facts.frame_count), body_style),
        ],
        [
            Paragraph("<b>SHA-256 Digest</b>", body_style),
            Paragraph(f"<b>{facts.sha256}</b>", mono_style),
            "",
            "",
        ],
        [
            Paragraph("<b>SHA-1 Digest</b>", body_style),
            Paragraph(facts.sha1 or "N/A", mono_style),
            Paragraph("<b>MD5 Digest</b>", body_style),
            Paragraph(facts.md5 or "N/A", mono_style),
        ],
    ]

    facts_table = Table(facts_data, colWidths=[105, 165, 105, 165])
    facts_table.setStyle(
        TableStyle(
            [
                ("SPAN", (1, 3), (3, 3)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, c_line),
                ("BACKGROUND", (0, 0), (0, -1), c_bg),
                ("BACKGROUND", (2, 0), (2, 2), c_bg),
                ("BACKGROUND", (2, 4), (2, 4), c_bg),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(facts_table)
    story.append(Spacer(1, 8))

    # 4. Method Results
    method_titles = {
        "metadata": "Metadata Inspection",
        "ela": "JPEG Error Level Analysis",
        "image_statistics": "Image Statistics & Color Histograms",
    }

    for method_id, method_res in report.method_results.items():
        title = method_titles.get(method_id, method_id.replace("_", " ").title())
        status_str = method_res.status.value.upper()

        method_flowables = []
        method_flowables.append(
            Paragraph(f"{title} &nbsp;&nbsp;[Status: <b>{status_str}</b>]", section_h1)
        )
        method_flowables.append(Paragraph(f"<b>Observation:</b> {_safe_escape(method_res.summary)}", body_style))
        method_flowables.append(Spacer(1, 4))

        # Photographic exposure settings if present
        obs = method_res.observations
        if method_id == "metadata" and (
            obs.get("iso") or obs.get("exposure_time") or obs.get("f_number") or obs.get("focal_length")
        ):
            exp_parts = []
            if obs.get("iso"):
                exp_parts.append(f"ISO {_safe_escape(obs['iso'])}")
            if obs.get("exposure_time"):
                exp_parts.append(f"Shutter {_safe_escape(obs['exposure_time'])}")
            if obs.get("f_number"):
                exp_parts.append(f"Aperture {_safe_escape(obs['f_number'])}")
            if obs.get("focal_length"):
                exp_parts.append(f"Focal Length {_safe_escape(obs['focal_length'])}")
            exp_text = f"<b>Exposure Settings:</b> {' | '.join(exp_parts)}"
            method_flowables.append(Paragraph(exp_text, body_style))
            method_flowables.append(Spacer(1, 3))

        # Warnings / Cues
        for w in method_res.warnings:
            w_para = Paragraph(f"<b>Review Cue:</b> {_safe_escape(w)}", body_style)
            w_table = Table([[w_para]], colWidths=[540])
            w_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E1")),
                        ("BOX", (0, 0), (-1, -1), 0.5, c_warning),
                        ("PADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            method_flowables.append(w_table)
            method_flowables.append(Spacer(1, 3))

        # Embedded Artifact Image if present
        if method_res.artifact_bytes:
            try:
                with Image.open(io.BytesIO(method_res.artifact_bytes)) as pil_img:
                    w, h = pil_img.size
                aspect = w / h if h > 0 else 1.0
                target_w = 4.2 * inch
                target_h = target_w / aspect
                if target_h > 3.0 * inch:
                    target_h = 3.0 * inch
                    target_w = target_h * aspect

                rl_img = RLImage(io.BytesIO(method_res.artifact_bytes), width=target_w, height=target_h)
                method_flowables.append(Spacer(1, 4))
                method_flowables.append(rl_img)
                method_flowables.append(
                    Paragraph("Derived Analysis Artifact — Not Original Evidence", caption_style)
                )
                method_flowables.append(Spacer(1, 4))
            except Exception:
                pass

        # Limitations note
        if method_res.limitations:
            lim_text = " | ".join(method_res.limitations[:2])
            method_flowables.append(
                Paragraph(f"<i>Limitations: {_safe_escape(lim_text)}</i>", notice_style)
            )

        method_flowables.append(Spacer(1, 8))
        story.append(KeepTogether(method_flowables))

    # 5. References and Legal Disclaimer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_line, spaceBefore=4, spaceAfter=6))
    story.append(Paragraph("Standards & References", section_h1))
    for ref in report.references:
        story.append(Paragraph(f"• {_safe_escape(ref)}", notice_style))

    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "<b>Disclaimer:</b> This report is generated by AegisImage for educational and investigative guidance. "
            "It does not constitute legal proof of authenticity, chain-of-custody certification, or definitive tamper determination.",
            notice_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
