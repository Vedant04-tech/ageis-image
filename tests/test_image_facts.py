"""Unit tests for FileFacts extraction and evidence identity."""

from datetime import datetime, timezone
import pytest
from src.exceptions import (
    FileTooLargeError,
    ImageDecodeError,
    UnsupportedFormatError,
)
from src.image_facts import extract_file_facts
from src.integrity import compute_sha256
from src.models import FileFacts
from tests.fixtures.synthetic import (
    create_corrupt_image_bytes,
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_extract_file_facts_jpeg() -> None:
    """Verify complete FileFacts extraction from a valid JPEG."""
    jpeg_bytes = create_synthetic_jpeg(width=120, height=80)
    facts = extract_file_facts(jpeg_bytes, original_filename="../../suspicious_upload.jpg")

    assert isinstance(facts, FileFacts)
    assert facts.original_filename_display == "suspicious_upload.jpg"
    assert facts.sha256 == compute_sha256(jpeg_bytes)
    assert len(facts.sha1) == 40
    assert len(facts.md5) == 32
    assert facts.size_bytes == len(jpeg_bytes)
    assert facts.detected_format == "JPEG"
    assert facts.width == 120
    assert facts.height == 80
    assert facts.mode == "RGB"
    assert facts.frame_count == 1

    # Verify timestamp format (ISO 8601 UTC)
    ts = datetime.fromisoformat(facts.analysis_timestamp_utc)
    assert ts.tzinfo is not None


def test_extract_file_facts_png() -> None:
    """Verify FileFacts extraction from a valid PNG."""
    png_bytes = create_synthetic_png(width=50, height=75)
    facts = extract_file_facts(png_bytes, original_filename="scan.png")

    assert facts.detected_format == "PNG"
    assert facts.width == 50
    assert facts.height == 75
    assert facts.size_bytes == len(png_bytes)


def test_extract_file_facts_webp() -> None:
    """Verify FileFacts extraction from a valid WebP."""
    webp_bytes = create_synthetic_webp(width=200, height=150)
    facts = extract_file_facts(webp_bytes)

    assert facts.detected_format == "WEBP"
    assert facts.width == 200
    assert facts.height == 150
    assert facts.original_filename_display == "unnamed_image"


def test_extract_file_facts_extension_mismatch() -> None:
    """Verify facts detected_format relies on decoded bytes, not extension."""
    jpeg_bytes = create_synthetic_jpeg(width=100, height=100)
    # File disguised with a .png extension
    facts = extract_file_facts(jpeg_bytes, original_filename="fake_image.png")
    assert facts.detected_format == "JPEG"


def test_extract_file_facts_corrupt_rejection() -> None:
    """Verify corrupt bytes fail gracefully with ImageDecodeError."""
    corrupt = create_corrupt_image_bytes()
    with pytest.raises(ImageDecodeError):
        extract_file_facts(corrupt, original_filename="corrupt.jpg")


def test_extract_file_facts_oversized_rejection() -> None:
    """Verify oversized bytes fail before decoding with FileTooLargeError."""
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        extract_file_facts(oversized, original_filename="huge.jpg")
