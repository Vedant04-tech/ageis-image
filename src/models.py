"""Data models and serialization contracts for AegisImage.

All contracts match architecture.md Section 6.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.config import APP_NAME, APP_VERSION, OVERALL_NOTICE, SCHEMA_VERSION


class MethodStatus(str, Enum):
    """Execution status for an analysis method."""

    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"
    FAILED = "failed"


@dataclass(frozen=True)
class FileFacts:
    """Safe, verifiable facts about the original evidence bytes."""

    original_filename_display: str
    sha256: str
    size_bytes: int
    detected_format: str
    width: int
    height: int
    mode: str
    frame_count: int
    analysis_timestamp_utc: str
    sha1: str = ""
    md5: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class MethodResult:
    """Observation and metadata for a single forensic analysis method."""

    method_id: str
    status: MethodStatus
    summary: str
    observations: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    artifact_ids: List[str] = field(default_factory=list)
    artifact_bytes: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary with string status."""
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, MethodStatus) else str(self.status)
        data.pop("artifact_bytes", None)
        return data


@dataclass
class AnalysisReport:
    """Canonical analysis report structure for UI display and export."""

    file_facts: FileFacts
    generated_at_utc: str
    method_results: Dict[str, MethodResult] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    application_name: str = APP_NAME
    application_version: str = APP_VERSION
    overall_notice: str = OVERALL_NOTICE
    report_warnings: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire report to a JSON-serializable dictionary."""
        return {
            "schema_version": self.schema_version,
            "application_name": self.application_name,
            "application_version": self.application_version,
            "generated_at_utc": self.generated_at_utc,
            "overall_notice": self.overall_notice,
            "report_warnings": list(self.report_warnings),
            "references": list(self.references),
            "file_facts": self.file_facts.to_dict(),
            "method_results": {k: v.to_dict() for k, v in self.method_results.items()},
        }
