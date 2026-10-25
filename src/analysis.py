"""Forensic analysis orchestration.

Per architecture.md:
- Orchestrates intake, evidence hashing, metadata extraction, ELA, and image statistics.
- Isolates individual method execution so non-fatal method errors do not block independent analysis.
- Assembles a unified, schema-versioned AnalysisReport object consumed by UI and exporters.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ELA_AMPLIFICATION,
    DEFAULT_ELA_QUALITY,
    OVERALL_NOTICE,
    SCHEMA_VERSION,
)
from src.ela import compute_ela
from src.image_facts import extract_file_facts
from src.image_statistics import compute_image_statistics
from src.metadata import extract_metadata
from src.models import AnalysisReport, MethodResult, MethodStatus

STANDARD_REFERENCES: List[str] = [
    "Krawetz, N. (2007). A Picture's Worth... Digital Image Analysis and Forensics. Black Hat DC.",
    "NIST Computer Forensic Tool Testing Program (CFTT).",
    "ISO/IEC 27037:2012 Guidelines for identification, collection, acquisition and preservation of digital evidence.",
]


def analyze_image(
    data: bytes,
    filename: Optional[str] = None,
    suppress_gps: bool = True,
    ela_quality: int = DEFAULT_ELA_QUALITY,
    ela_amplification: int = DEFAULT_ELA_AMPLIFICATION,
) -> AnalysisReport:
    """Execute complete digital image forensic analysis pipeline.

    Args:
        data: Raw uploaded image bytes.
        filename: Client-supplied filename or None.
        suppress_gps: Whether to suppress exact GPS coordinates (default: True).
        ela_quality: Recompression quality for ELA if applicable (default: 90).
        ela_amplification: Difference scaling factor for ELA display (default: 10).

    Returns:
        Unified AnalysisReport containing file facts, per-method results, and limitations.

    Raises:
        FileTooLargeError: If upload exceeds 10 MiB limit.
        UnsupportedFormatError: If container is not JPEG, PNG, or WEBP.
        ImageDimensionsError: If pixel area exceeds 40 MP or triggers decompression bombs.
        AnimatedImageError: If image contains multiple frames.
        ImageDecodeError: If bytes are corrupt or malformed.
    """
    # 1. Intake validation & evidence facts (fails fast on corrupt/oversized/unsupported input)
    file_facts = extract_file_facts(data, original_filename=filename)

    method_results: Dict[str, MethodResult] = {}
    report_warnings: List[str] = []

    # 2. Metadata Inspection
    try:
        method_results["metadata"] = extract_metadata(data, suppress_gps=suppress_gps)
    except Exception as e:
        method_results["metadata"] = MethodResult(
            method_id="metadata",
            status=MethodStatus.FAILED,
            summary=f"Metadata extraction failed: {e}",
            observations={"error": str(e)},
            warnings=["Metadata parser encountered an unexpected error."],
        )
        report_warnings.append(f"Metadata extraction failed: {e}")

    # 3. JPEG Error Level Analysis (ELA)
    try:
        method_results["ela"] = compute_ela(
            data,
            detected_format=file_facts.detected_format,
            quality=ela_quality,
            amplification=ela_amplification,
        )
    except Exception as e:
        method_results["ela"] = MethodResult(
            method_id="ela",
            status=MethodStatus.FAILED,
            summary=f"Error Level Analysis failed: {e}",
            observations={"error": str(e)},
            warnings=["ELA algorithm encountered an unexpected error."],
        )
        report_warnings.append(f"ELA execution failed: {e}")

    # 4. Color Channel Statistics & Histograms
    try:
        method_results["image_statistics"] = compute_image_statistics(data)
    except Exception as e:
        method_results["image_statistics"] = MethodResult(
            method_id="image_statistics",
            status=MethodStatus.FAILED,
            summary=f"Image statistics failed: {e}",
            observations={"error": str(e)},
            warnings=["Statistical calculation encountered an unexpected error."],
        )
        report_warnings.append(f"Image statistics computation failed: {e}")

    # 5. Assemble unified AnalysisReport
    now_utc = datetime.now(timezone.utc).isoformat()
    return AnalysisReport(
        file_facts=file_facts,
        generated_at_utc=now_utc,
        method_results=method_results,
        schema_version=SCHEMA_VERSION,
        application_name=APP_NAME,
        application_version=APP_VERSION,
        overall_notice=OVERALL_NOTICE,
        report_warnings=report_warnings,
        references=STANDARD_REFERENCES,
    )
