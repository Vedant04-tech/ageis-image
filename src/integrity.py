"""Evidence integrity and cryptographic identification.

Calculates SHA-256 over exact original bytes before any transformations.
Per rules.md: The hash identifies original bytes; it does NOT prove authenticity,
provenance, date of creation, or absence of prior edits.
"""

import hashlib
from typing import Dict, Union


def compute_sha256(data: Union[bytes, bytearray, memoryview]) -> str:
    """Compute 64-character lowercase hexadecimal SHA-256 digest over exact bytes.

    Args:
        data: Raw byte sequence of original uploaded file.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest().lower()


def compute_integrity_hashes(data: Union[bytes, bytearray, memoryview]) -> Dict[str, str]:
    """Compute multi-algorithm forensic cryptographic hashes over exact original bytes.

    Computes SHA-256 (standard), SHA-1, and MD5 (legacy reference) digests.

    Args:
        data: Raw byte sequence of original uploaded file.

    Returns:
        Dictionary with keys 'sha256', 'sha1', 'md5' mapped to lowercase hex digests.
    """
    h_sha256 = hashlib.sha256()
    h_sha1 = hashlib.sha1()
    h_md5 = hashlib.md5()

    h_sha256.update(data)
    h_sha1.update(data)
    h_md5.update(data)

    return {
        "sha256": h_sha256.hexdigest().lower(),
        "sha1": h_sha1.hexdigest().lower(),
        "md5": h_md5.hexdigest().lower(),
    }

