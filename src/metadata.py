"""Metadata extraction, normalization, and privacy suppression.

Per architecture.md and rules.md:
- Extract EXIF metadata safely using Pillow's built-in EXIF parser.
- Distinguish absent metadata from extraction failure. Missing metadata is NOT a manipulation signal.
- Suppress exact GPS coordinates by default to preserve privacy.
- Convert all values (including IFDRational, tuples, bytes) to JSON-serializable types.
- Editing software tags are treated as exploratory review cues, never definitive forgery verdicts.
"""

import io
from typing import Any, Dict, List, Optional
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import GPSTAGS, IFD, TAGS

from src.config import METADATA_NOTICE
from src.exceptions import MetadataExtractionError
from src.models import MethodResult, MethodStatus

# Known image manipulation/editing software keywords for exploratory review cues
KNOWN_EDITORS = (
    "photoshop",
    "gimp",
    "lightroom",
    "paint.net",
    "canva",
    "snapseed",
    "pixlr",
    "affinity",
    "corel",
    "pixelmator",
)

# GPS tags to suppress when privacy protection is active
GPS_SENSITIVE_TAGS = {
    "GPSLatitude",
    "GPSLongitude",
    "GPSAltitude",
    "GPSDestLatitude",
    "GPSDestLongitude",
    "GPSPosition",
}


def _normalize_value(val: Any) -> Any:
    """Recursively convert Pillow/EXIF types to strictly JSON-serializable types."""
    if val is None:
        return None

    if isinstance(val, (bool, int, str)):
        return val

    if isinstance(val, float):
        # Ensure finite floats
        return val if (val == val and abs(val) != float("inf")) else 0.0

    if isinstance(val, bytes):
        try:
            decoded = val.decode("utf-8", errors="replace").rstrip("\x00").strip()
            return decoded if decoded else val.hex()
        except Exception:
            return val.hex()

    # IFDRational or objects with numerator and denominator
    if hasattr(val, "numerator") and hasattr(val, "denominator"):
        num, den = val.numerator, val.denominator
        if den == 0:
            return 0.0
        return round(float(num / den), 6)

    if isinstance(val, (list, tuple, set)):
        return [_normalize_value(item) for item in val]

    if isinstance(val, dict):
        return {str(k): _normalize_value(v) for k, v in val.items()}

    return str(val).strip()


