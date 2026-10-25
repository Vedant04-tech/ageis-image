"""AegisImage system configuration and constants.

All constants are explicit and align with architecture.md and prd.md.
"""

from typing import Final, Tuple

APP_NAME: Final[str] = "AegisImage"
APP_VERSION: Final[str] = "0.1.0"
SCHEMA_VERSION: Final[str] = "1.0"

# Intake constraints
MAX_UPLOAD_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MiB
MAX_IMAGE_PIXELS: Final[int] = 40_000_000  # 40 MP
SUPPORTED_FORMATS: Final[Tuple[str, ...]] = ("JPEG", "PNG", "WEBP")

# JPEG ELA defaults
DEFAULT_ELA_QUALITY: Final[int] = 90
DEFAULT_ELA_AMPLIFICATION: Final[int] = 10

# Image statistics
HISTOGRAM_BINS: Final[int] = 256

# Standard notices and disclaimers (per rules.md and design.md)
OVERALL_NOTICE: Final[str] = (
    "AegisImage is an educational digital image forensics aid. "
    "Findings are exploratory observations and do not constitute proof of authenticity or tampering."
)

HASH_NOTICE: Final[str] = (
    "SHA-256 digest calculated from the exact original uploaded file bytes before any decoding or transformation."
)

METADATA_NOTICE: Final[str] = (
    "Metadata may be absent, stripped, modified, or forged. "
    "The absence of metadata is not proof of tampering."
)

ELA_NOTICE: Final[str] = (
    "Error Level Analysis (ELA) is an exploratory visualization for JPEG images. "
    "Variations arise from compression history, high-frequency textures, and surface contrast. "
    "It does not provide a definitive tampering verdict."
)
