"""Unit tests for evidence hashing and SHA-256 integrity."""

import hashlib
from src.integrity import compute_sha256


def test_sha256_known_vectors() -> None:
    """Verify SHA-256 calculation against known NIST standard test vectors."""
    # Vector 1: Empty string
    assert (
        compute_sha256(b"")
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    # Vector 2: "hello world"
    assert (
        compute_sha256(b"hello world")
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )

    # Vector 3: Arbitrary forensic test bytes
    test_bytes = b"AegisImage forensics test vector 2026"
    expected = hashlib.sha256(test_bytes).hexdigest().lower()
    assert compute_sha256(test_bytes) == expected


def test_sha256_format_and_casing() -> None:
    """Verify digest is exactly 64 characters and strictly lowercase hex."""
    digest = compute_sha256(b"evidence payload")
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


def test_sha256_source_immutability() -> None:
    """Verify hashing operation does not mutate or consume original bytearray/bytes."""
    raw = bytearray(b"\x00\x01\x02\x03\x04\xff")
    snapshot = bytes(raw)
    digest = compute_sha256(raw)
    assert bytes(raw) == snapshot
    assert digest == hashlib.sha256(snapshot).hexdigest()


def test_compute_integrity_hashes_multi_algorithm() -> None:
    """Verify compute_integrity_hashes computes accurate SHA-256, SHA-1, and MD5 digests."""
    from src.integrity import compute_integrity_hashes

    sample_data = b"Forensic evidence sample bytes 2026"
    hashes = compute_integrity_hashes(sample_data)

    assert "sha256" in hashes
    assert "sha1" in hashes
    assert "md5" in hashes

    assert hashes["sha256"] == hashlib.sha256(sample_data).hexdigest().lower()
    assert hashes["sha1"] == hashlib.sha1(sample_data).hexdigest().lower()
    assert hashes["md5"] == hashlib.md5(sample_data).hexdigest().lower()

