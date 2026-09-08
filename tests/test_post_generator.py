import json
import random
import post_generator


class MockMessage:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, message):
        self.message = message

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(MockMessage(content))]

class MockCompletions:
    def __init__(self, response_content):
        self._response_content = response_content
    def create(self, *args, **kwargs):
        return MockResponse(self._response_content)

class MockChat:
    def __init__(self, response_content):
        self.completions = MockCompletions(response_content)

class MockGroq:
    def __init__(self, api_key=None, response_content=None):
        self.chat = MockChat(response_content)


def test_sanitize_text_removes_markdown():
    s = "Hello **bold** and `code` and ```sql\nSELECT 1\n```"
    out = post_generator.sanitize_text(s)
    assert "**" not in out
    assert "`" not in out
    assert "```" not in out
    assert "SELECT 1" in out


def test_pick_hashtags_count():
    tags = post_generator.pick_hashtags("insight", "databricks")
    count = len(tags.split())
    assert 4 <= count <= 6


def test_generate_post_parses_json_and_sanitizes(monkeypatch, tmp_path):
    # make a 160-word sample post_text
    words = ["word"] * 160
    sample_text = " ".join(words)
    mock_json = json.dumps({
        "post_text": sample_text,
        "hashtags": "#DataEngineering #HealthTech #DataMesh #GenAI #CloudArchitecture",
        "image_prompt": "Sample image prompt for testing"
    })

    # Monkeypatch Groq client and model selection
    monkeypatch.setattr(post_generator, "Groq", lambda api_key=None: MockGroq(response_content=mock_json))
    monkeypatch.setattr(post_generator, "select_best_model", lambda api_key=None: "mock-model")

    result = post_generator.generate_post(api_key="dummy")
    assert "text" in result and "hashtags" in result and "image_prompt" in result
    assert "```" not in result["text"] and "`" not in result["text"]
    assert 150 <= len(result["text"].split()) <= 250


def test_sanitize_post_text_removes_nested_json_fragments_and_stray_braces():
    raw = '{"post_text": "This is a clean caption with braces {and quotes}. { \\"post_text\\": \\"duplicate\\" }"}'
    out = post_generator.sanitize_post_text(raw, "#DataEngineering #DataPlatform")
    assert "post_text" not in out
    assert "{" not in out
    assert "}" not in out
    assert "This is a clean caption" in out
