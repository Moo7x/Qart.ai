"""The web app's generated API types match the server: regenerate after a contract change.

python -m scripts.api_types
"""

from scripts.api_types import OUT, generate


def test_generated_web_types_are_up_to_date() -> None:
    assert OUT.read_text(encoding="utf-8") == generate(), (
        "web/src/apiTypes.ts is out of date: run python -m scripts.api_types"
    )
