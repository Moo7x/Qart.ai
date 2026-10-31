"""Automatic fit check for candidate courses: does the course's own page show it teaches the skill?

    .venv/Scripts/python.exe -m src.collectors.course_check            # check unchecked candidates
    .venv/Scripts/python.exe -m src.collectors.course_check --recheck  # check every candidate again

A candidate (`verified: false`) comes from a provider's catalogue or a page read by hand, so the
course is real and free; what is open is whether it teaches the skill it was matched to. For each
candidate the check reads the course page and asks the language model (`LLM_MODEL`) for a verdict
and one sentence copied from the page that shows the skill is taught. Code then keeps the verdict
only if that sentence is really on the page. A course becomes `verified` only on "fits" with a
found quote; anything else stays a candidate and is never planned. The result is stored as
`fit_check` (result, model, quote, date), so the screen can say how the course was checked.
The model gives a verdict and a quote, never a number.
"""

import argparse
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from src import http, llm, params
from src.config import Settings, load_settings
from src.envfile import load_env_file
from src.evidence.field import PACK_DIR
from src.pack import load_pack

# The candidate files this check may change (both written by owner A's catalogue work).
CANDIDATE_FILES = ("courses_mslearn.yaml", "courses_open.yaml")
SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "quote", "reason"],
    "properties": {
        "verdict": {"type": "string", "enum": ["fits", "does_not_fit", "unclear"]},
        "quote": {"type": "string"},
        "reason": {"type": "string"},
    },
}
SYSTEM = (
    "You check whether a free course teaches one finance-related skill. Use only the course page "
    "text you are given. Answer 'fits' when the course teaches knowledge or tasks that belong to "
    "the skill, including doing that work in a particular software system; it does not need to "
    "cover the whole skill. The level sentences only show what the skill means. Copy one sentence "
    "or list item from the page, word for word, that shows it; if you cannot, answer 'unclear'. "
    "Answer 'does_not_fit' when the course teaches something else, for example only a software "
    "setting unrelated to the skill. Never use outside knowledge and never invent text."
)

Reader = Callable[[str], str]


def _squash(text: str) -> str:
    """Compare quotes without case, spacing or punctuation differences the page extraction adds."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def quote_found(quote: str, page: str) -> bool:
    words = _squash(quote).split()
    return len(words) >= params.COURSE_CHECK_MIN_QUOTE_WORDS and " ".join(words) in _squash(page)


def read_page(url: str) -> str:
    import trafilatura

    with http.client(
        "course check", params.COURSE_CHECK_FETCH_SECONDS, follow_redirects=True
    ) as client:
        response = client.get(url)
        response.raise_for_status()
    return trafilatura.extract(response.text, include_comments=False) or ""


def check_course(
    course: dict[str, Any], skill_text: str, page: str, complete: llm.Complete, model: str
) -> dict[str, Any]:
    """The stored fit check for one course and one skill description."""
    today = f"{datetime.now(UTC):%Y-%m-%d}"
    if not page.strip():
        return {"result": "unclear", "by": model, "quote": "", "checked": today}
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Skill: {skill_text}\n\nCourse: {course['title']} ({course['provider']})\n\n"
                f"Course page text:\n{page[: params.COURSE_CHECK_PAGE_CHARS]}"
            ),
        },
    ]
    answer = json.loads(complete(messages, SCHEMA))
    result = answer["verdict"]
    if result == "fits" and not quote_found(answer["quote"], page):
        result = "unclear"  # the model's sentence is not on the page: never a verified fit
    quote = answer["quote"] if result == "fits" else ""
    return {"result": result, "by": model, "quote": quote, "checked": today}


def _skill_text(skill_id: str) -> str:
    pack = load_pack()
    from src.levels import load_levels

    name = pack.skills[skill_id].name
    try:
        anchors = load_levels().skills[skill_id].anchors
        return f"{name}. Level 1: {anchors[1]} Level 2: {anchors[2]}"
    except KeyError:
        return name


def run(
    settings: Settings,
    recheck: bool = False,
    reader: Reader = read_page,
    complete: llm.Complete | None = None,
    files: tuple[str, ...] = CANDIDATE_FILES,
    pack_dir: Path = PACK_DIR,
) -> dict[str, int]:
    """Check the candidates in each file and write the results back. Returns counts by result."""
    if complete is None:
        if not settings.llm_configured:
            raise SystemExit("the course check needs the language model (LLM_API_KEY)")
        complete = llm.openai_complete(
            settings,
            schema_name="course_fit",
            purpose="course_fit_check",
            timeout=params.COURSE_CHECK_LLM_SECONDS,
        )
    counts = {"fits": 0, "does_not_fit": 0, "unclear": 0, "skipped": 0}
    for name in files:
        path = pack_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        header = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
        data = yaml.safe_load(text)
        for course in data["courses"]:
            if course.get("verified") or (course.get("fit_check") and not recheck):
                counts["skipped"] += 1
                continue
            try:
                page = reader(course["url"])
            except httpx.HTTPError:
                page = ""  # page down or refusing: unclear, so the course stays a candidate
            # Each covered skill is judged on its own; the course keeps the skills it teaches.
            checks = {
                skill: check_course(course, _skill_text(skill), page, complete, settings.llm_model)
                for skill in course["covers"]
            }
            fitting = [skill for skill, c in checks.items() if c["result"] == "fits"]
            if fitting:
                course["fit_check"] = {
                    **checks[fitting[0]],
                    "skills_removed": [s for s in course["covers"] if s not in fitting],
                }
                course["covers"] = fitting
                course["verified"] = True
                counts["fits"] += 1
            else:
                order = ["does_not_fit", "unclear"]
                worst = min(checks.values(), key=lambda c: order.index(c["result"]))
                course["fit_check"] = worst
                course["verified"] = False
                counts[worst["result"]] += 1
        path.write_text(
            header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--recheck", action="store_true", help="check every candidate again")
    args = parser.parse_args()
    load_env_file()  # the model key lives in the local .env
    print(run(load_settings(), recheck=args.recheck))


if __name__ == "__main__":
    main()
