import os
from dataclasses import dataclass


DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_TEMPLATE_PATH = "templates/b2b_template.ipynb"
DEFAULT_NOTEBOOK_BLOCKS_DIR = "templates/notebook_blocks"
DEFAULT_DICT_PATH = "data/words_ok_groups_v2.xlsx"
DEFAULT_OUTPUT_DIR = "output"


@dataclass(frozen=True)
class AgentSettings:
    api_key: str | None
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    llm_model: str = DEFAULT_LLM_MODEL
    template_path: str = DEFAULT_TEMPLATE_PATH
    notebook_blocks_dir: str = DEFAULT_NOTEBOOK_BLOCKS_DIR
    dict_path: str = DEFAULT_DICT_PATH
    output_dir: str = DEFAULT_OUTPUT_DIR

    @classmethod
    def from_env(cls) -> "AgentSettings":
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            llm_base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_LLM_BASE_URL),
            llm_model=os.getenv("DEEPSEEK_MODEL", DEFAULT_LLM_MODEL),
            template_path=os.getenv("TEMPLATE_PATH", DEFAULT_TEMPLATE_PATH),
            notebook_blocks_dir=os.getenv(
                "NOTEBOOK_BLOCKS_DIR",
                DEFAULT_NOTEBOOK_BLOCKS_DIR,
            ),
            dict_path=os.getenv("DICT_PATH", DEFAULT_DICT_PATH),
            output_dir=os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        )
