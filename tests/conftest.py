"""Pytest configuration and shared fixtures."""

import pytest
from tests.fixtures.synthetic import (
    create_corrupt_image_bytes,
    create_synthetic_animated_gif,
    create_synthetic_jpeg,
    create_synthetic_png,
    create_synthetic_webp,
)


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Provide valid in-memory JPEG bytes."""
    return create_synthetic_jpeg(width=64, height=64)


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Provide valid in-memory PNG bytes."""
    return create_synthetic_png(width=64, height=64)


@pytest.fixture
def sample_webp_bytes() -> bytes:
    """Provide valid in-memory WebP bytes."""
    return create_synthetic_webp(width=64, height=64)


@pytest.fixture
def animated_gif_bytes() -> bytes:
    """Provide valid in-memory multi-frame GIF bytes."""
    return create_synthetic_animated_gif()


@pytest.fixture
def corrupt_bytes() -> bytes:
    """Provide corrupted image bytes."""
    return create_corrupt_image_bytes()
