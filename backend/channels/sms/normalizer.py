"""
Ethiopian Phone Number Normalizer.
Complies with Hackathon Guide Section 9 (Built for Ethiopia):
'Phone numbers: accept 09..., 07... and +251..., and store one format.'
"""

import re
from typing import Optional


def normalize_ethiopian_phone(raw_phone: str) -> str:
    """
    Normalizes an Ethiopian phone number to international E.164 format (+251...).
    Accepts:
      - 09XXXXXXXX -> +2519XXXXXXXX
      - 07XXXXXXXX -> +2517XXXXXXXX
      - 2519XXXXXXXX -> +2519XXXXXXXX
      - +2519XXXXXXXX -> +2519XXXXXXXX
    """
    if not raw_phone:
        raise ValueError("Phone number cannot be empty.")

    # Strip whitespace, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', str(raw_phone))

    if cleaned.startswith('+251'):
        digits = cleaned[4:]
    elif cleaned.startswith('251'):
        digits = cleaned[3:]
    elif cleaned.startswith('0'):
        digits = cleaned[1:]
    else:
        digits = cleaned

    # Must start with 9 or 7 and have 9 digits total in national format
    if not (digits.startswith('9') or digits.startswith('7')):
        raise ValueError(f"Invalid Ethiopian phone prefix. Must start with 09 or 07 (got {raw_phone}).")

    if len(digits) != 9:
        raise ValueError(f"Invalid phone number length. Expected 9 digits after country code (got {len(digits)}).")

    return f"+251{digits}"


def is_valid_ethiopian_phone(raw_phone: str) -> bool:
    """Utility check for validation."""
    try:
        normalize_ethiopian_phone(raw_phone)
        return True
    except (ValueError, TypeError):
        return False
