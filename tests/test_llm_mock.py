from slick_shared.config import get_settings
from slick_shared.llm import CompletionRequest, MockProvider, get_provider


async def test_mock_provider_is_zero_cost():
    provider = MockProvider(get_settings())
    result = await provider.complete(
        CompletionRequest(prompt="hello", purpose="clarifying-questions")
    )
    assert result.mock is True
    assert result.estimated_cost == 0.0
    assert result.tokens_out > 0
    assert "1." in result.text  # clarifying questions are numbered


async def test_get_provider_returns_mock_in_mock_mode():
    provider = get_provider()
    assert provider.name == "mock"
