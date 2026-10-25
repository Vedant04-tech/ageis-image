"""Unit tests for analysis orchestration and report aggregation."""

import pytest
from src.analysis import analyze_image
from src.exceptions import FileTooLargeError, ImageDecodeError
from src.integrity import compute_sha256
from src.models import AnalysisReport, MethodStatus
from tests.fixtures.synthetic import (
    create_corrupt_image_bytes,
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_analyze_image_jpeg_complete() -> None:
    """JPEG analysis runs all methods: metadata, ELA, and statistics."""
    jpeg_bytes = create_synthetic_jpeg(width=100, height=80)
    report = analyze_image(jpeg_bytes, filename="evidence_photo.jpg")

    assert isinstance(report, AnalysisReport)
    assert report.application_name == "AegisImage"
    assert report.schema_version == "1.0"
    assert report.file_facts.sha256 == compute_sha256(jpeg_bytes)
    assert report.file_facts.detected_format == "JPEG"

    # All three core methods should be present
    assert "metadata" in report.method_results
    assert "ela" in report.method_results
    assert "image_statistics" in report.method_results

    assert report.method_results["metadata"].status == MethodStatus.COMPLETED
    assert report.method_results["ela"].status == MethodStatus.COMPLETED
    assert report.method_results["image_statistics"].status == MethodStatus.COMPLETED

    # Check ELA and statistics artifacts
    assert report.method_results["ela"].artifact_bytes is not None
    assert report.method_results["image_statistics"].artifact_bytes is not None


def test_analyze_image_png_ela_not_applicable() -> None:
    """PNG analysis runs metadata and stats, marking ELA as NOT_APPLICABLE."""
    png_bytes = create_synthetic_png(width=50, height=50)
    report = analyze_image(png_bytes, filename="document_scan.png")

    assert report.file_facts.detected_format == "PNG"
    assert report.method_results["metadata"].status == MethodStatus.COMPLETED
    assert report.method_results["ela"].status == MethodStatus.NOT_APPLICABLE
    assert report.method_results["image_statistics"].status == MethodStatus.COMPLETED


def test_analyze_image_intake_failure_propagation() -> None:
    """Intake failures (corrupt or oversized) fail immediately at validation boundary."""
    corrupt_bytes = create_corrupt_image_bytes()
    with pytest.raises(ImageDecodeError):
        analyze_image(corrupt_bytes)

    oversized = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        analyze_image(oversized)


def test_analyze_image_custom_ela_parameters() -> None:
    """Verify analyze_image passes custom ELA parameters to compute_ela."""
    jpeg_bytes = create_synthetic_jpeg(width=80, height=60)
    report = analyze_image(
        jpeg_bytes,
        filename="custom_ela.jpg",
        ela_quality=75,
        ela_amplification=15,
    )

    ela_res = report.method_results["ela"]
    assert ela_res.status == MethodStatus.COMPLETED
    assert ela_res.parameters["quality"] == 75
    assert ela_res.parameters["amplification"] == 15
    assert ela_res.observations["quality"] == 75
    assert ela_res.observations["amplification"] == 15

