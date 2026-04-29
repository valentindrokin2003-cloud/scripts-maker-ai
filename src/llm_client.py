import logging

import httpx
from openai import OpenAI

from src.settings import AgentSettings


def create_openai_client(settings: AgentSettings) -> OpenAI:
    http_client = httpx.Client(trust_env=False)
    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.llm_base_url,
        http_client=http_client,
    )


def check_client_connection(client: OpenAI, settings: AgentSettings, logger: logging.Logger) -> None:
    logger.info("=" * 60)
    logger.info("Testing API connectivity...")
    logger.info("=" * 60)
    logger.info("OpenAI client initialized")
    logger.info("  Base URL: %s", settings.llm_base_url)
    logger.info("  Model: %s", settings.llm_model)

    try:
        logger.info("Attempting quick API test call (testing connection)...")
        test_response = client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=100,
            timeout=30,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say OK"},
            ],
        )
        logger.info("API test call successful - API is reachable")
        logger.info("  Response: %s", test_response.choices[0].message.content[:50])
    except Exception as e:
        logger.error("API test call failed: %s: %s", type(e).__name__, e)
        logger.error("  The API might be unreachable. Check:")
        logger.error("  1. Internet connection")
        logger.error("  2. API endpoint (%s)", settings.llm_base_url)
        logger.error("  3. Firewall/proxy settings")
        logger.error("  4. API key validity")
        logger.warning("Continuing anyway, but main API calls may also fail...")

    logger.info("=" * 60)
