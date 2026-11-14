from __future__ import annotations

import re
from dataclasses import dataclass

from knowledge.extraction import ExtractedPage

HEADING_RE = re.compile(r"^(#{1,6}\s+|[A-Z][A-Z0-9 ]{8,}|[^\n:]{3,40}:)\s*$")


@dataclass
class PreparedChunk:
    text: str
    index: int
    page_number: int | None
    section_heading: str
    metadata: dict


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_pages(
    pages: list[ExtractedPage],
    *,
    max_chars: int = 800,
    overlap: int = 80,
) -> list[PreparedChunk]:
    chunks: list[PreparedChunk] = []
    heading = ""
    for page in pages:
        cleaned = normalize_text(page.text)
        if not cleaned:
            continue
        if len(cleaned) <= max_chars:
            chunks.append(
                PreparedChunk(
                    text=cleaned,
                    index=len(chunks),
                    page_number=page.page_number,
                    section_heading=heading,
                    metadata={"char_count": len(cleaned)},
                )
            )
            continue
        for paragraph in _split_paragraphs(cleaned):
            maybe_heading = paragraph.strip()
            if _looks_like_heading(maybe_heading):
                heading = maybe_heading[:255]
            for piece in _window(paragraph, max_chars, overlap):
                chunks.append(
                    PreparedChunk(
                        text=piece,
                        index=len(chunks),
                        page_number=page.page_number,
                        section_heading=heading,
                        metadata={"char_count": len(piece)},
                    )
                )
    return chunks


def _looks_like_heading(text: str) -> bool:
    if len(text) > 80 or len(text) < 3:
        return False
    return bool(HEADING_RE.match(text)) or text.endswith(":")


def _split_paragraphs(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    return parts or [text]


def _window(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        pieces.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]
