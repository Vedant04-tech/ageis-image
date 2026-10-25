"""Unit tests for image statistics and color channel histograms."""

import io
import json
import pytest
from PIL import Image

from src.image_statistics import compute_image_statistics
from src.models import MethodResult, MethodStatus
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_statistics_rgb_jpeg() -> None:
    """Verify channel histograms, summaries, and Matplotlib plot for RGB JPEG."""
    jpeg_bytes = create_synthetic_jpeg(width=100, height=80, color=(128, 64, 192))
    result = compute_image_statistics(jpeg_bytes)

    assert isinstance(result, MethodResult)
    assert result.method_id == "image_statistics"
    assert result.status == MethodStatus.COMPLETED

    obs = result.observations
    assert obs["total_pixels"] == 8000
    assert obs["aspect_ratio"] == "5:4"

    # Channel histograms (256 bins each)
    histograms = obs["histograms"]
    assert len(histograms["red"]) == 256
    assert len(histograms["green"]) == 256
    assert len(histograms["blue"]) == 256
    assert len(histograms["luminance"]) == 256

    # Channel summaries
    channel_stats = obs["channel_statistics"]
    for ch in ("red", "green", "blue", "luminance"):
        stats = channel_stats[ch]
        assert "mean" in stats
        assert "std_dev" in stats
        assert "min" in stats
        assert "max" in stats
        assert "median" in stats
        assert isinstance(stats["mean"], float)
        assert isinstance(stats["min"], int)

    # Matplotlib visualization artifact
    assert result.artifact_bytes is not None
    with Image.open(io.BytesIO(result.artifact_bytes)) as plot_im:
        assert plot_im.format == "PNG"


def test_statistics_png_and_webp() -> None:
    """Verify statistics calculation on PNG and WebP formats."""
    png_bytes = create_synthetic_png(width=50, height=50)
    res_png = compute_image_statistics(png_bytes)
    assert res_png.status == MethodStatus.COMPLETED
    assert res_png.observations["total_pixels"] == 2500

    webp_bytes = create_synthetic_webp(width=60, height=40)
    res_webp = compute_image_statistics(webp_bytes)
    assert res_webp.status == MethodStatus.COMPLETED
    assert res_webp.observations["total_pixels"] == 2400


def test_statistics_grayscale_input() -> None:
    """Verify graceful handling of grayscale ('L') single-channel image."""
    gray_buf = io.BytesIO()
    Image.new("L", (40, 40), color=128).save(gray_buf, format="PNG")
    gray_bytes = gray_buf.getvalue()

    result = compute_image_statistics(gray_bytes)
    assert result.status == MethodStatus.COMPLETED
    obs = result.observations
    assert "channel_statistics" in obs
    assert result.artifact_bytes is not None


def test_statistics_json_serializable() -> None:
    """Verify that all numeric types serialize cleanly to JSON."""
    jpeg_bytes = create_synthetic_jpeg()
    result = compute_image_statistics(jpeg_bytes)

    res_dict = result.to_dict()
    assert "artifact_bytes" not in res_dict
    json_str = json.dumps(res_dict)
    assert isinstance(json_str, str)
    loaded = json.loads(json_str)
    assert loaded["method_id"] == "image_statistics"
