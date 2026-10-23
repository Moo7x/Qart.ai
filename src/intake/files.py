"""Turn an uploaded CV file (PDF, DOCX or plain text) into text. Nothing is written to disk."""

import io

MAX_UPLOAD_BYTES = 2_000_000  # a CV is a few pages; larger files are refused
TEXT_TYPES = (".txt", ".md")


class UnsupportedFileError(ValueError):
    """The file type cannot be read, or the file is too large."""


def read_cv(filename: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise UnsupportedFileError("the file is larger than 2 MB")
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document

        document = Document(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs)
    if name.endswith(TEXT_TYPES):
        return content.decode("utf-8", errors="replace")
    raise UnsupportedFileError("use a PDF, DOCX or text file")
