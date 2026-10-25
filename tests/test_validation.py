"""Unit tests for input intake validation, security limits, and format enforcement."""

import io
import pytest
from PIL import Image

from src.config import MAX_IMAGE_PIXELS, MAX_UPLOAD_SIZE_BYTES
from src.exceptions import (
    AnimatedImageError,
    FileTooLargeError,
    ImageDecodeError,
    ImageDimensionsError,
    UnsupportedFormatError,
)
from src.validation import (
    inspect_and_validate_image,
    sanitize_filename,
    validate_upload_size,
)
from tests.fixtures.synthetic import (
    create_corrupt_image_bytes,
    create_synthetic_animated_gif,
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


# --- Size Validation Tests ---

def test_validate_upload_size_valid() -> None:
    """Bytes under or at 10 MiB limit pass validation."""
    validate_upload_size(b"small payload")
    validate_upload_size(b"x" * MAX_UPLOAD_SIZE_BYTES)


def test_validate_upload_size_exceeded() -> None:
    """Bytes exceeding 10 MiB limit raise FileTooLargeError."""
    oversized = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
    with pytest.raises(FileTooLargeError) as exc_info:
        validate_upload_size(oversized)
    assert "exceeds maximum size limit" in str(exc_info.value)


# --- Filename Sanitization Tests ---

def test_sanitize_filename_standard() -> None:
    """Standard filenames are preserved cleanly."""
    assert sanitize_filename("evidence.jpg") == "evidence.jpg"
    assert sanitize_filename("photo_2026.PNG") == "photo_2026.PNG"


def test_sanitize_filename_traversal_and_paths() -> None:
    """Paths and directory traversal patterns are stripped to display-only base names."""
    assert sanitize_filename("../../etc/passwd.jpg") == "passwd.jpg"
    assert sanitize_filename("..\\..\\Windows\\System32\\evidence.png") == "evidence.png"
    assert sanitize_filename("C:\\Users\\User\\secret.webp") == "secret.webp"
    assert sanitize_filename("/var/log/syslog.jpeg") == "syslog.jpeg"


def test_sanitize_filename_empty_and_special() -> None:
    """Empty or non-string filenames return safe default display name."""
    assert sanitize_filename("") == "unnamed_image"
    assert sanitize_filename("   ") == "unnamed_image"
    assert sanitize_filename(None) == "unnamed_image"
    assert sanitize_filename("...///") == "unnamed_image"


# --- Format & Decompression Safeguard Tests ---

def test_validate_supported_formats() -> None:
    """JPEG, PNG, and WebP valid inputs are successfully validated."""
    jpeg_bytes = create_synthetic_jpeg(100, 100)
    png_bytes = create_synthetic_png(100, 100)
    webp_bytes = create_synthetic_webp(100, 100)

    fmt_jpeg, (w1, h1), mode1, frames1 = inspect_and_validate_image(jpeg_bytes)
    assert fmt_jpeg == "JPEG"
    assert (w1, h1) == (100, 100)
    assert mode1 == "RGB"
    assert frames1 == 1

    fmt_png, (w2, h2), mode2, frames2 = inspect_and_validate_image(png_bytes)
    assert fmt_png == "PNG"
    assert (w2, h2) == (100, 100)
    assert frames2 == 1

    fmt_webp, (w3, h3), mode3, frames3 = inspect_and_validate_image(webp_bytes)
    assert fmt_webp == "WEBP"
    assert (w3, h3) == (100, 100)
    assert frames3 == 1


def test_validate_unsupported_formats() -> None:
    """Formats outside JPEG, PNG, WEBP (e.g., BMP, GIF, TIFF) raise UnsupportedFormatError."""
    # BMP image
    bmp_buf = io.BytesIO()
    Image.new("RGB", (50, 50), color=(10, 20, 30)).save(bmp_buf, format="BMP")
    bmp_bytes = bmp_buf.getvalue()

    with pytest.raises(UnsupportedFormatError) as exc_info:
        inspect_and_validate_image(bmp_bytes)
    assert "BMP" in str(exc_info.value)


def test_validate_animated_and_multiframe() -> None:
    """Animated or multi-frame images raise AnimatedImageError."""
    animated_gif = create_synthetic_animated_gif()
    with pytest.raises((AnimatedImageError, UnsupportedFormatError)):
        inspect_and_validate_image(animated_gif)


def test_validate_corrupt_bytes() -> None:
    """Corrupt or non-image bytes raise ImageDecodeError."""
    corrupt_data = create_corrupt_image_bytes()
    with pytest.raises(ImageDecodeError) as exc_info:
        inspect_and_validate_image(corrupt_data)
    assert "decode" in str(exc_info.value).lower()

    with pytest.raises(ImageDecodeError):
        inspect_and_validate_image(b"not an image at all")


def test_validate_pixel_limit_exceeded() -> None:
    """Images exceeding MAX_IMAGE_PIXELS raise ImageDimensionsError."""
    oversized_buf = io.BytesIO()
    old_max = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = None
        img = Image.new("RGB", (7000, 6000), color=(100, 100, 100))
        img.save(oversized_buf, format="JPEG")
    finally:
        Image.MAX_IMAGE_PIXELS = old_max

    huge_bytes = oversized_buf.getvalue()
    with pytest.warns(Image.DecompressionBombWarning):
        with pytest.raises(ImageDimensionsError) as exc_info:
            inspect_and_validate_image(huge_bytes)
    assert "exceeds" in str(exc_info.value).lower()
