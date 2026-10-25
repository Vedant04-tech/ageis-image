"""Unit tests for JSON and PDF report generation and security controls."""

import json
import pytest
from src.analysis import analyze_image
from src.reporting import export_json, export_pdf, generate_export_filename
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_jpeg_with_gps,
    create_synthetic_png,
)


def test_export_json_schema_and_values() -> None:
    """Verify JSON export contains required schema fields and accurate digest."""
    jpeg_bytes = create_synthetic_jpeg(width=80, height=60)
    report = analyze_image(jpeg_bytes, filename="test_sample.jpg")

    json_str = export_json(report)
    assert isinstance(json_str, str)

    loaded = json.loads(json_str)
    assert loaded["schema_version"] == "1.0"
    assert loaded["application_name"] == "AegisImage"
    assert "file_facts" in loaded
    assert "method_results" in loaded
    assert loaded["file_facts"]["sha256"] == report.file_facts.sha256
    assert loaded["file_facts"]["sha1"] == report.file_facts.sha1
    assert loaded["file_facts"]["md5"] == report.file_facts.md5
    assert loaded["file_facts"]["width"] == 80
    assert loaded["file_facts"]["height"] == 60

    # Ensure no binary payloads leaked into JSON
    assert "artifact_bytes" not in json_str


def test_export_json_gps_suppression() -> None:
    """Verify exact GPS coordinates are excluded from JSON report."""
    gps_jpeg = create_synthetic_jpeg_with_gps()
    report = analyze_image(gps_jpeg, filename="geotagged.jpg", suppress_gps=True)

    json_str = export_json(report)
    loaded = json.loads(json_str)

    meta_obs = loaded["method_results"]["metadata"]["observations"]
    assert meta_obs["gps_present"] is True
    assert meta_obs.get("gps_coordinates") is None

    # Check that raw coordinate tags are not in raw_tags
    raw = meta_obs.get("raw_tags", {})
    assert "GPSLatitude" not in raw
    assert "GPSLongitude" not in raw


def test_export_pdf_valid_header_and_structure() -> None:
    """Verify PDF generation succeeds and outputs valid PDF document bytes."""
    jpeg_bytes = create_synthetic_jpeg(width=90, height=70)
    report = analyze_image(jpeg_bytes, filename="evidence.jpg")

    pdf_bytes = export_pdf(report)
    assert isinstance(pdf_bytes, bytes)
    # Valid PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")
    # File size should be substantive given ReportLab formatting
    assert len(pdf_bytes) > 2000


def test_export_pdf_non_jpeg_with_missing_ela_artifact() -> None:
    """PDF exports successfully for PNG input where ELA is NOT_APPLICABLE."""
    png_bytes = create_synthetic_png()
    report = analyze_image(png_bytes, filename="scan.png")

    pdf_bytes = export_pdf(report)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_generate_export_filename_safe() -> None:
    """Verify export filenames sanitize input and neutralize path traversal."""
    fn_pdf = generate_export_filename("../../malicious/path.jpg", "pdf")
    assert fn_pdf.endswith(".pdf")
    assert "/" not in fn_pdf
    assert "\\" not in fn_pdf
    assert ".." not in fn_pdf
    assert "aegis_report_" in fn_pdf

    fn_json = generate_export_filename("standard_test.PNG", "json")
    assert fn_json.endswith(".json")
    assert "aegis_report_standard_test" in fn_json
