# B2B Script Agent

Generates a populated Jupyter notebook from an Excel brief. The CLI reads the
brief, extracts structured fields with DeepSeek-compatible chat completions,
resolves dates, matches product words against the dictionary, generates regex
patterns, and fills the notebook template.

## Usage

```bash
python agent.py --brief "data/ТЗ_Fresh.xlsx"
python agent.py --brief "data/ТЗ_Fresh.xlsx" --output "output"
python agent.py --brief "data/ТЗ_Fresh.xlsx" --skip-api-check
```

Required environment:

```bash
DEEPSEEK_API_KEY=...
```

Optional environment overrides:

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
TEMPLATE_PATH=templates/b2b_template.ipynb
NOTEBOOK_BLOCKS_DIR=templates/notebook_blocks
DICT_PATH=data/words_ok_groups_v2.xlsx
OUTPUT_DIR=output
LOG_DIR=logs
```

Detailed CLI logs are written to `logs/agent_YYYYmmdd_HHMMSS.log` by default.
Use `--log-file path/to/run.log` to choose a specific file. `--skip-api-check`
skips the optional preflight API call and goes straight to the two pipeline LLM
calls.

## Web UI

Run the local upload interface:

```bash
python ui_server.py
```

Then open `http://127.0.0.1:8765`. The UI accepts an Excel `.xlsx` brief,
runs the same pipeline as the CLI, and downloads the generated `.ipynb`
notebook. Generated UI files are copied to `output/ui/`; temporary uploads live
under `.runtime/ui/` and are ignored by git.

Optional UI runtime settings:

```bash
MAX_UPLOAD_BYTES=26214400
python ui_server.py --host 127.0.0.1 --port 8765
```

## Workflow

The reusable orchestration lives in `src/pipeline.py` as `run_pipeline(...)`.
It performs the six production steps and returns a `PipelineResult` with the
resolved brief, dates, matched words, regex patterns, output path, and parsed
Excel text. `agent.py` is now a thin CLI wrapper around that service.

## Notebook Blocks

Notebook marker replacement code lives in `templates/notebook_blocks/`. Each
file corresponds to one `##AGENT:...##` marker in `templates/b2b_template.ipynb`.
`src/notebook_replacements.py` renders those files with standard-library
`string.Template`, then `src/notebook_filler.py` replaces the matching notebook
cells.

When adding or renaming a marker:

1. Add or update the code cell marker in `templates/b2b_template.ipynb`.
2. Add the matching block file in `templates/notebook_blocks/`.
3. Update `MARKER_TEMPLATES` in `src/notebook_replacements.py`.
4. Run the tests.

## Tests

Use the project virtual environment:

```bash
venv/bin/python -m pytest -q
venv/bin/python test_smoke_integration.py
```

The smoke integration test creates its own minimal Excel fixture and uses
mocked LLM calls, so it does not depend on private local brief files.
