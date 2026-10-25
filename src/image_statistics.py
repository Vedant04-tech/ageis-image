"""Color channel histograms and descriptive image statistics.

Per architecture.md and rules.md:
- Computes separate Red, Green, Blue channel histograms with fixed 256 bins.
- Calculates per-channel statistical summaries (mean, std_dev, min, max, median).
- Safely handles color, grayscale ('L'), and palette ('P') images via working RGB conversion.
- Generates a local Matplotlib visualization artifact without external network requests.
- All numeric outputs are converted from NumPy to native Python types for JSON purity.
- Histograms are descriptive statistics, never manipulation classifiers.
"""

import io
import math
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend safe for headless/server execution
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from src.config import HISTOGRAM_BINS
from src.models import MethodResult, MethodStatus


def _channel_metrics(channel_data: np.ndarray) -> Dict[str, Any]:
    """Compute basic descriptive summary metrics for a single color channel."""
    return {
        "mean": round(float(np.mean(channel_data)), 3),
        "std_dev": round(float(np.std(channel_data)), 3),
        "min": int(np.min(channel_data)),
        "max": int(np.max(channel_data)),
        "median": float(np.median(channel_data)),
    }


def compute_image_statistics(
    data: bytes,
    bins: int = HISTOGRAM_BINS,
) -> MethodResult:
    """Compute 256-bin channel histograms and summary statistics.

    Args:
        data: Raw image bytes.
        bins: Number of histogram bins across 0-255 intensity range (default: 256).

    Returns:
        MethodResult containing channel histograms, summary statistics, and plot artifact.
    """
    safe_bins = max(1, min(256, int(bins)))
    parameters: Dict[str, Any] = {"bins": safe_bins, "range": [0, 255]}
    limitations: List[str] = [
        "Histograms describe pixel intensity distributions across color channels.",
        "Histogram analysis is descriptive and cannot independently detect or prove image manipulation.",
        "Color conversions for palette or grayscale inputs are working representations and do not modify source bytes.",
    ]

    try:
        with Image.open(io.BytesIO(data)) as im:
            orig_mode = im.mode
            width, height = im.size
            # Working copy in RGB for consistent 3-channel statistical analysis
            rgb_im = im.convert("RGB")

        arr = np.array(rgb_im, dtype=np.uint8)
        r_channel = arr[:, :, 0]
        g_channel = arr[:, :, 1]
        b_channel = arr[:, :, 2]
        # ITU-R BT.601 perceptual luminance
        lum_channel = np.clip(
            0.299 * r_channel.astype(np.float32)
            + 0.587 * g_channel.astype(np.float32)
            + 0.114 * b_channel.astype(np.float32),
            0,
            255,
        ).astype(np.uint8)

        # Calculate 256-bin histograms
        r_hist, _ = np.histogram(r_channel, bins=safe_bins, range=(0, 256))
        g_hist, _ = np.histogram(g_channel, bins=safe_bins, range=(0, 256))
        b_hist, _ = np.histogram(b_channel, bins=safe_bins, range=(0, 256))
        lum_hist, _ = np.histogram(lum_channel, bins=safe_bins, range=(0, 256))

        # Channel statistics
        channel_stats: Dict[str, Dict[str, Any]] = {
            "red": _channel_metrics(r_channel),
            "green": _channel_metrics(g_channel),
            "blue": _channel_metrics(b_channel),
            "luminance": _channel_metrics(lum_channel),
        }

        # Calculate simplified aspect ratio
        gcd_val = math.gcd(width, height)
        aspect_ratio = f"{width // gcd_val}:{height // gcd_val}"
        total_pixels = width * height

        # Check for potential clipping
        warnings: List[str] = []
        zero_count = int(r_hist[0] + g_hist[0] + b_hist[0])
        max_count = int(r_hist[-1] + g_hist[-1] + b_hist[-1])
        clip_threshold = total_pixels * 0.15  # >15% of pixels at extreme limits
        if zero_count > clip_threshold or max_count > clip_threshold:
            warnings.append(
                "Noticeable concentration of pixel intensities at dynamic range limits (0 or 255); "
                "this often indicates sensor clipping, underexposure, or high-contrast graphics."
            )

        # Generate Matplotlib plot artifact
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=100)
        try:
            x_axis = np.arange(safe_bins)
            ax.plot(x_axis, r_hist, color="#D32F2F", label="Red Channel", alpha=0.85, linewidth=1.4)
            ax.plot(x_axis, g_hist, color="#388E3C", label="Green Channel", alpha=0.85, linewidth=1.4)
            ax.plot(x_axis, b_hist, color="#1976D2", label="Blue Channel", alpha=0.85, linewidth=1.4)
            ax.plot(x_axis, lum_hist, color="#546E7A", label="Luminance (Y)", alpha=0.9, linewidth=1.4, linestyle="--")

            ax.set_title("Color Channel & Luminance Histograms", fontsize=11, fontweight="bold", pad=8)
            ax.set_xlabel("Pixel Intensity (0 - 255)", fontsize=9)
            ax.set_ylabel("Pixel Count", fontsize=9)
            ax.set_xlim(0, 255)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.legend(loc="upper right", fontsize=8)
            fig.tight_layout()

            plot_buf = io.BytesIO()
            fig.savefig(plot_buf, format="PNG")
            plot_bytes = plot_buf.getvalue()
        finally:
            plt.close(fig)

        summary = (
            f"Color channel distribution and descriptive statistics computed across "
            f"{width}x{height} pixels ({total_pixels:,} total)."
        )

        observations: Dict[str, Any] = {
            "mode": orig_mode,
            "width": width,
            "height": height,
            "total_pixels": total_pixels,
            "aspect_ratio": aspect_ratio,
            "histograms": {
                "red": [int(x) for x in r_hist],
                "green": [int(x) for x in g_hist],
                "blue": [int(x) for x in b_hist],
                "luminance": [int(x) for x in lum_hist],
            },
            "channel_statistics": channel_stats,
        }

        return MethodResult(
            method_id="image_statistics",
            status=MethodStatus.COMPLETED,
            summary=summary,
            observations=observations,
            warnings=warnings,
            limitations=limitations,
            parameters=parameters,
            artifact_ids=["channel_histograms"],
            artifact_bytes=plot_bytes,
        )

    except Exception as e:
        return MethodResult(
            method_id="image_statistics",
            status=MethodStatus.FAILED,
            summary=f"Failed to compute image statistics: {e}",
            observations={"error": str(e)},
            warnings=[f"Statistics computation encountered an error: {e}"],
            limitations=limitations,
            parameters=parameters,
            artifact_bytes=None,
        )
