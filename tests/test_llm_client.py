from unittest.mock import MagicMock

from src.llm_client import check_client_connection
from src.settings import AgentSettings


def test_client_connection_uses_configured_model():
    client = MagicMock()
    choice = MagicMock()
    choice.message.content = "OK"
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    logger = MagicMock()
    settings = AgentSettings(
        api_key="sk-test",
        llm_base_url="https://example.test",
        llm_model="example-model",
    )

    check_client_connection(client, settings, logger)

    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "example-model"
