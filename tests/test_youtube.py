import json

import httpx

from src.collectors import youtube


def test_minutes_parses_iso_durations() -> None:
    assert youtube.minutes("PT1H2M3S") == 63
    assert youtube.minutes("PT9M") == 9
    assert youtube.minutes("bad") == 0


def test_only_trusted_channels_of_a_teaching_length_are_eligible() -> None:
    ok = {"channel": "Corporate Finance Institute", "minutes": 12}
    assert youtube.eligible(ok)
    assert not youtube.eligible({**ok, "channel": "Random Uploader"})
    assert not youtube.eligible({**ok, "minutes": 1})


def test_a_fit_needs_a_quote_found_in_the_video_text() -> None:
    video = {"title": "Variance analysis", "channel": "Edspira"}
    text = "Variance analysis compares the budget with the actual result for each line."

    def answer(quote: str):
        return lambda messages, schema: json.dumps(
            {"verdict": "fits", "quote": quote, "reason": ""}
        )

    assert youtube.check(
        video, "Variance analytics", text, answer("compares the budget with the actual result")
    )
    assert (
        youtube.check(
            video, "Variance analytics", text, answer("an invented sentence the video never said")
        )
        == ""
    )
    assert youtube.check(video, "Variance analytics", "", answer("anything")) == ""


def test_search_and_details_read_the_api_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"items": [{"id": {"videoId": "abc"}}]})
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "abc",
                        "snippet": {
                            "title": "T",
                            "channelTitle": "Edspira",
                            "description": "D",
                            "publishedAt": "2024-01-02T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT10M"},
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        ids = youtube.search(client, "key", "q")
        assert ids == ["abc"]
        assert youtube.details(client, "key", ids)[0] == {
            "video": "abc",
            "title": "T",
            "channel": "Edspira",
            "description": "D",
            "published": "2024-01-02",
            "minutes": 10,
        }