def extract_metadata(data: bytes, suppress_gps: bool = True) -> MethodResult:
    """Extract and normalize EXIF metadata from raw image bytes.

    Args:
        data: Raw image bytes.
        suppress_gps: Whether to suppress exact GPS coordinates (default: True).

    Returns:
        MethodResult containing structured observations, warnings, and limitations.

    Raises:
        MetadataExtractionError: Only if critical parsing failure occurs.
    """
    raw_tags: Dict[str, Any] = {}
    warnings: List[str] = []
    limitations: List[str] = [
        METADATA_NOTICE,
        "The absence of metadata is common across social media platforms and does not indicate tampering.",
        "EXIF metadata can be easily modified, inserted, or stripped using standard photo tools.",
    ]
    parameters: Dict[str, Any] = {"gps_suppressed": suppress_gps}

    try:
        with Image.open(io.BytesIO(data)) as im:
            exif = im.getexif()

            has_exif = bool(exif and len(exif) > 0)
            gps_present = False
            make: Optional[str] = None
            model: Optional[str] = None
            software: Optional[str] = None
            datetime_original: Optional[str] = None
            orientation: Optional[Any] = None
            iso: Optional[int] = None
            exposure_time: Optional[str] = None
            f_number: Optional[str] = None
            focal_length: Optional[str] = None

            def _to_float(v: Any) -> Optional[float]:
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    try:
                        n, d = float(v[0]), float(v[1])
                        return n / d if d != 0 else 0.0
                    except Exception:
                        return None
                try:
                    return float(v)
                except Exception:
                    return None

            def _parse_tag(name: str, val: Any) -> None:
                nonlocal make, model, software, datetime_original, orientation
                nonlocal iso, exposure_time, f_number, focal_length
                if name == "Make":
                    make = str(val)
                elif name == "Model":
                    model = str(val)
                elif name == "Software":
                    software = str(val)
                elif name in ("DateTimeOriginal", "DateTime"):
                    if not datetime_original or name == "DateTimeOriginal":
                        datetime_original = str(val)
                elif name == "Orientation":
                    orientation = val
                elif name in ("ISOSpeedRatings", "PhotographicSensitivity", "ISO") and iso is None:
                    try:
                        iso = int(val[0] if isinstance(val, (list, tuple)) else val)
                    except Exception:
                        pass
                elif name == "ExposureTime" and exposure_time is None:
                    f_val = _to_float(val)
                    if f_val is not None and f_val > 0:
                        if f_val < 1:
                            exposure_time = f"1/{int(round(1.0 / f_val))}s"
                        else:
                            exposure_time = f"{f_val:.4g}s"
                    else:
                        exposure_time = str(val)
                elif name == "FNumber" and f_number is None:
                    f_val = _to_float(val)
                    if f_val is not None:
                        f_number = f"f/{f_val:.1f}"
                    else:
                        f_number = str(val)
                elif name == "FocalLength" and focal_length is None:
                    f_val = _to_float(val)
                    if f_val is not None:
                        focal_length = f"{f_val:.1f} mm"
                    else:
                        focal_length = str(val)

            if has_exif:
                # 1. Root EXIF tags
                for tag_id, value in exif.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    norm_val = _normalize_value(value)
                    raw_tags[tag_name] = norm_val
                    _parse_tag(tag_name, norm_val)

                # 2. Exif sub-IFD (DateTimeOriginal, LensModel, exposure settings, etc.)
                try:
                    exif_ifd = exif.get_ifd(IFD.Exif)
                    for sub_tag_id, sub_value in exif_ifd.items():
                        sub_tag_name = TAGS.get(sub_tag_id, str(sub_tag_id))
                        norm_sub_val = _normalize_value(sub_value)
                        raw_tags[sub_tag_name] = norm_sub_val
                        _parse_tag(sub_tag_name, norm_sub_val)
                except Exception:
                    # Non-fatal if sub-IFD is malformed
                    pass

                # 3. GPS sub-IFD
                try:
                    gps_ifd = exif.get_ifd(IFD.GPSInfo)
                    if gps_ifd and len(gps_ifd) > 0:
                        gps_present = True
                        for gps_tag_id, gps_val in gps_ifd.items():
                            gps_tag_name = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                            if not suppress_gps or gps_tag_name not in GPS_SENSITIVE_TAGS:
                                raw_tags[f"GPS_{gps_tag_name}"] = _normalize_value(gps_val)
                except Exception:
                    pass

            # Check top-level GPS tag if not yet detected
            if not gps_present and exif is not None and (IFD.GPSInfo in exif or 34853 in exif):
                gps_present = True

            # Privacy handling for GPS
            gps_coordinates: Optional[Dict[str, Any]] = None
            if gps_present and suppress_gps:
                # Ensure no sensitive GPS tags leaked into raw_tags
                raw_tags = {
                    k: v
                    for k, v in raw_tags.items()
                    if not any(k.endswith(sens) or k == sens for sens in GPS_SENSITIVE_TAGS)
                }
                warnings.append(
                    "Geotagging metadata detected. Exact GPS coordinates have been suppressed to protect privacy."
                )
            elif gps_present and not suppress_gps:
                warnings.append(
                    "Geotagging metadata detected. GPS coordinates have been unsuppressed per examiner request."
                )
                try:
                    gps_ifd = exif.get_ifd(IFD.GPSInfo)
                    lat_val = gps_ifd.get(2)
                    lat_ref = str(gps_ifd.get(1, "N")).strip().upper()
                    lon_val = gps_ifd.get(4)
                    lon_ref = str(gps_ifd.get(3, "E")).strip().upper()

                    def _dms_to_deg(dms: Any) -> float:
                        if isinstance(dms, (list, tuple)) and len(dms) >= 3:
                            d = _to_float(dms[0]) or 0.0
                            m = _to_float(dms[1]) or 0.0
                            s = _to_float(dms[2]) or 0.0
                            return d + (m / 60.0) + (s / 3600.0)
                        return float(dms)

                    if lat_val and lon_val:
                        lat_deg = _dms_to_deg(lat_val)
                        if lat_ref == "S":
                            lat_deg = -lat_deg
                        lon_deg = _dms_to_deg(lon_val)
                        if lon_ref == "W":
                            lon_deg = -lon_deg
                        gps_coordinates = {
                            "latitude": round(lat_deg, 6),
                            "longitude": round(lon_deg, 6),
                            "formatted": f"{abs(lat_deg):.4f}° {lat_ref}, {abs(lon_deg):.4f}° {lon_ref}",
                        }
                except Exception:
                    pass

            # Check software tag for review cues
            if software:
                soft_lower = software.lower()
                for editor in KNOWN_EDITORS:
                    if editor in soft_lower:
                        warnings.append(
                            f"Software tag indicates an editor ('{software}') was recorded. "
                            f"This is a review cue regarding processing history, not proof of forgery."
                        )
                        break

            # Formulate clear, non-verdict summary
            if has_exif:
                device_info = f" ({make} {model})".strip() if (make or model) else ""
                summary = f"EXIF metadata present{device_info} with {len(raw_tags)} tag(s) extracted."
            else:
                summary = "No EXIF metadata found. Many cameras, web services, and apps routinely strip metadata."

            observations: Dict[str, Any] = {
                "has_exif": has_exif,
                "make": make,
                "model": model,
                "software": software,
                "datetime_original": datetime_original,
                "orientation": orientation,
                "iso": iso,
                "exposure_time": exposure_time,
                "f_number": f_number,
                "focal_length": focal_length,
                "gps_present": gps_present,
                "gps_coordinates": gps_coordinates,
                "raw_tags": raw_tags,
            }

            return MethodResult(
                method_id="metadata",
                status=MethodStatus.COMPLETED,
                summary=summary,
                observations=observations,
                warnings=warnings,
                limitations=limitations,
                parameters=parameters,
            )

    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        return MethodResult(
            method_id="metadata",
            status=MethodStatus.FAILED,
            summary=f"Could not read metadata: {e}",
            observations={"has_exif": False, "error": str(e)},
            warnings=["Metadata parser failed to read image container."],
            limitations=limitations,
            parameters=parameters,
        )
