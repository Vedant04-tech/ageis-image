"""JPEG Error Level Analysis (ELA) implementation.

Per architecture.md, rules.md, and ADR-003:
- ELA is strictly limited to validated JPEG input; PNG/WebP return NOT_APPLICABLE.
- Uses standard working recompression quality (default: 90) and amplification (default: 10x).
- Computes per-pixel absolute channel difference and clamps to valid RGB range.
- Derived artifact is labeled exploratory; NO binary verdict or tampering score is emitted.
"""

import io
from typing import Any, Dict, List, Optional
import numpy as np
from PIL import Image

from src.config import (
    DEFAULT_ELA_AMPLIFICATION,
    DEFAULT_ELA_QUALITY,
    ELA_NOTICE,
)
from src.exceptions import AnalysisMethodError
from src.models import MethodResult, MethodStatus


def compute_ela(
    data: bytes,
    detected_format: str,
    quality: int = DEFAULT_ELA_QUALITY,
    amplification: int = DEFAULT_ELA_AMPLIFICATION,
) -> MethodResult:
    """Compute JPEG Error Level Analysis on image bytes.

    Args:
        data: Raw image bytes.
        detected_format: Validated container format (e.g. 'JPEG', 'PNG', 'WEBP').
        quality: JPEG recompression quality setting (default: 90).
        amplification: Difference scaling factor for display (default: 10).

    Returns:
        MethodResult containing metrics, visualization PNG artifact, and limitations.
    """
    safe_quality = max(1, min(100, int(quality)))
    safe_amplification = max(0, int(amplification))
    norm_fmt = detected_format.upper()
    parameters: Dict[str, Any] = {
        "quality": safe_quality,
        "amplification": safe_amplification,
    }
    limitations: List[str] = [
        ELA_NOTICE,
        "ELA is an exploratory visualization and cannot provide a definitive authenticity or forgery verdict.",
        "Variations in error level occur naturally across high-frequency edges, solid fields, and complex textures.",
        "Resaving or recompressing an image repeatedly reduces global error levels.",
    ]

    # Enforce JPEG-only eligibility policy (ADR-003)
    if norm_fmt not in ("JPEG", "JPG"):
        return MethodResult(
            method_id="ela",
            status=MethodStatus.NOT_APPLICABLE,
            summary=(
                f"Error Level Analysis is only applicable to JPEG images. "
                f"Input format '{detected_format}' does not use lossy discrete cosine transform compression."
            ),
            observations={"eligible": False, "detected_format": detected_format},
            warnings=[
                f"ELA skipped: Format '{detected_format}' is not eligible for JPEG recompression analysis."
            ],
            limitations=limitations,
            parameters=parameters,
            artifact_bytes=None,
        )

    try:
        # 1. Decode original into RGB working representation
        with Image.open(io.BytesIO(data)) as im:
            orig_rgb = im.convert("RGB")
            width, height = orig_rgb.size

        # 2. Re-encode working copy at documented quality
        recompressed_buf = io.BytesIO()
        orig_rgb.save(
            recompressed_buf,
            format="JPEG",
            quality=safe_quality,
            optimize=False,
            progressive=False,
            )
        recompressed_buf.seek(0)

        # 3. Decode recompressed working copy
        with Image.open(recompressed_buf) as recomp_im:
            recomp_rgb = recomp_im.convert("RGB")

        # 4. Compute per-pixel channel differences using NumPy
        orig_arr = np.array(orig_rgb, dtype=np.int16)
        recomp_arr = np.array(recomp_rgb, dtype=np.int16)
        diff_arr = np.abs(orig_arr - recomp_arr)

        # 5. Calculate descriptive metrics (strictly converted to native Python types)
        mean_diff = float(np.mean(diff_arr))
        max_diff = int(np.max(diff_arr))
        min_diff = int(np.min(diff_arr))

        # 6. Amplify differences and clamp to valid 8-bit range
        amplified_arr = np.clip(diff_arr * safe_amplification, 0, 255).astype(np.uint8)
        ela_image = Image.fromarray(amplified_arr, mode="RGB")

        # 7. Encode derived visual artifact as PNG bytes
        artifact_buf = io.BytesIO()
        ela_image.save(artifact_buf, format="PNG")
        artifact_bytes = artifact_buf.getvalue()

        summary = (
            f"Error Level Analysis visualization generated with recompression quality {safe_quality} "
            f"and amplification {safe_amplification}x."
        )

        observations: Dict[str, Any] = {
            "eligible": True,
            "quality": safe_quality,
            "amplification": safe_amplification,
            "width": width,
            "height": height,
            "mean_difference": round(mean_diff, 4),
            "max_difference": max_diff,
            "min_difference": min_diff,
        }

        warnings: List[str] = [
            "ELA visualization highlights variations in compression error. "
            "Bright areas indicate higher differences between original and recompressed pixels; "
            "this naturally happens around contrast edges, fine textures, or spliced regions."
        ]

        return MethodResult(
            method_id="ela",
            status=MethodStatus.COMPLETED,
            summary=summary,
            observations=observations,
            warnings=warnings,
            limitations=limitations,
            parameters=parameters,
            artifact_ids=["ela_visualization"],
            artifact_bytes=artifact_bytes,
        )

    except Exception as e:
        return MethodResult(
            method_id="ela",
            status=MethodStatus.FAILED,
            summary=f"Error Level Analysis execution failed: {e}",
            observations={"eligible": True, "error": str(e)},
            warnings=[f"Failed to generate ELA visualization: {e}"],
            limitations=limitations,
            parameters=parameters,
            artifact_bytes=None,
        )
