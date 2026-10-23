"""Remove personal identifiers from CV text before anything else reads it.

Removed: email addresses, phone numbers, Malaysian IC numbers, web links, labelled personal lines
(Name, Address, Phone, Email, IC, Date of birth, Gender, Religion, Race, Nationality) and the
first line when it looks like a person's name (a short line of words with no digits). Age,
gender and background never reach matching. The scrubbed text is what the model and the
evidence check see.
"""

import re
from dataclasses import dataclass

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
# Malaysian identity card number: YYMMDD-PB-###G, with or without dashes.
MY_IC = re.compile(r"\b\d{6}-?\d{2}-?\d{4}\b")
# Phone numbers: +60 or 0 prefix, 9–11 digits with optional spaces or dashes.
PHONE = re.compile(r"(?:\+?6?0)[\s-]?\d{1,2}[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
LABELLED = re.compile(
    r"^\s*(name|full name|address|phone|mobile|tel|email|e-mail|ic|ic no|nric|date of birth|dob|"
    r"age|gender|sex|religion|race|ethnicity|nationality|marital status)\s*[:\-].*$",
    re.I | re.M,
)
NAME_LINE_MAX_WORDS = 6  # longer first lines are headlines or summaries, not names


@dataclass(frozen=True)
class Scrubbed:
    text: str
    removed: dict[str, int]  # what kind of identifier, how many (never the values)


def _looks_like_name(line: str) -> bool:
    words = line.split()
    return (
        0 < len(words) <= NAME_LINE_MAX_WORDS
        and not any(ch.isdigit() for ch in line)
        and all(w[:1].isupper() or w.lower() in {"bin", "binti", "a/l", "a/p", "@"} for w in words)
    )


def scrub(text: str) -> Scrubbed:
    removed: dict[str, int] = {}

    def cut(pattern: re.Pattern[str], label: str, source: str) -> str:
        found = pattern.findall(source)
        if found:
            removed[label] = removed.get(label, 0) + len(found)
        return pattern.sub(f"[{label} removed]", source)

    out = cut(LABELLED, "personal detail", text)
    out = cut(EMAIL, "email", out)
    out = cut(URL, "link", out)
    out = cut(MY_IC, "IC number", out)
    out = cut(PHONE, "phone", out)
    lines = out.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is not None and _looks_like_name(lines[first].strip()):
        lines[first] = "[name removed]"
        removed["name"] = 1
    return Scrubbed(text="\n".join(lines), removed=removed)
