"""Write one named section of eval/RESULTS.md without touching the other sections."""

from pathlib import Path

RESULTS_PATH = Path(__file__).resolve().parent / "RESULTS.md"
HEADER = (
    "# Evaluation results\n\n"
    "Counts on synthetic data, never rounded up. Each section is rewritten by its own script.\n"
)


def write_section(name: str, body: str, path: Path = RESULTS_PATH) -> None:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    block = f"{start}\n{body.rstrip()}\n{end}"
    text = path.read_text(encoding="utf-8") if path.exists() else HEADER
    if start in text and end in text:
        before = text.split(start)[0]
        after = text.split(end, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")
