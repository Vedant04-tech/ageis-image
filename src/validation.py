"""Upload validation and decompression safeguards.

Per architecture.md:
- Enforce 10 MiB byte-size limit before decoding.
- Detect actual image format; do not rely on extensions or MIME types.
- Restrict to supported formats: JPEG, PNG, WEBP.
- Enforce 40 MP maximum pixel area and single-frame policy.
- Sanitize original filename for display only (never use as a filesystem path).
"""

import io
from pathlib import PurePath
import re
from typing import Optional, Tuple
import warnings
from PIL import Image, UnidentifiedImageError

from src.config import (
    MAX_IMAGE_PIXELS,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_FORMATS,
)
from src.exceptions import (
    AnimatedImageError,
    FileTooLargeError,
    ImageDecodeError,
    ImageDimensionsError,
    UnsupportedFormatError,
)

# Explicitly configure Pillow global decompression bomb safeguards to 40 MP
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def validate_upload_size(data: bytes) -> None:
    """Validate that upload bytes do not exceed the size limit.

    Args:
        data: Raw uploaded file bytes.

    Raises:
        FileTooLargeError: If payload exceeds MAX_UPLOAD_SIZE_BYTES.
    """
    size = len(data)
    if size > MAX_UPLOAD_SIZE_BYTES:
        max_mib = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise FileTooLargeError(
            f"Uploaded file size ({size:,} bytes) exceeds maximum size limit of "
            f"{MAX_UPLOAD_SIZE_BYTES:,} bytes ({max_mib} MiB)."
        )


def sanitize_filename(filename: Optional[str]) -> str:
    """Sanitize user-provided filename strictly for display purposes.

    WARNING: This output MUST NOT be used to construct disk paths or shell commands.

    Args:
        filename: Client-supplied filename or None.

    Returns:
        Safe display basename.
    """
    if filename is None:
        return "unnamed_image"

    raw = str(filename).strip()
    if not raw:
        return "unnamed_image"

    # Normalize Windows and Unix path separators and extract terminal component
    raw = raw.replace("\\", "/")
    basename = PurePath(raw).name.strip()

    # Strip control characters, null bytes, and leading/trailing dots/spaces
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", basename).strip(" .")

    if not sanitized:
        return "unnamed_image"

    # Enforce safe length limit for display to prevent UI layout breakage or buffer bloat
    if len(sanitized) > 255:
        p = PurePath(sanitized)
        ext = p.suffix[:20]
        stem_max = max(1, 255 - len(ext))
        sanitized = p.stem[:stem_max] + ext

    return sanitized


def inspect_and_validate_image(data: bytes) -> Tuple[str, Tuple[int, int], str, int]:
    """Inspect and validate image format, dimensions, frame count, and integrity.

    Args:
        data: Raw image bytes (must already be size-validated).

    Returns:
        Tuple containing:
        - normalized format (e.g. 'JPEG', 'PNG', 'WEBP')
        - (width, height)
        - color mode string (e.g. 'RGB')
        - frame count (integer, guaranteed to be 1 for valid single frames)

    Raises:
        ImageDimensionsError: If dimensions exceed MAX_IMAGE_PIXELS or trigger bomb limits.
        UnsupportedFormatError: If format is not in SUPPORTED_FORMATS.
        AnimatedImageError: If image contains multiple frames.
        ImageDecodeError: If image bytes are truncated, corrupt, or unparseable.
    """
    if not data:
        raise ImageDecodeError("Uploaded file is empty (0 bytes).")

    try:
        stream = io.BytesIO(data)
        with Image.open(stream) as im:
            raw_format = im.format
            if not raw_format:
                raise ImageDecodeError("Unable to detect image container format.")

            norm_format = raw_format.upper()
            if norm_format == "JPG":
                norm_format = "JPEG"

            # Check supported formats
            if norm_format not in SUPPORTED_FORMATS:
                raise UnsupportedFormatError(
                    f"Unsupported image format '{norm_format}'. "
                    f"Allowed formats are: {', '.join(SUPPORTED_FORMATS)}."
                )

            # Check dimensions & pixel area
            width, height = im.size
            if width <= 0 or height <= 0:
                raise ImageDimensionsError(f"Invalid image dimensions: {width}x{height}.")

            pixel_count = width * height
            if pixel_count > MAX_IMAGE_PIXELS:
                raise ImageDimensionsError(
                    f"Image resolution {width}x{height} ({pixel_count:,} pixels) "
                    f"exceeds maximum allowed limit of {MAX_IMAGE_PIXELS:,} pixels."
                )

            # Check single-frame policy
            frame_count = getattr(im, "n_frames", 1)
            if frame_count > 1:
                raise AnimatedImageError(
                    f"Multi-frame or animated images are not supported in MVP "
                    f"(detected {frame_count} frames)."
                )

            # Ensure image pixels are decodable and not truncated
            im.load()
            mode = im.mode

            return norm_format, (width, height), mode, frame_count

    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ImageDimensionsError(
            f"Image exceeds safe decompression limits: {e}"
        ) from e
    except (UnsupportedFormatError, AnimatedImageError, ImageDimensionsError):
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as e:
        raise ImageDecodeError(
            f"Failed to decode image data. The file may be corrupt or malformed: {e}"
        ) from e
