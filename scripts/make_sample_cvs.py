"""Write the synthetic sample CVs as Word files, for uploading in a demo like a real CV.

    .venv/Scripts/python.exe scripts/make_sample_cvs.py

Reads data/samples/<name>.txt and writes data/samples/cv_files/<name>.docx: the first line as the
name, section titles (Profile, Experience, ...) as headings and "- " lines as bullets. The people
are synthetic; the files say so, as the text versions do.
"""

import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import REPO_ROOT  # noqa: E402

SAMPLES = REPO_ROOT / "data" / "samples"
OUT = SAMPLES / "cv_files"
SECTIONS = {"Profile", "Experience", "Education", "Internship", "Skills", "Interests"}


def write(name: str) -> Path:
    lines = (SAMPLES / f"{name}.txt").read_text(encoding="utf-8").splitlines()
    doc = Document()
    doc.add_heading(lines[0], level=0)
    for line in lines[1:]:
        text = line.strip()
        if not text:
            continue
        if text in SECTIONS:
            doc.add_heading(text, level=1)
        elif text.startswith("- "):
            doc.add_paragraph(text[2:], style="List Bullet")
        else:
            doc.add_paragraph(text)
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.docx"
    doc.save(str(path))
    return path


if __name__ == "__main__":
    for sample in ("nur", "kavitha", "hafiz", "mei"):
        print(write(sample).relative_to(REPO_ROOT))
