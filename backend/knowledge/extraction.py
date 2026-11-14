from __future__ import annotations

from dataclasses import dataclass


class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_failed"):
        super().__init__(message)
        self.code = code


@dataclass
class ExtractedPage:
    page_number: int
    text: str


def extract_pages(content: bytes, document_type: str) -> list[ExtractedPage]:
    if document_type == "txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError("TXT documents must be valid UTF-8.", "invalid_txt") from exc
        return [ExtractedPage(page_number=1, text=text)]
    if document_type == "pdf":
        return _extract_pdf(content)
    raise ExtractionError(f"Unsupported document type: {document_type}", "unsupported_type")


def _extract_pdf(content: bytes) -> list[ExtractedPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError("pypdf is not installed.", "missing_dependency") from exc

    try:
        reader = PdfReader(io_bytes(content))
    except Exception as exc:  # noqa: BLE001 - invalid PDFs take many forms
        raise ExtractionError("The PDF could not be read.", "invalid_pdf") from exc

    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(ExtractedPage(page_number=index, text=text))

    combined = "\n".join(page.text.strip() for page in pages if page.text.strip())
    if not combined.strip():
        raise ExtractionError(
            "No extractable text was found. Scanned PDFs are not supported because OCR is not implemented.",
            "empty_pdf_text",
        )
    return pages


def io_bytes(content: bytes):
    from io import BytesIO

    return BytesIO(content)
