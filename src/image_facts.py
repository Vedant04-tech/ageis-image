"""Extraction and construction of FileFacts evidence identity.

Orchestrates size check, original-byte hashing, filename sanitization,
and safe image property extraction.
"""

from datetime import datetime, timezone
from typing import Optional

from src.integrity import compute_integrity_hashes, compute_sha256
from src.models import FileFacts
from src.validation import (
    inspect_and_validate_image,
    sanitize_filename,
    validate_upload_size,
)


def extract_file_facts(data: bytes, original_filename: Optional[str] = None) -> FileFacts:
    """Extract verifiable facts from original uploaded image bytes.

    Execution order:
    1. Validate size constraint (10 MiB) before decode.
    2. Compute cryptographic hashes (SHA-256, SHA-1, MD5) from exact original bytes before any transformations.
    3. Sanitize original filename strictly for display.
    4. Decode and validate format, dimensions, mode, and single-frame requirement.
    5. Construct and return immutable FileFacts object.

    Args:
        data: Raw uploaded bytes.
        original_filename: User-supplied filename or None.

    Returns:
        FileFacts object populated with verified evidence properties.

    Raises:
        FileTooLargeError: If payload exceeds 10 MiB.
        UnsupportedFormatError: If image container is not JPEG, PNG, or WEBP.
        ImageDimensionsError: If resolution exceeds 40 MP or fails decompression bomb checks.
        AnimatedImageError: If image contains multiple frames.
        ImageDecodeError: If bytes are corrupt or cannot be parsed.
    """
    # 1. Byte size validation before decode
    validate_upload_size(data)

    # 2. Cryptographic digests over exact original bytes
    hashes = compute_integrity_hashes(data)

    # 3. Sanitize display filename
    display_filename = sanitize_filename(original_filename)

    # 4. Safe image inspection and decoding checks
    detected_format, (width, height), mode, frame_count = inspect_and_validate_image(data)

    # 5. Timestamp in ISO 8601 UTC
    now_utc = datetime.now(timezone.utc).isoformat()

    return FileFacts(
        original_filename_display=display_filename,
        sha256=hashes["sha256"],
        sha1=hashes["sha1"],
        md5=hashes["md5"],
        size_bytes=len(data),
        detected_format=detected_format,
        width=width,
        height=height,
        mode=mode,
        frame_count=frame_count,
        analysis_timestamp_utc=now_utc,
    )
