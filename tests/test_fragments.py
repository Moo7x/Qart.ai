from src import params
from src.agents.segments import combined_link, fragment


def test_a_long_passage_is_highlighted_from_its_first_to_its_last_words() -> None:
    words = [f"w{i}" for i in range(3 * params.FRAGMENT_WORDS)]
    directive = fragment(" ".join(words) + ".")
    start, end = directive.removeprefix("text=").split(",")
    assert start.split("%20")[0] == "w0" and end.split("%20")[-1] == words[-1]


def test_short_passages_use_the_start_only_and_symbols_are_encoded() -> None:
    assert (
        fragment("Accrual-based accounting, explained")
        == "text=Accrual%2Dbased%20accounting%2C%20explained"
    )
    assert fragment("") == ""


def test_several_passages_share_one_link() -> None:
    url = combined_link("https://example.org/page#old", ["First passage here.", "Second one."])
    assert url == "https://example.org/page#:~:text=First%20passage%20here.&text=Second%20one."
