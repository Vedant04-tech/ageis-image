"""Generate synthetic evaluation dataset and manifest for AegisImage Phase 6.

Creates small, sanitized, license-clean, synthetic evaluation fixtures in sample_images/
and writes sample_images/manifest.json. No personal photos or private metadata are used.
"""

from fractions import Fraction
import io
import json
from pathlib import Path
from PIL import ExifTags, Image, ImageDraw

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "sample_images"


def generate_pattern_image(width: int = 240, height: int = 180) -> Image.Image:
    """Generate a clean synthetic test card image with geometric shapes and gradients."""
    img = Image.new("RGB", (width, height), color=(230, 235, 240))
    draw = ImageDraw.Draw(img)

    # Gradient background stripes
    for y in range(height):
        r = int(180 + 50 * (y / height))
        g = int(200 + 40 * (1 - y / height))
        b = 220
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Geometric reference shapes
    draw.rectangle([20, 20, 90, 90], fill=(220, 50, 50), outline=(120, 20, 20), width=2)
    draw.ellipse([110, 30, 180, 100], fill=(40, 140, 60), outline=(20, 80, 30), width=2)
    draw.polygon([(160, 150), (200, 110), (220, 160)], fill=(30, 90, 180), outline=(10, 40, 100))
    return img


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    # 1. Untouched baseline JPEG
    img1 = generate_pattern_image()
    path1 = OUTPUT_DIR / "sample_01_untouched.jpg"
    img1.save(path1, format="JPEG", quality=95)
    manifest.append({
        "sample_id": "SMP-01",
        "filename": path1.name,
        "format": "JPEG",
        "category": "untouched_baseline",
        "operation": "Single high-quality compression (Q=95)",
        "ground_truth": "Authentic synthetic baseline, no splicing",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED (uniform compression error pattern)",
        "expected_metadata": "COMPLETED (no EXIF tags)",
    })

    # 2. Recompressed JPEG
    img2 = generate_pattern_image()
    buf = io.BytesIO()
    img2.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    recompressed_img = Image.open(buf)
    path2 = OUTPUT_DIR / "sample_02_recompressed.jpg"
    recompressed_img.save(path2, format="JPEG", quality=70)
    manifest.append({
        "sample_id": "SMP-02",
        "filename": path2.name,
        "format": "JPEG",
        "category": "recompressed",
        "operation": "Two-generation compression (Q=95 -> Q=70)",
        "ground_truth": "Resaved lower quality, global error increase",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED (elevated mean difference across whole frame)",
        "expected_metadata": "COMPLETED",
    })

    # 3. Tampered / Spliced JPEG
    img3 = generate_pattern_image()
    buf3 = io.BytesIO()
    img3.save(buf3, format="JPEG", quality=75)
    buf3.seek(0)
    base_tampered = Image.open(buf3).copy()
    # Splice an uncompressed high-frequency patch
    patch = Image.new("RGB", (60, 40), color=(255, 255, 0))
    p_draw = ImageDraw.Draw(patch)
    for x in range(0, 60, 6):
        p_draw.line([(x, 0), (x, 40)], fill=(0, 0, 0), width=2)
    base_tampered.paste(patch, (80, 80))
    path3 = OUTPUT_DIR / "sample_03_tampered_spliced.jpg"
    base_tampered.save(path3, format="JPEG", quality=92)
    manifest.append({
        "sample_id": "SMP-03",
        "filename": path3.name,
        "format": "JPEG",
        "category": "tampered_spliced",
        "operation": "Pasted high-frequency pattern into Q=75 base and resaved at Q=92",
        "ground_truth": "Manipulated / spliced composite region",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED (patch exhibits distinct error level response)",
        "expected_metadata": "COMPLETED",
    })

    # 4. JPEG with EXIF & Software Tag
    img4 = generate_pattern_image()
    exif4 = Image.Exif()
    exif4[271] = "AegisLabCam"
    exif4[272] = "Model-ForensicsX"
    exif4[305] = "Adobe Photoshop 2024 (Windows)"
    exif4[306] = "2026:10:23 12:00:00"
    exif_ifd = exif4.get_ifd(ExifTags.IFD.Exif)
    exif_ifd[36867] = "2026:10:23 12:00:00"
    path4 = OUTPUT_DIR / "sample_04_with_exif.jpg"
    img4.save(path4, format="JPEG", quality=90, exif=exif4)
    manifest.append({
        "sample_id": "SMP-04",
        "filename": path4.name,
        "format": "JPEG",
        "category": "with_metadata",
        "operation": "Added standard EXIF tags and editing software tag",
        "ground_truth": "Valid camera tags with Photoshop software signature",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED",
        "expected_metadata": "COMPLETED (extracts make, model, software review cue)",
    })

    # 5. JPEG with Geotagging / GPS Metadata
    img5 = generate_pattern_image()
    exif5 = Image.Exif()
    exif5[271] = "AegisGeoCam"
    gps_ifd = exif5.get_ifd(ExifTags.IFD.GPSInfo)
    gps_ifd[1] = "N"
    gps_ifd[2] = (Fraction(37, 1), Fraction(46, 1), Fraction(2974, 100))
    gps_ifd[3] = "W"
    gps_ifd[4] = (Fraction(122, 1), Fraction(25, 1), Fraction(983, 100))
    path5 = OUTPUT_DIR / "sample_05_with_gps.jpg"
    img5.save(path5, format="JPEG", quality=90, exif=exif5)
    manifest.append({
        "sample_id": "SMP-05",
        "filename": path5.name,
        "format": "JPEG",
        "category": "geotagged",
        "operation": "Injected GPS coordinates in IFD.GPSInfo",
        "ground_truth": "Contains geotagging metadata",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED",
        "expected_metadata": "COMPLETED (gps_present=True; exact coordinates suppressed)",
    })

    # 6. Metadata-Free JPEG
    img6 = generate_pattern_image()
    path6 = OUTPUT_DIR / "sample_06_metadata_free.jpg"
    img6.save(path6, format="JPEG", quality=90)
    manifest.append({
        "sample_id": "SMP-06",
        "filename": path6.name,
        "format": "JPEG",
        "category": "metadata_free",
        "operation": "Stripped container without EXIF or APP markers",
        "ground_truth": "No metadata tags in file container",
        "expected_intake": "ACCEPTED",
        "expected_ela": "COMPLETED",
        "expected_metadata": "COMPLETED (has_exif=False; neutral non-tampering interpretation)",
    })

    # 7. Clean PNG
    img7 = generate_pattern_image()
    path7 = OUTPUT_DIR / "sample_07_clean.png"
    img7.save(path7, format="PNG")
    manifest.append({
        "sample_id": "SMP-07",
        "filename": path7.name,
        "format": "PNG",
        "category": "lossless_png",
        "operation": "Lossless PNG encoding",
        "ground_truth": "Valid single-frame PNG",
        "expected_intake": "ACCEPTED",
        "expected_ela": "NOT_APPLICABLE (non-JPEG format safely rejected from ELA)",
        "expected_metadata": "COMPLETED",
    })

    # 8. Clean WebP
    img8 = generate_pattern_image()
    path8 = OUTPUT_DIR / "sample_08_clean.webp"
    img8.save(path8, format="WEBP", quality=85)
    manifest.append({
        "sample_id": "SMP-08",
        "filename": path8.name,
        "format": "WEBP",
        "category": "lossy_webp",
        "operation": "WebP still compression",
        "ground_truth": "Valid single-frame WebP",
        "expected_intake": "ACCEPTED",
        "expected_ela": "NOT_APPLICABLE (WebP block transform != JPEG DCT)",
        "expected_metadata": "COMPLETED",
    })

    # 9. Oversized payload (11 MiB)
    path9 = OUTPUT_DIR / "sample_09_oversized.bin"
    with open(path9, "wb") as f:
        # Write 11 MiB sparse/zeroes with JPEG header
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024))
    manifest.append({
        "sample_id": "SMP-09",
        "filename": path9.name,
        "format": "UNKNOWN/OVERSIZED",
        "category": "oversized_rejection",
        "operation": "Payload size = 11.0 MiB (> 10 MiB limit)",
        "ground_truth": "Boundary violation: exceeds maximum byte size",
        "expected_intake": "REJECTED (FileTooLargeError)",
        "expected_ela": "N/A",
        "expected_metadata": "N/A",
    })

    # 10. Corrupt payload
    path10 = OUTPUT_DIR / "sample_10_corrupt.jpg"
    with open(path10, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xde\xad\xbe\xef" * 8)
    manifest.append({
        "sample_id": "SMP-10",
        "filename": path10.name,
        "format": "CORRUPT_JPEG",
        "category": "malformed_rejection",
        "operation": "Truncated header with invalid entropy bitstream",
        "ground_truth": "Corrupt image bytes",
        "expected_intake": "REJECTED (CorruptImageError)",
        "expected_ela": "N/A",
        "expected_metadata": "N/A",
    })

    # 11. Animated Multi-frame GIF
    path11 = OUTPUT_DIR / "sample_11_animated.gif"
    f1 = Image.new("RGB", (64, 64), color=(255, 0, 0))
    f2 = Image.new("RGB", (64, 64), color=(0, 0, 255))
    f1.save(path11, format="GIF", save_all=True, append_images=[f2], duration=150, loop=0)
    manifest.append({
        "sample_id": "SMP-11",
        "filename": path11.name,
        "format": "GIF",
        "category": "animated_unsupported",
        "operation": "Multi-frame animated sequence in unsupported container",
        "ground_truth": "Unsupported animated format",
        "expected_intake": "REJECTED (UnsupportedFormatError or AnimatedImageError)",
        "expected_ela": "N/A",
        "expected_metadata": "N/A",
    })

    # Write manifest.json
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(manifest)} evaluation samples and manifest at {manifest_path}")


if __name__ == "__main__":
    main()
