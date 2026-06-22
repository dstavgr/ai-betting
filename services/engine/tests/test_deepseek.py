import httpx

from app.llm.deepseek import DeepSeekClient, parse_json_content


def test_deepseek_client_generates_opportunity_copy() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"headline":"Draw is the rivalry angle",'
                                '"interesting_fact":"Two of the last three synced meetings ended level.",'
                                '"historical_angle":"The draw is the cleanest historical watch.",'
                                '"model_note":"Research signal only; no guarantees."}'
                            )
                        }
                    }
                ]
            },
        )

    client = DeepSeekClient(
        api_key="secret",
        base_url="https://example.test",
        model="deepseek-chat",
        transport=httpx.MockTransport(handler),
    )
    copy = client.opportunity_copy(
        {
            "headline": "Fallback headline",
            "interesting_fact": "Fallback fact",
            "historical_angle": "Fallback angle",
            "model_note": "Fallback note",
            "bet_angle": "Draw at 5.65",
            "home_team": "Atromitos",
            "away_team": "Panserraikos",
            "league": "Super League 1",
            "status": "FT",
            "data_state": "historical_validation",
            "h2h_sample_size": 3,
            "sample_size": 20,
            "recommendation": None,
        }
    )

    assert copy.headline == "Draw is the rivalry angle"
    assert copy.model_note == "Research signal only; no guarantees."
    assert seen_request is not None
    assert seen_request.url.path == "/chat/completions"
    assert seen_request.headers["authorization"] == "Bearer secret"


def test_parse_json_content_allows_fenced_json() -> None:
    assert parse_json_content('```json\n{"headline":"A"}\n```') == {"headline": "A"}
