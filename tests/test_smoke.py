"""Smoke tests verifying Phase 0 foundation, contracts, and environment."""

import json
from src import APP_NAME, APP_VERSION
from src.config import (
    MAX_IMAGE_PIXELS,
    MAX_UPLOAD_SIZE_BYTES,
    OVERALL_NOTICE,
    SCHEMA_VERSION,
    SUPPORTED_FORMATS,
)
from src.exceptions import FileTooLargeError, ForensicError, UnsupportedFormatError
from src.models import AnalysisReport, FileFacts, MethodResult, MethodStatus
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_package_exports() -> None:
    """Verify package name and version constant exports."""
    assert APP_NAME == "AegisImage"
    assert APP_VERSION == "0.1.0"


def test_config_constants() -> None:
    """Verify configuration boundaries match specification."""
    assert MAX_UPLOAD_SIZE_BYTES == 10 * 1024 * 1024
    assert MAX_IMAGE_PIXELS == 40_000_000
    assert "JPEG" in SUPPORTED_FORMATS
    assert "PNG" in SUPPORTED_FORMATS
    assert "WEBP" in SUPPORTED_FORMATS
    assert SCHEMA_VERSION == "1.0"
    assert "educational" in OVERALL_NOTICE.lower()


def test_exceptions_hierarchy() -> None:
    """Verify custom domain exceptions inherit from ForensicError."""
    with pytest_raises(ForensicError):
        raise FileTooLargeError("File exceeds 10 MiB limit")

    with pytest_raises(ForensicError):
        raise UnsupportedFormatError("SVG not supported")


def pytest_raises(expected_type):
    import pytest
    return pytest.raises(expected_type)


def test_models_instantiation_and_serialization() -> None:
    """Verify FileFacts, MethodResult, and AnalysisReport contract and serialization."""
    facts = FileFacts(
        original_filename_display="sample.jpg",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        size_bytes=1024,
        detected_format="JPEG",
        width=100,
        height=100,
        mode="RGB",
        frame_count=1,
        analysis_timestamp_utc="2026-10-23T12:00:00Z",
    )
    assert facts.size_bytes == 1024
    facts_dict = facts.to_dict()
    assert facts_dict["sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    method_res = MethodResult(
        method_id="metadata",
        status=MethodStatus.COMPLETED,
        summary="EXIF metadata inspected.",
        observations={"camera_make": "TestCamera"},
        warnings=[],
        limitations=["Metadata can be forged."],
        parameters={},
    )
    method_dict = method_res.to_dict()
    assert method_dict["status"] == "completed"

    report = AnalysisReport(
        file_facts=facts,
        generated_at_utc="2026-10-23T12:00:00Z",
        method_results={"metadata": method_res},
    )
    report_dict = report.to_dict()
    assert report_dict["schema_version"] == "1.0"
    assert report_dict["application_name"] == "AegisImage"
    assert "metadata" in report_dict["method_results"]

    # Verify JSON serializability
    json_str = json.dumps(report_dict)
    assert isinstance(json_str, str)
    loaded = json.loads(json_str)
    assert loaded["file_facts"]["width"] == 100


def test_synthetic_fixture_generation() -> None:
    """Verify synthetic image generator generates non-empty valid bytes."""
    jpeg_bytes = create_synthetic_jpeg(64, 64)
    png_bytes = create_synthetic_png(64, 64)
    webp_bytes = create_synthetic_webp(64, 64)

    assert len(jpeg_bytes) > 0
    assert len(png_bytes) > 0
    assert len(webp_bytes) > 0
    assert jpeg_bytes.startswith(b"\xff\xd8")  # JPEG SOI
    assert png_bytes.startswith(b"\x89PNG")  # PNG magic
    assert webp_bytes[:4] == b"RIFF" and webp_bytes[8:12] == b"WEBP"  # WebP magic
