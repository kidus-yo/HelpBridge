"""Shared language codes for HelpBridge.

Not every AI or speech provider supports all of these equally. Callers must
treat unsupported provider languages as a documented limitation, not a runtime
guarantee.
"""

from typing import Final

LANGUAGE_CHOICES: Final[list[tuple[str, str]]] = [
    ("en", "English"),
    ("am", "Amharic"),
    ("om", "Afaan Oromo"),
    ("so", "Somali"),
    ("ti", "Tigrinya"),
    ("aa", "Afar"),
]

SUPPORTED_LANGUAGE_CODES: Final[frozenset[str]] = frozenset(code for code, _ in LANGUAGE_CHOICES)
SUPPORTED_TUTOR_LANGUAGE_CODES: Final[frozenset[str]] = frozenset({"en", "am"})


def is_supported_language(code: str | None) -> bool:
    return bool(code) and code in SUPPORTED_LANGUAGE_CODES


def is_supported_tutor_language(code: str | None) -> bool:
    return bool(code) and code in SUPPORTED_TUTOR_LANGUAGE_CODES
