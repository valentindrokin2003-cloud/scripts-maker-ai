from pathlib import Path

from agent import configure_logging


def test_configure_logging_uses_logs_dir_from_env(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("LOG_DIR", str(log_dir))

    log_file = configure_logging()

    assert Path(log_file).parent == log_dir
    assert Path(log_file).name.startswith("agent_")
    assert Path(log_file).suffix == ".log"


def test_configure_logging_accepts_explicit_log_file(tmp_path):
    log_file = tmp_path / "custom" / "run.log"

    result = configure_logging(str(log_file))

    assert result == str(log_file)
    assert log_file.parent.exists()
