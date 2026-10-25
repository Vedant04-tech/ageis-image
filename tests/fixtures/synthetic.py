"""Synthetic in-memory image generator for tests and benchmarks.

Ensures no personal photos, sensitive metadata, or copyrighted assets are committed.
"""

import io
from typing import Tuple
from PIL import Image


def create_synthetic_jpeg(
    width: int = 100,
    height: int = 100,
    color: Tuple[int, int, int] = (128, 128, 128),
    quality: int = 90,
) -> bytes:
    """Generate in-memory JPEG bytes without external dependencies."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def create_synthetic_png(
    width: int = 100,
    height: int = 100,
    color: Tuple[int, int, int] = (64, 128, 192),
) -> bytes:
    """Generate in-memory PNG bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_synthetic_webp(
    width: int = 100,
    height: int = 100,
    color: Tuple[int, int, int] = (200, 100, 50),
) -> bytes:
    """Generate in-memory WebP bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP")
    return buffer.getvalue()


def create_synthetic_animated_gif(width: int = 50, height: int = 50) -> bytes:
    """Generate in-memory animated multi-frame GIF for validation testing."""
    frame1 = Image.new("RGB", (width, height), color=(255, 0, 0))
    frame2 = Image.new("RGB", (width, height), color=(0, 255, 0))
    buffer = io.BytesIO()
    frame1.save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=[frame2],
        duration=100,
        loop=0,
    )
    return buffer.getvalue()


def create_corrupt_image_bytes() -> bytes:
    """Generate invalid, corrupt image bytes with a valid JPEG header followed by garbage."""
    # JPEG magic SOI marker followed by random corrupt data
    return b"\xff\xd8\xff\xe0" + b"\x00" * 32


def create_synthetic_jpeg_with_exif(
    make: str = "AegisTestCam",
    model: str = "Forensics-100",
    software: str = "Adobe Photoshop 2024",
    date_time: str = "2026:10:23 14:30:00",
) -> bytes:
    """Generate in-memory JPEG with standard EXIF metadata."""
    from PIL.ExifTags import IFD
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    exif = Image.Exif()
    exif[271] = make  # Make
    exif[272] = model  # Model
    exif[305] = software  # Software
    exif[306] = date_time  # DateTime
    # Sub-IFD DateTimeOriginal
    exif_ifd = exif.get_ifd(IFD.Exif)
    exif_ifd[36867] = date_time  # DateTimeOriginal

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def create_synthetic_jpeg_with_gps(
    latitude_ref: str = "N",
    latitude: Tuple[float, float, float] = (37.0, 46.0, 29.74),
    longitude_ref: str = "W",
    longitude: Tuple[float, float, float] = (122.0, 25.0, 9.83),
) -> bytes:
    """Generate in-memory JPEG with GPS metadata."""
    from fractions import Fraction
    from PIL.ExifTags import IFD
    img = Image.new("RGB", (100, 100), color=(120, 180, 240))
    exif = Image.Exif()
    exif[271] = "GPSTestCamera"
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[1] = latitude_ref
    gps_ifd[2] = tuple(Fraction(str(x)) for x in latitude)
    gps_ifd[3] = longitude_ref
    gps_ifd[4] = tuple(Fraction(str(x)) for x in longitude)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


