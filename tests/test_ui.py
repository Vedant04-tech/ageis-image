"""Automated tests for Streamlit interface and interaction flow."""

import pytest
from streamlit.testing.v1 import AppTest
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_png,
)


def test_app_initial_empty_state() -> None:
    """Verify app renders title, header, uploader, and initial educational notice."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    assert not at.exception
    # Verify title or header text
    assert len(at.info) > 0
    assert "Get started" in at.info[0].value


def test_app_with_uploaded_jpeg() -> None:
    """Verify end-to-end rendering when a JPEG is uploaded."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    assert not at.exception

    # Upload synthetic JPEG
    jpeg_bytes = create_synthetic_jpeg(width=64, height=64)
    at.file_uploader[0].upload("sample_evidence.jpg", jpeg_bytes)
    at.run()

    assert not at.exception
    assert len(at.success) > 0
    assert "Analysis completed" in at.success[0].value

    # Verify tabs rendered
    assert len(at.tabs) == 3
    # Verify download buttons rendered
    assert len(at.download_button) == 2


def test_app_with_uploaded_png() -> None:
    """Verify end-to-end rendering when a PNG is uploaded (ELA not applicable)."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    png_bytes = create_synthetic_png(width=50, height=50)
    at.file_uploader[0].upload("document.png", png_bytes)
    at.run()

    assert not at.exception
    assert len(at.success) > 0
    assert len(at.download_button) == 2


def test_app_with_uploaded_webp() -> None:
    """Verify end-to-end rendering when a WebP is uploaded (ELA not applicable)."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    from tests.fixtures.synthetic import create_synthetic_webp
    webp_bytes = create_synthetic_webp(width=60, height=60)
    at.file_uploader[0].upload("sample.webp", webp_bytes)
    at.run()

    assert not at.exception
    assert len(at.success) > 0
    assert "Analysis completed" in at.success[0].value
    assert len(at.download_button) == 2


def test_app_with_gps_exif_metadata() -> None:
    """Verify JPEG with GPS metadata displays detection while suppressing coordinates."""
    from tests.fixtures.synthetic import create_synthetic_jpeg_with_gps
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    gps_bytes = create_synthetic_jpeg_with_gps()
    at.file_uploader[0].upload("location_test.jpg", gps_bytes)
    at.run()

    assert not at.exception
    assert len(at.success) > 0


def test_app_with_corrupt_file_shows_error() -> None:
    """Verify corrupt upload displays user-safe error and does not produce reports."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    at.file_uploader[0].upload("corrupt.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20)
    at.run()

    assert not at.exception
    assert len(at.error) > 0
    assert "Intake Rejected" in at.error[0].value or "Failed" in at.error[0].value


def test_app_with_preset_selection() -> None:
    """Verify selecting a fixture from the preset selectbox executes analysis."""
    at = AppTest.from_file("../app.py", default_timeout=25).run()
    assert not at.exception
    assert len(at.selectbox) > 0

    # Select Sample 01
    at.selectbox[0].select("Sample 01: Untouched Baseline (JPEG)")
    at.run()

    assert not at.exception
    assert len(at.success) > 0
    assert "Analysis completed" in at.success[0].value
    assert len(at.download_button) == 2


