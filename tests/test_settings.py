from src.settings import (
    DEFAULT_DICT_PATH,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_NOTEBOOK_BLOCKS_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TEMPLATE_PATH,
    AgentSettings,
)


def test_settings_defaults_when_env_is_empty(monkeypatch):
    for key in (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "TEMPLATE_PATH",
        "NOTEBOOK_BLOCKS_DIR",
        "DICT_PATH",
        "OUTPUT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = AgentSettings.from_env()

    assert settings.api_key is None
    assert settings.llm_base_url == DEFAULT_LLM_BASE_URL
    assert settings.llm_model == DEFAULT_LLM_MODEL
    assert settings.template_path == DEFAULT_TEMPLATE_PATH
    assert settings.notebook_blocks_dir == DEFAULT_NOTEBOOK_BLOCKS_DIR
    assert settings.dict_path == DEFAULT_DICT_PATH
    assert settings.output_dir == DEFAULT_OUTPUT_DIR


def test_settings_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.test")
    monkeypatch.setenv("DEEPSEEK_MODEL", "example-model")
    monkeypatch.setenv("TEMPLATE_PATH", "custom/template.ipynb")
    monkeypatch.setenv("NOTEBOOK_BLOCKS_DIR", "custom/notebook_blocks")
    monkeypatch.setenv("DICT_PATH", "custom/dict.xlsx")
    monkeypatch.setenv("OUTPUT_DIR", "custom-output")

    settings = AgentSettings.from_env()

    assert settings.api_key == "sk-test"
    assert settings.llm_base_url == "https://example.test"
    assert settings.llm_model == "example-model"
    assert settings.template_path == "custom/template.ipynb"
    assert settings.notebook_blocks_dir == "custom/notebook_blocks"
    assert settings.dict_path == "custom/dict.xlsx"
    assert settings.output_dir == "custom-output"
