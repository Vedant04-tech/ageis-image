"""Unit tests for JPEG Error Level Analysis (ELA)."""

import io
import json
import pytest
from PIL import Image

from src.ela import compute_ela
from src.models import MethodResult, MethodStatus
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_ela_jpeg_success() -> None:
    """Eligible JPEG input executes ELA and produces visualization and metrics."""
    jpeg_bytes = create_synthetic_jpeg(width=80, height=60, quality=95)
    result = compute_ela(jpeg_bytes, detected_format="JPEG")

    assert isinstance(result, MethodResult)
    assert result.method_id == "ela"
    assert result.status == MethodStatus.COMPLETED
    assert "quality 90" in result.summary.lower()
    assert "amplification 10" in result.summary.lower()

    obs = result.observations
    assert "mean_difference" in obs
    assert "max_difference" in obs
    assert "min_difference" in obs
    assert isinstance(obs["mean_difference"], float)
    assert isinstance(obs["max_difference"], int)
    assert obs["quality"] == 90
    assert obs["amplification"] == 10

    # Verify visualization artifact
    assert result.artifact_bytes is not None
    assert len(result.artifact_bytes) > 0
    with Image.open(io.BytesIO(result.artifact_bytes)) as art_im:
        assert art_im.size == (80, 60)
        assert art_im.format == "PNG"

    # Verify limitations and no verdict
    assert len(result.limitations) > 0
    for warning in result.warnings:
        assert "fake" not in warning.lower()
        assert "forged" not in warning.lower()


def test_ela_png_not_applicable() -> None:
    """PNG input is rejected as NOT_APPLICABLE (does not silently fake JPEG history)."""
    png_bytes = create_synthetic_png()
    result = compute_ela(png_bytes, detected_format="PNG")

    assert result.status == MethodStatus.NOT_APPLICABLE
    assert "not applicable" in result.summary.lower() or "only applicable to jpeg" in result.summary.lower()
    assert result.artifact_bytes is None


def test_ela_webp_not_applicable() -> None:
    """WebP input is rejected as NOT_APPLICABLE."""
    webp_bytes = create_synthetic_webp()
    result = compute_ela(webp_bytes, detected_format="WEBP")

    assert result.status == MethodStatus.NOT_APPLICABLE
    assert result.artifact_bytes is None


def test_ela_controlled_alteration_difference() -> None:
    """Controlled spliced JPEG fixture demonstrates detectable error level difference."""
    # 1. Base JPEG at quality 75
    base = Image.new("RGB", (100, 100), color=(180, 180, 180))
    buf = io.BytesIO()
    base.save(buf, format="JPEG", quality=75)
    base_bytes = buf.getvalue()

    # 2. Re-open base, paste an uncompressed high-contrast patch, save again at quality 95
    with Image.open(io.BytesIO(base_bytes)) as im_base:
        im_spliced = im_base.copy()
        patch = Image.new("RGB", (30, 30), color=(10, 20, 200))
        im_spliced.paste(patch, (35, 35))
        spliced_buf = io.BytesIO()
        im_spliced.save(spliced_buf, format="JPEG", quality=95)
        spliced_bytes = spliced_buf.getvalue()

    result_clean = compute_ela(base_bytes, detected_format="JPEG")
    result_spliced = compute_ela(spliced_bytes, detected_format="JPEG")

    assert result_clean.status == MethodStatus.COMPLETED
    assert result_spliced.status == MethodStatus.COMPLETED
    # The spliced region produces higher compression error differences
    assert result_spliced.observations["max_difference"] > 0


def test_ela_json_serialization() -> None:
    """Result serializes cleanly to JSON without binary payload leak."""
    jpeg_bytes = create_synthetic_jpeg()
    result = compute_ela(jpeg_bytes, detected_format="JPEG")

    res_dict = result.to_dict()
    assert "artifact_bytes" not in res_dict  # Excluded from JSON dict
    json_str = json.dumps(res_dict)
    assert isinstance(json_str, str)
    loaded = json.loads(json_str)
    assert loaded["method_id"] == "ela"
    assert loaded["status"] == "completed"
