import json

import httpx
import pytest

from jarvis.config import ProviderConfig
from jarvis.providers import Provider, ProviderError

GROQ = ProviderConfig("groq", "https://api.groq.com/openai/v1", "llama-test", "secret-key")


def provider_with(handler, config=GROQ):
    client = httpx.Client(
        base_url=config.base_url,
        headers={"Authorization": f"Bearer {config.api_key}"},
        transport=httpx.MockTransport(handler),
    )
    return Provider(config, client=client)


def sse(*events):
    lines = [f"data: {json.dumps(e)}" for e in events] + ["data: [DONE]"]
    return "\n\n".join(lines).encode()


def delta(text):
    return {"choices": [{"delta": {"content": text}}]}


def test_streams_text_from_sse_and_sends_model_and_key():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        body = sse(delta("Good "), {"choices": [{"delta": {}}]}, delta("morning."))
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    text = "".join(provider_with(handler).stream([{"role": "user", "content": "hi"}]))

    assert text == "Good morning."
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer secret-key"
    assert seen["body"]["model"] == "llama-test"
    assert seen["body"]["stream"] is True


@pytest.mark.parametrize(
    "status, expected",
    [
        (401, "API key was rejected"),
        (404, "model 'llama-test' was not found"),
        (429, "rate limit"),
        (503, "HTTP 503"),
    ],
)
def test_http_errors_become_plain_reasons(status, expected):
    provider = provider_with(lambda r: httpx.Response(status, json={"error": {"message": "x"}}))
    with pytest.raises(ProviderError) as info:
        list(provider.stream([]))
    assert expected in info.value.reason
    assert info.value.provider == "groq"


def test_other_errors_include_the_service_message():
    provider = provider_with(lambda r: httpx.Response(400, json=[{"error": {"message": "Bad temperature"}}]))
    with pytest.raises(ProviderError) as info:
        list(provider.stream([]))
    assert info.value.reason == "HTTP 400: Bad temperature"


def test_gemini_style_bad_key_reads_as_rejected_key():
    provider = provider_with(lambda r: httpx.Response(400, json=[{"error": {"message": "Please pass a valid API key"}}]))
    with pytest.raises(ProviderError) as info:
        list(provider.stream([]))
    assert "API key was rejected" in info.value.reason


def test_error_event_mid_stream_raises():
    def handler(request):
        return httpx.Response(200, content=sse(delta("Hal"), {"error": {"message": "overloaded"}}))

    stream = provider_with(handler).stream([])
    assert next(stream) == "Hal"
    with pytest.raises(ProviderError, match="overloaded"):
        next(stream)


def test_connection_failure_mentions_ollama_when_local():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    ollama = ProviderConfig("ollama", "http://localhost:11434/v1", "qwen", None)
    with pytest.raises(ProviderError, match="is Ollama running"):
        list(provider_with(handler, ollama).stream([]))


def test_list_models_strips_gemini_prefix():
    def handler(request):
        assert request.url.path.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "models/gemini-b"}, {"id": "models/gemini-a"}]})

    assert provider_with(handler).list_models() == ["gemini-a", "gemini-b"]


def test_tool_call_deltas_are_assembled():
    deltas = [
        {"tool_calls": [{"index": 0, "id": "call_abc", "type": "function", "function": {"name": "get_", "arguments": ""}}]},
        {"tool_calls": [{"index": 0, "function": {"name": "time", "arguments": "{\"zone\":"}}]},
        {"tool_calls": [{"index": 0, "function": {"arguments": " \"Africa/Nairobi\"}"}}]},
    ]
    assembled = Provider.assemble_tool_calls(deltas)
    assert len(assembled) == 1
    call = assembled[0]
    assert call["id"] == "call_abc"
    assert call["function"]["name"] == "get_time"
    assert json.loads(call["function"]["arguments"]) == {"zone": "Africa/Nairobi"}


def test_image_is_sent_as_base64_data_url():
    """P6-03: Provider handles multimodal content blocks containing image_url."""
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=sse(delta("I see an error dialog.")), headers={"content-type": "text/event-stream"})

    image_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is on my screen?"},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]

    reply = "".join(provider_with(handler).stream(messages))
    assert reply == "I see an error dialog."
    sent_msgs = seen["body"]["messages"]
    assert len(sent_msgs) == 1
    parts = sent_msgs[0]["content"]
    assert isinstance(parts, list)
    assert parts[0]["type"] == "text"
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/")

