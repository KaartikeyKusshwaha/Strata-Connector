"""Path security utilities for the Strata Connector.

Validates that all input/output paths are absolute, do not contain
traversal sequences, and stay within expected boundaries.
"""
from __future__ import annotations

import os
import re


class PathSecurityError(Exception):
    """Raised when a path fails security validation."""
    pass


# Patterns that indicate path traversal attempts
_TRAVERSAL_PATTERNS = [
    "..",
    "~",
]

# Disallowed path components (case-insensitive on Windows)
_DISALLOWED_COMPONENTS = [
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4",
    "LPT1", "LPT2", "LPT3", "LPT4",
]


def validate_path(path: str) -> str:
    """Validates that a path is safe for use.

    Args:
        path: The path to validate.

    Returns:
        The normalized absolute path.

    Raises:
        PathSecurityError: If the path is invalid or unsafe.
    """
    if not path or not path.strip():
        raise PathSecurityError("Path must not be empty.")

    # Normalize the path
    normalized = os.path.normpath(path)

    # Must be absolute
    if not os.path.isabs(normalized):
        raise PathSecurityError(
            f"Path must be absolute. Got relative path: '{path}'"
        )

    # Check for traversal patterns in the original path
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part == "..":
            raise PathSecurityError(
                f"Path contains directory traversal: '{path}'"
            )

    # Check for null bytes
    if "\x00" in path:
        raise PathSecurityError("Path contains null bytes.")

    # Check for Windows reserved device names
    basename = os.path.basename(normalized).upper().split(".")[0]
    if basename in _DISALLOWED_COMPONENTS:
        raise PathSecurityError(
            f"Path contains reserved device name: '{basename}'"
        )

    return normalized


def validate_output_path(output_dir: str, filepath: str) -> str:
    """Validates that a file path stays within the output directory.

    Used to verify manifest output paths don't escape the result directory.

    Args:
        output_dir: The expected output root directory.
        filepath: The file path to validate.

    Returns:
        The normalized absolute path.

    Raises:
        PathSecurityError: If the path escapes the output directory.
    """
    abs_output = os.path.abspath(output_dir)
    abs_file = os.path.abspath(os.path.join(output_dir, filepath))

    if not abs_file.startswith(abs_output):
        raise PathSecurityError(
            f"Output path escapes result directory: '{filepath}'"
        )

    return abs_file
