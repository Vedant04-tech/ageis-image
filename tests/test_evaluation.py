"""Integration test verifying full evaluation run across labelled fixtures."""

from pathlib import Path
from scripts.run_evaluation import run_evaluation


def test_full_evaluation_suite() -> None:
    """Verify that all manifest samples evaluate cleanly with zero unexpected failures."""
    eval_output = run_evaluation()
    summary = eval_output["summary"]

    assert summary["total"] >= 10
    assert summary["failed_unexpectedly"] == 0
    assert summary["intake_accepted"] >= 7
    assert summary["intake_rejected_as_expected"] >= 3
    assert summary["sha256_exact_matches"] == summary["intake_accepted"]
    assert summary["gps_properly_suppressed"] == summary["intake_accepted"]
    assert summary["ela_jpeg_correct"] >= 5
    assert summary["ela_non_jpeg_not_applicable"] >= 2
    assert summary["pdf_exports_successful"] == summary["intake_accepted"]
    assert summary["json_exports_successful"] == summary["intake_accepted"]
