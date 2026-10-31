"""Every outbound client names Qart.ai and its purpose, and has a time budget."""

from src import http


def test_client_names_itself_and_keeps_its_budget() -> None:
    with http.client("link check", 7, follow_redirects=True) as client:
        assert client.headers["User-Agent"].startswith("Qart.ai link check (")
        assert client.timeout.read == 7 and client.follow_redirects
    with http.client("skill search") as client:
        assert client.timeout.read == http.DEFAULT_TIMEOUT_SECONDS
        assert not client.follow_redirects
