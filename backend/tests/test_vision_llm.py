"""Unit tests for `llms/vision_llm.py` — the image-to-product extractor.

Tests two things:

1. `_parse_json` — a pure function that defends against LLMs wrapping their
   JSON in markdown blocks, chatty preambles, or multi-line formatting. No
   mocking needed.

2. `invoke_llm_with_image` — the async orchestrator that sends an image to
   Groq and parses/validates the result. The `vision_llm_mock` fixture
   replaces the real Groq API call with an AsyncMock.
"""
import json
import pytest
from unittest.mock import MagicMock

from llms.vision_llm import _parse_json, invoke_llm_with_image, ProductInfo

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════
# _parse_json — the resilient JSON extractor
# ═══════════════════════════════════════════════════════════════════════

class TestParseJson:
    def test_clean_json_parses_directly(self):
        text = '{"norm_name": "Shan Biryani", "companies": ["National Foods"]}'
        result = _parse_json(text)

        assert result["norm_name"] == "Shan Biryani"
        assert result["companies"] == ["National Foods"]

    def test_markdown_code_block_stripped(self):
        """LLMs love wrapping JSON in ```json ... ``` blocks."""
        text = '```json\n{"norm_name": "Halal Chicken"}\n```'
        result = _parse_json(text)

        assert result is not None
        assert result["norm_name"] == "Halal Chicken"

    def test_chatty_preamble_stripped(self):
        """LLMs sometimes add text before the JSON block."""
        text = 'Here is the extracted information:\n{"norm_name": "Halal Nuggets"}\nHope this helps!'
        result = _parse_json(text)

        assert result is not None
        assert result["norm_name"] == "Halal Nuggets"

    def test_multiline_json_parsed(self):
        """The regex uses re.DOTALL, so it should handle multi-line JSON."""
        text = """Sure! Here you go:
{
    "norm_name": "Halal Marshmallows",
    "companies": ["Freedom Mallows"]
}
Let me know if you need anything else."""
        result = _parse_json(text)

        assert result is not None
        assert result["norm_name"] == "Halal Marshmallows"
        assert result["companies"] == ["Freedom Mallows"]

    def test_no_json_returns_none(self):
        text = "I cannot extract any product information from this image."
        result = _parse_json(text)

        assert result is None

    def test_completely_invalid_json_returns_none(self):
        """Regex finds a {..} block but the content inside is not valid JSON."""
        text = "Here: {this is not: valid json at all}"
        result = _parse_json(text)

        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_json("")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# invoke_llm_with_image — the async orchestrator
# ═══════════════════════════════════════════════════════════════════════

def _make_llm_response(content: str):
    """Build a fake LLM response object with a .content attribute."""
    response = MagicMock()
    response.content = content
    return response


def _valid_product_json(**overrides) -> str:
    """Generate a complete, schema-valid ProductInfo JSON string."""
    base = {
        "norm_name": "Halal Chicken Nuggets",
        "companies": ["Crestwood"],
        "cert_bodies": ["HFA"],
        "typical_uses": ["Snack"],
        "marketplace": ["Tesco"],
        "category_l1": "Food",
        "category_l2": "Poultry",
        "halal_status": "Halal",
        "sold_in": ["UK"],
        "cert_numbers": ["HFA-001"],
        "health_info": ["High Protein"],
        "fda_numbers": [],
        "barcodes": ["1234567890"],
    }
    base.update(overrides)
    return json.dumps(base)


class TestInvokeLlmWithImage:
    async def test_empty_url_returns_error(self, vision_llm_mock):
        result = await invoke_llm_with_image("")

        assert result == {"error": "No valid image found"}
        # The LLM was never called
        vision_llm_mock.assert_not_called()

    async def test_none_url_returns_error(self, vision_llm_mock):
        result = await invoke_llm_with_image(None)

        assert result == {"error": "No valid image found"}

    async def test_llm_network_crash_returns_error(self, vision_llm_mock):
        """Simulates Groq throwing a rate-limit or network error."""
        vision_llm_mock.side_effect = RuntimeError("Rate limit exceeded")

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert "error" in result
        assert "LLM request failed" in result["error"]

    async def test_llm_empty_response_returns_error(self, vision_llm_mock):
        """LLM returns an empty string."""
        vision_llm_mock.return_value = _make_llm_response("")

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert result == {"error": "Empty response from LLM"}

    async def test_llm_none_content_returns_error(self, vision_llm_mock):
        """LLM returns None as content (edge case)."""
        vision_llm_mock.return_value = _make_llm_response(None)

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert result == {"error": "Empty response from LLM"}

    async def test_llm_unparseable_response_returns_error(self, vision_llm_mock):
        """LLM returns text with no JSON at all."""
        vision_llm_mock.return_value = _make_llm_response("I can see a chicken product but cannot format my response.")

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert result == {"error": "No valid JSON in LLM response"}

    async def test_happy_path_returns_validated_product(self, vision_llm_mock):
        """Perfect LLM response → parsed → validated → returned as dict."""
        vision_llm_mock.return_value = _make_llm_response(_valid_product_json())

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert result["norm_name"] == "Halal Chicken Nuggets"
        assert result["companies"] == ["Crestwood"]
        assert result["halal_status"] == "Halal"

    async def test_markdown_wrapped_response_still_parses(self, vision_llm_mock):
        """LLM wraps the JSON in markdown — _parse_json's regex saves the day."""
        wrapped = f"```json\n{_valid_product_json()}\n```"
        vision_llm_mock.return_value = _make_llm_response(wrapped)

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        assert result["norm_name"] == "Halal Chicken Nuggets"

    async def test_validation_failure_returns_raw_dict(self, vision_llm_mock):
        """If the LLM returns valid JSON but misses required Pydantic fields,
        the code catches ValidationError and returns the raw dict rather than
        crashing. This is graceful degradation."""
        # Missing norm_name (required by ProductInfo)
        partial = json.dumps({
            "companies": ["SomeCompany"],
            "halal_status": "Halal",
        })
        vision_llm_mock.return_value = _make_llm_response(partial)

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        # We get back the raw dict, not an error
        assert result["companies"] == ["SomeCompany"]
        assert result["halal_status"] == "Halal"
        # No "error" key — the code returned partial data rather than failing
        assert "error" not in result

    async def test_extra_fields_in_response_are_preserved_by_pydantic(self, vision_llm_mock):
        """If the LLM returns extra keys not in the schema, Pydantic ignores
        them in model_dump but they don't cause a crash."""
        extended = _valid_product_json(extra_field="bonus data")
        vision_llm_mock.return_value = _make_llm_response(extended)

        result = await invoke_llm_with_image("https://example.com/image.jpg")

        # The core fields are still correct
        assert result["norm_name"] == "Halal Chicken Nuggets"
        # Extra fields are dropped by model_dump (Pydantic's default behavior)
        assert "extra_field" not in result
