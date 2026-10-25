"""AegisImage domain-specific exceptions.

Defined at explicit module boundaries with user-safe messaging.
"""


class ForensicError(Exception):
    """Base exception for all domain-specific forensic errors."""

    def __init__(self, message: str, user_safe: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.user_safe = user_safe


class UnsupportedFormatError(ForensicError):
    """Raised when an uploaded file format is not supported."""


class FileTooLargeError(ForensicError):
    """Raised when an uploaded file exceeds the configured byte size limit."""


class ImageDimensionsError(ForensicError):
    """Raised when image pixel count exceeds the safe decoding boundary."""


class AnimatedImageError(ForensicError):
    """Raised when an uploaded image contains multiple frames or animation."""


class ImageDecodeError(ForensicError):
    """Raised when an uploaded file cannot be decoded safely."""


class MetadataExtractionError(ForensicError):
    """Raised when metadata extraction completely fails (distinct from absent metadata)."""


class AnalysisMethodError(ForensicError):
    """Raised when an analysis method fails execution."""


class ReportGenerationError(ForensicError):
    """Raised when report generation (PDF or JSON) fails."""
