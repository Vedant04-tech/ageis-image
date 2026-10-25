"""Unit tests for metadata extraction, normalization, and privacy suppression."""

import json
import pytest
from src.metadata import extract_metadata
from src.models import MethodResult, MethodStatus
from tests.fixtures.synthetic import (
    create_synthetic_jpeg,
    create_synthetic_jpeg_with_exif,
    create_synthetic_jpeg_with_gps,
    create_synthetic_png,
    create_synthetic_webp,
)


def test_metadata_absent_returns_completed_status() -> None:
    """Images with absent EXIF return COMPLETED status without tampering warnings."""
    clean_jpeg = create_synthetic_jpeg()
    result = extract_metadata(clean_jpeg)

    assert isinstance(result, MethodResult)
    assert result.method_id == "metadata"
    assert result.status == MethodStatus.COMPLETED
    assert result.observations["has_exif"] is False
    assert "No EXIF" in result.summary or "not found" in result.summary.lower()

    # Rule check: Missing metadata must NOT be flagged as manipulation or forgery
    for warning in result.warnings:
        assert "tamper" not in warning.lower()
        assert "forg" not in warning.lower()
        assert "fake" not in warning.lower()

    assert len(result.limitations) > 0


def test_metadata_present_extracts_known_fields() -> None:
    """Verify standard camera, capture time, and software tags are extracted."""
    jpeg_with_exif = create_synthetic_jpeg_with_exif(
        make="NikonTest",
        model="D850-Forensics",
        software="Nikon Capture NX",
        date_time="2026:10:23 15:45:00",
    )
    result = extract_metadata(jpeg_with_exif)

    assert result.status == MethodStatus.COMPLETED
    obs = result.observations
    assert obs["has_exif"] is True
    assert obs["make"] == "NikonTest"
    assert obs["model"] == "D850-Forensics"
    assert obs["software"] == "Nikon Capture NX"
    assert obs["datetime_original"] == "2026:10:23 15:45:00"
    assert "raw_tags" in obs
    assert obs["raw_tags"]["Make"] == "NikonTest"


def test_gps_presence_and_suppression() -> None:
    """Verify GPS presence is detected but exact coordinates are suppressed by default."""
    jpeg_with_gps = create_synthetic_jpeg_with_gps()

    # Default extraction (GPS suppressed)
    result = extract_metadata(jpeg_with_gps, suppress_gps=True)

    assert result.status == MethodStatus.COMPLETED
    obs = result.observations
    assert obs["gps_present"] is True

    # Exact coordinates must be None/suppressed in observations
    assert obs.get("gps_coordinates") is None

    # Exact GPS coordinate sub-tags must be excluded from raw_tags
    raw = obs.get("raw_tags", {})
    assert "GPSLatitude" not in raw
    assert "GPSLongitude" not in raw
    assert "GPSDestLatitude" not in raw

    # Warning must explain privacy suppression
    assert any("suppressed" in w.lower() for w in result.warnings)
    assert result.parameters.get("gps_suppressed") is True


def test_software_tag_review_cue_not_forgery_verdict() -> None:
    """Editing software tag generates an exploratory review cue, not a forgery accusation."""
    jpeg_photoshop = create_synthetic_jpeg_with_exif(software="Adobe Photoshop CC 2024")
    result = extract_metadata(jpeg_photoshop)

    assert result.observations["software"] == "Adobe Photoshop CC 2024"
    # Must have a cautionary review warning
    assert any("Adobe Photoshop" in w for w in result.warnings)
    # Must NOT claim image is fake or forged
    for warning in result.warnings:
        assert "forged" not in warning.lower()
        assert "fake" not in warning.lower()
        assert "tampered" not in warning.lower()


def test_metadata_json_serializability() -> None:
    """Verify MethodResult dictionary is strictly JSON serializable."""
    jpeg_with_exif = create_synthetic_jpeg_with_exif()
    result = extract_metadata(jpeg_with_exif)

    res_dict = result.to_dict()
    # Must serialize without TypeError
    json_str = json.dumps(res_dict)
    assert isinstance(json_str, str)

    loaded = json.loads(json_str)
    assert loaded["method_id"] == "metadata"
    assert loaded["status"] == "completed"


def test_metadata_png_and_webp_support() -> None:
    """PNG and WebP images process metadata cleanly."""
    png_bytes = create_synthetic_png()
    webp_bytes = create_synthetic_webp()

    res_png = extract_metadata(png_bytes)
    assert res_png.status == MethodStatus.COMPLETED
    assert res_png.method_id == "metadata"

    res_webp = extract_metadata(webp_bytes)
    assert res_webp.status == MethodStatus.COMPLETED
    assert res_webp.method_id == "metadata"


def test_metadata_exposure_tags() -> None:
    """Verify photographic exposure parameters are extracted when present."""
    from PIL import Image
    from PIL.ExifTags import IFD
    import io

    img = Image.new("RGB", (100, 100), color=(150, 150, 150))
    exif = Image.Exif()
    exif[271] = "CanonTest"
    exif[272] = "EOS Forensics"
    exif_ifd = exif.get_ifd(IFD.Exif)
    exif_ifd[34855] = 400  # ISO Speed Ratings
    exif_ifd[33434] = (1, 125)  # ExposureTime = 1/125s (IFDRational numerator/denominator)
    exif_ifd[33437] = (28, 10)  # FNumber = 2.8
    exif_ifd[37386] = (50, 1)   # FocalLength = 50mm

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    data = buf.getvalue()

    result = extract_metadata(data)
    assert result.status == MethodStatus.COMPLETED
    obs = result.observations
    assert obs.get("iso") == 400
    assert obs.get("f_number") == "f/2.8" or obs.get("f_number") == 2.8
    assert "1/125" in str(obs.get("exposure_time"))
    assert "50" in str(obs.get("focal_length"))

