from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_failed"):
        super().__init__(message)
        self.code = code


@dataclass
class ExtractedPage:
    page_number: int | None
    text: str
    section_heading: str = ""


def extract_pages(content: bytes, document_type: str) -> list[ExtractedPage]:
    if document_type == "txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError("TXT documents must be valid UTF-8.", "invalid_txt") from exc
        return [ExtractedPage(page_number=1, text=text)]
    if document_type == "pdf":
        return _extract_pdf(content)
    if document_type == "docx":
        return _extract_docx(content)
    raise ExtractionError(f"Unsupported document type: {document_type}", "unsupported_type")


def _extract_docx(content: bytes) -> list[ExtractedPage]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    document_path = "word/document.xml"
    try:
        with ZipFile(BytesIO(content)) as archive:
            info = archive.getinfo(document_path)
            if info.file_size > 50 * 1024 * 1024:
                raise ExtractionError("DOCX document content is too large.", "docx_too_large")
            root = ElementTree.fromstring(archive.read(document_path))
    except ExtractionError:
        raise
    except (BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ExtractionError("The DOCX could not be read.", "invalid_docx") from exc

    pages = []
    heading = ""
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ).strip()
        if not text:
            continue
        style = paragraph.find("./w:pPr/w:pStyle", namespace)
        style_id = style.get(f"{{{namespace['w']}}}val", "") if style is not None else ""
        if style_id.startswith(("Heading", "Title", "Subtitle")):
            heading = text[:255]
            continue
        pages.append(ExtractedPage(page_number=None, text=text, section_heading=heading))

    if not pages:
        raise ExtractionError("No extractable text was found in the DOCX.", "empty_docx")
    return pages


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
