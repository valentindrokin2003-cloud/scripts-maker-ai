#!/usr/bin/env python3
"""Local web UI for generating B2B notebooks from Excel briefs."""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import shutil
import threading
import time
import uuid
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from dotenv import load_dotenv

from src.brief_extractor import BriefExtractionError
from src.llm_client import create_openai_client
from src.models import BriefReview
from src.pipeline import PipelineCancelledError, run_pipeline
from src.settings import AgentSettings

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
STATIC_DIR = WEB_DIR / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 60 * 60
JOB_STORE: dict[str, dict[str, Any]] = {}
JOB_STORE_LOCK = threading.Lock()
JOB_QUEUE: list[tuple[str, Path, str]] = []
CANCEL_EVENTS: dict[str, threading.Event] = {}
RUNNING_JOB_ID: str | None = None
QUEUE_PROCESSOR_ACTIVE = False


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _safe_download_name(path: str) -> str:
    name = Path(path).name
    return name.replace('"', "").replace("\\", "_")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _content_disposition(filename: str) -> str:
    safe_name = _safe_download_name(filename)
    ascii_raw = safe_name.encode("ascii", "ignore").decode("ascii")
    ascii_name = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in ascii_raw
    ).strip("._-")
    ascii_name = ascii_name or "b2b_script.ipynb"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(safe_name)}"


def _download_content_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".ipynb":
        return "application/vnd.jupyter"
    if suffix == ".html":
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def _max_upload_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


def _max_batch_files() -> int:
    return int(os.getenv("MAX_BATCH_FILES", "10"))


def _validate_request_size(size: int) -> None:
    if size <= 0:
        raise ValueError("Не удалось прочитать загруженные файлы")

    max_request_bytes = _max_upload_bytes() * _max_batch_files()
    if size > max_request_bytes:
        mb = max_request_bytes // (1024 * 1024)
        raise ValueError(f"Слишком большой пакет файлов. Лимит запроса: {mb} MB")


def _validate_upload(filename: str, size: int) -> None:
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Загрузите бриф в формате .xlsx")
    if size <= 0:
        raise ValueError("Файл пустой")
    max_upload_bytes = _max_upload_bytes()
    if size > max_upload_bytes:
        mb = max_upload_bytes // (1024 * 1024)
        raise ValueError(f"Файл слишком большой. Лимит: {mb} MB")


def _extract_brief_uploads(content_type: str, body: bytes) -> list[tuple[str, bytes]]:
    if "multipart/form-data" not in content_type:
        raise ValueError("Ожидается multipart/form-data запрос")

    raw_message = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n\r\n"
    ).encode("utf-8") + body
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    if not message.is_multipart():
        raise ValueError("Не удалось разобрать загруженный файл")

    uploads: list[tuple[str, bytes]] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "brief":
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if not filename:
            raise ValueError("Выберите Excel-бриф перед запуском")
        uploads.append((Path(filename).name, payload))

    if not uploads:
        raise ValueError("Выберите Excel-бриф перед запуском")

    if len(uploads) > _max_batch_files():
        raise ValueError(f"Можно загрузить не более {_max_batch_files()} брифов за раз")

    return uploads


def _extract_brief_upload(content_type: str, body: bytes) -> tuple[str, bytes]:
    return _extract_brief_uploads(content_type, body)[0]


def _read_static_file(path: Path) -> tuple[bytes, str]:
    suffix = path.suffix.lower()
    content_type = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
    return path.read_bytes(), content_type


def _step_index_from_message(message: str) -> int | None:
    if not message.startswith("["):
        return None
    closing = message.find("]")
    if closing == -1:
        return None
    token = message[1:closing]
    current, _, total = token.partition("/")
    if not current.isdigit() or not total.isdigit():
        return None
    return max(0, int(current) - 1)


def _step_title_from_message(message: str) -> str:
    if "]" not in message:
        return message.strip()
    return message.split("]", 1)[1].strip()


def _cleanup_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    with JOB_STORE_LOCK:
        expired = [
            job_id
            for job_id, job in JOB_STORE.items()
            if job.get("updated_at", 0) < cutoff
        ]
        for job_id in expired:
            JOB_STORE.pop(job_id, None)
            CANCEL_EVENTS.pop(job_id, None)
        if expired:
            expired_ids = set(expired)
            JOB_QUEUE[:] = [
                item
                for item in JOB_QUEUE
                if item[0] not in expired_ids
            ]
            _refresh_queue_positions_locked()


def _create_job(filename: str) -> tuple[str, dict[str, Any]]:
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "status": "queued",
        "filename": filename,
        "progress": 0,
        "message": "Бриф загружен. Подготавливаю задачу.",
        "queue_position": None,
        "steps": [
            {"title": "Проверка и чтение Excel", "status": "pending", "detail": ""},
            {"title": "Извлечение полей из брифа", "status": "pending", "detail": ""},
            {"title": "Проверка качества брифа", "status": "pending", "detail": ""},
            {"title": "Нормализация периода", "status": "pending", "detail": ""},
            {"title": "Сопоставление со словарем", "status": "pending", "detail": ""},
            {"title": "Построение regex", "status": "pending", "detail": ""},
            {"title": "Сборка итогового notebook", "status": "pending", "detail": ""},
        ],
        "output_path": None,
        "review": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    with JOB_STORE_LOCK:
        JOB_STORE[job_id] = job
    return job_id, job


def _update_job(job_id: str, **updates: Any) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updated_at"] = time.time()


def _refresh_queue_positions_locked() -> None:
    for index, (job_id, _, _) in enumerate(JOB_QUEUE):
        job = JOB_STORE.get(job_id)
        if not job or job["status"] != "queued":
            continue
        queue_position = index + 1
        job["queue_position"] = queue_position
        job["message"] = (
            "Бриф в очереди на обработку."
            if queue_position == 1
            else f"Бриф в очереди на обработку. Позиция: {queue_position}."
        )
        job["updated_at"] = time.time()


def _append_job_progress(job_id: str, message: str) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job or job["status"] == "cancelled":
            return

        step_index = _step_index_from_message(message)
        detail = _step_title_from_message(message)

        if step_index is None:
            for step in reversed(job["steps"]):
                if step["status"] == "active":
                    step["detail"] = detail
                    break
        else:
            for index, step in enumerate(job["steps"]):
                if index < step_index and step["status"] != "done":
                    step["status"] = "done"
                    if not step["detail"]:
                        step["detail"] = step["title"]
                elif index == step_index:
                    step["status"] = "active"
                    step["detail"] = detail
                elif step["status"] == "active":
                    step["status"] = "pending"
            job["progress"] = int(((step_index + 1) / len(job["steps"])) * 100)

        job["message"] = detail
        job["status"] = "running"
        job["queue_position"] = None
        job["updated_at"] = time.time()


def _finish_job(job_id: str, output_path: str) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        for step in job["steps"]:
            step["status"] = "done"
            if not step["detail"]:
                step["detail"] = step["title"]
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Notebook собран и готов к скачиванию."
        job["output_path"] = output_path
        job["queue_position"] = None
        job["updated_at"] = time.time()
        global RUNNING_JOB_ID
        if RUNNING_JOB_ID == job_id:
            RUNNING_JOB_ID = None


def _fail_job(job_id: str, error: str) -> None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        for step in job["steps"]:
            if step["status"] == "active":
                step["status"] = "error"
                if not step["detail"]:
                    step["detail"] = error
                break
        job["status"] = "failed"
        job["error"] = error
        job["message"] = error
        job["queue_position"] = None
        job["updated_at"] = time.time()
        global RUNNING_JOB_ID
        if RUNNING_JOB_ID == job_id:
            RUNNING_JOB_ID = None
    _attach_failure_report(job_id, error)


def _cancel_job(job_id: str) -> None:
    cancel_event = CANCEL_EVENTS.get(job_id)
    if cancel_event:
        cancel_event.set()

    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        for step in job["steps"]:
            if step["status"] == "active":
                step["status"] = "cancelled"
                step["detail"] = "Задача отменена пользователем"
                break
        job["status"] = "cancelled"
        job["message"] = "Задача отменена пользователем."
        job["queue_position"] = None
        job["updated_at"] = time.time()
        JOB_QUEUE[:] = [item for item in JOB_QUEUE if item[0] != job_id]
        _refresh_queue_positions_locked()
        global RUNNING_JOB_ID
        if RUNNING_JOB_ID == job_id:
            RUNNING_JOB_ID = None


def _job_payload(job_id: str) -> dict[str, Any] | None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return None
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "filename": job["filename"],
            "progress": job["progress"],
            "message": job["message"],
            "queue_position": job["queue_position"],
            "steps": [dict(step) for step in job["steps"]],
            "download_url": f"/api/jobs/{job_id}/download" if job.get("output_path") else None,
            "review": job["review"],
            "error": job["error"],
            "cancellable": job["status"] in ("queued", "running"),
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }


def _job_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "filename": job["filename"],
        "progress": job["progress"],
        "message": job["message"],
        "queue_position": job["queue_position"],
        "download_url": f"/api/jobs/{job['job_id']}/download" if job.get("output_path") else None,
        "error": job["error"],
        "cancellable": job["status"] in ("queued", "running"),
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }


def _jobs_payload() -> dict[str, Any]:
    with JOB_STORE_LOCK:
        jobs = sorted(JOB_STORE.values(), key=lambda item: item["created_at"])
        summaries = [_job_summary(job) for job in jobs]

    return {
        "jobs": summaries,
        "counts": {
            "total": len(summaries),
            "queued": sum(job["status"] == "queued" for job in summaries),
            "running": sum(job["status"] == "running" for job in summaries),
            "completed": sum(job["status"] == "completed" for job in summaries),
            "needs_revision": sum(job["status"] == "needs_revision" for job in summaries),
            "failed": sum(job["status"] == "failed" for job in summaries),
            "cancelled": sum(job["status"] == "cancelled" for job in summaries),
        },
    }


def _serialize_review(review: BriefReview) -> dict[str, Any]:
    return {
        "status": review.status,
        "issues": [
            {
                "severity": issue.severity,
                "title": issue.title,
                "detail": issue.detail,
                "field_name": issue.field_name,
            }
            for issue in review.issues
        ],
        "extracted_fields": review.extracted_fields,
    }


def _format_report_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "Не выделено"
    if isinstance(value, dict):
        if not value:
            return "Не выделено"
        parts = []
        for key, items in value.items():
            rendered_items = ", ".join(str(item) for item in items) if isinstance(items, list) else str(items)
            parts.append(f"{key}: {rendered_items}")
        return "; ".join(parts)
    if value in (None, ""):
        return "Не выделено"
    return str(value)


def _build_report_html(
    *,
    filename: str,
    status: str,
    title: str,
    summary: str,
    review: dict[str, Any] | None = None,
    error: str | None = None,
) -> str:
    issue_blocks = ""
    if review and review.get("issues"):
        blocks: list[str] = []
        for issue in review["issues"]:
            blocks.append(
                "<article class=\"issue\">"
                f"<div class=\"issue__severity\">{html.escape(issue['severity'])}</div>"
                f"<h3>{html.escape(issue['title'])}</h3>"
                f"<p>{html.escape(issue['detail'])}</p>"
                "</article>"
            )
        issue_blocks = (
            "<section><h2>Замечания</h2>"
            f"{''.join(blocks)}"
            "</section>"
        )

    fields_block = ""
    extracted_fields = review.get("extracted_fields") if review else None
    if extracted_fields:
        rows = []
        for key, value in extracted_fields.items():
            rows.append(
                "<div class=\"field\">"
                f"<dt>{html.escape(str(key))}</dt>"
                f"<dd>{html.escape(_format_report_value(value))}</dd>"
                "</div>"
            )
        fields_block = (
            "<section><h2>Что удалось извлечь</h2>"
            f"<dl>{''.join(rows)}</dl>"
            "</section>"
        )

    error_block = ""
    if error:
        error_block = (
            "<section><h2>Текст ошибки</h2>"
            f"<pre>{html.escape(error)}</pre>"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe4;
      --paper: #fffdf8;
      --ink: #1f1a17;
      --muted: #6f6358;
      --line: #d8c7b0;
      --accent: #b35c2e;
      --accent-soft: #f3dfd2;
      --danger: #9f2f2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f1e5d2 0%, var(--bg) 38%, #efe6d8 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}
    .sheet {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 60px rgba(69, 42, 19, 0.08);
      overflow: hidden;
    }}
    header {{
      padding: 28px 28px 22px;
      background: linear-gradient(135deg, #fff6eb 0%, #f6e1cd 100%);
      border-bottom: 1px solid var(--line);
    }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 12px;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{ font-size: 34px; line-height: 1.1; }}
    .lead {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.5;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .meta__card {{
      padding: 14px 16px;
      background: rgba(255, 253, 248, 0.82);
      border: 1px solid var(--line);
      border-radius: 16px;
    }}
    .meta__card strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    section {{
      padding: 24px 28px;
      border-top: 1px solid var(--line);
    }}
    section h2 {{
      margin-bottom: 16px;
      font-size: 22px;
    }}
    .issue {{
      padding: 16px 18px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #fffaf4;
    }}
    .issue + .issue {{ margin-top: 12px; }}
    .issue__severity {{
      display: inline-block;
      margin-bottom: 10px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #f6ddd4;
      color: var(--danger);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .issue p {{
      margin: 10px 0 0;
      line-height: 1.55;
      color: var(--muted);
    }}
    dl {{
      margin: 0;
      display: grid;
      gap: 12px;
    }}
    .field {{
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #fffaf4;
    }}
    dt {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }}
    dd {{
      margin: 8px 0 0;
      line-height: 1.5;
    }}
    pre {{
      margin: 0;
      padding: 16px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      border-radius: 16px;
      background: #2f241f;
      color: #fff4ea;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 14px;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <main>
    <div class="sheet">
      <header>
        <span class="eyebrow">{html.escape(status)}</span>
        <h1>{html.escape(title)}</h1>
        <p class="lead">{html.escape(summary)}</p>
        <div class="meta">
          <div class="meta__card">
            <strong>Исходный бриф</strong>
            <span>{html.escape(filename)}</span>
          </div>
          <div class="meta__card">
            <strong>Статус</strong>
            <span>{html.escape(status)}</span>
          </div>
        </div>
      </header>
      {issue_blocks}
      {fields_block}
      {error_block}
    </div>
  </main>
</body>
</html>
"""


def _create_job_report(
    job_id: str,
    *,
    report_suffix: str,
    title: str,
    summary: str,
    review: dict[str, Any] | None = None,
    error: str | None = None,
) -> str | None:
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return None
        filename = job["filename"]
        status = job["status"]

    final_dir = ROOT_DIR / "output" / "ui"
    final_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"{Path(filename).stem}_{report_suffix}.html"
    report_path = _unique_path(final_dir / report_name)
    report_path.write_text(
        _build_report_html(
            filename=filename,
            status=status,
            title=title,
            summary=summary,
            review=review,
            error=error,
        ),
        encoding="utf-8",
    )
    return str(report_path)


def _mark_job_needs_revision(job_id: str, review: BriefReview) -> None:
    serialized_review = _serialize_review(review)
    with JOB_STORE_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        for index, step in enumerate(job["steps"]):
            if index < 2:
                step["status"] = "done"
                if not step["detail"]:
                    step["detail"] = step["title"]
            elif index == 2:
                step["status"] = "review"
                step["detail"] = f"Найдено замечаний: {len(review.issues)}"
        job["status"] = "needs_revision"
        job["progress"] = int((3 / len(job["steps"])) * 100)
        job["message"] = "Бриф требует доработки перед запуском генерации."
        job["review"] = serialized_review
        job["queue_position"] = None
        job["updated_at"] = time.time()
        global RUNNING_JOB_ID
        if RUNNING_JOB_ID == job_id:
            RUNNING_JOB_ID = None
    report_path = _create_job_report(
        job_id,
        report_suffix="review_report",
        title="Бриф требует доработки",
        summary="Сервис остановил генерацию и подготовил список замечаний по брифу.",
        review=serialized_review,
    )
    if report_path:
        _update_job(job_id, output_path=report_path)


def _attach_failure_report(job_id: str, error: str) -> None:
    report_path = _create_job_report(
        job_id,
        report_suffix="error_report",
        title="Генерация завершилась ошибкой",
        summary="Сервис не смог завершить обработку брифа. Ниже сохранен текст ошибки.",
        error=error,
    )
    if report_path:
        _update_job(job_id, output_path=report_path)


def _start_queue_processor_if_needed() -> None:
    global QUEUE_PROCESSOR_ACTIVE

    with JOB_STORE_LOCK:
        if QUEUE_PROCESSOR_ACTIVE:
            return
        QUEUE_PROCESSOR_ACTIVE = True

    thread = threading.Thread(target=_process_queue, daemon=True)
    thread.start()


def _schedule_job(job_id: str, brief_path: Path, original_name: str) -> None:
    with JOB_STORE_LOCK:
        JOB_QUEUE.append((job_id, brief_path, original_name))
        _refresh_queue_positions_locked()
    _start_queue_processor_if_needed()


def _process_queue() -> None:
    global QUEUE_PROCESSOR_ACTIVE, RUNNING_JOB_ID

    while True:
        with JOB_STORE_LOCK:
            if not JOB_QUEUE and RUNNING_JOB_ID is None:
                QUEUE_PROCESSOR_ACTIVE = False
                return

            if RUNNING_JOB_ID is not None or not JOB_QUEUE:
                pass
            else:
                job_id, brief_path, original_name = JOB_QUEUE.pop(0)
                job = JOB_STORE.get(job_id)
                if job and job["status"] == "cancelled":
                    continue
                if job:
                    job["queue_position"] = None
                RUNNING_JOB_ID = job_id
                _refresh_queue_positions_locked()
                thread = threading.Thread(
                    target=_run_job,
                    args=(job_id, brief_path, original_name),
                    daemon=True,
                )
                thread.start()

        time.sleep(0.5)


def _run_job(job_id: str, brief_path: Path, original_name: str) -> None:
    global RUNNING_JOB_ID
    cancel_event = threading.Event()
    CANCEL_EVENTS[job_id] = cancel_event

    try:
        settings = AgentSettings.from_env()
        if not settings.api_key:
            raise ValueError("DEEPSEEK_API_KEY не задан в .env")

        def _progress_callback(message: str) -> None:
            if cancel_event.is_set():
                raise PipelineCancelledError("Pipeline cancelled by user")
            _append_job_progress(job_id, message)

        output_dir = str(brief_path.parent.parent / "output")
        client = create_openai_client(settings)
        result = run_pipeline(
            str(brief_path),
            output_dir,
            settings,
            client,
            progress=_progress_callback,
            cancel_event=cancel_event,
        )
        if result.status == "needs_revision" and result.review is not None:
            _mark_job_needs_revision(job_id, result.review)
            logger.info("Brief %s requires revision before notebook generation", original_name)
            return

        logger.info("Generated notebook %s from %s", result.output_path, original_name)

        final_dir = ROOT_DIR / "output" / "ui"
        final_dir.mkdir(parents=True, exist_ok=True)
        final_path = _unique_path(final_dir / Path(result.output_path).name)
        shutil.copy2(result.output_path, final_path)
        _finish_job(job_id, str(final_path))
    except PipelineCancelledError:
        logger.info("Job %s (%s) was cancelled by user", job_id, original_name)
        with JOB_STORE_LOCK:
            if RUNNING_JOB_ID == job_id:
                RUNNING_JOB_ID = None
    except BriefExtractionError as exc:
        _fail_job(job_id, f"Не удалось разобрать бриф: {exc}")
    except Exception as exc:  # noqa: BLE001 - UI needs readable failure details
        logger.exception("Notebook generation failed for job %s", job_id)
        _fail_job(job_id, f"Ошибка генерации: {type(exc).__name__}: {exc}")
    finally:
        CANCEL_EVENTS.pop(job_id, None)


class B2BUIHandler(BaseHTTPRequestHandler):
    server_version = "B2BScriptUI/1.0"

    def do_GET(self) -> None:
        _cleanup_jobs()

        if self.path in {"/", "/index.html"}:
            self._send_file(WEB_DIR / "index.html")
            return

        if self.path.startswith("/static/"):
            requested = STATIC_DIR / unquote(self.path.removeprefix("/static/"))
            try:
                requested.resolve().relative_to(STATIC_DIR.resolve())
            except ValueError:
                self._send_json({"error": "Invalid static path"}, HTTPStatus.BAD_REQUEST)
                return
            self._send_file(requested)
            return

        if self.path.rstrip("/") == "/api/jobs":
            self._send_json(_jobs_payload(), HTTPStatus.OK)
            return

        if self.path.startswith("/api/jobs/"):
            self._handle_job_get()
            return

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        _cleanup_jobs()

        try:
            payload = self._create_generation_job()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # noqa: BLE001 - convert server failures into UI-visible errors
            logger.exception("Notebook generation setup failed")
            self._send_json({"error": f"Ошибка запуска: {type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(payload, HTTPStatus.ACCEPTED)

    def do_DELETE(self) -> None:
        if not self.path.startswith("/api/jobs/"):
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        self._handle_job_cancel()

    def _create_generation_job(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        _validate_request_size(content_length)

        raw_request = self.rfile.read(content_length)
        uploads = _extract_brief_uploads(
            self.headers.get("Content-Type", ""),
            raw_request,
        )

        run_id = uuid.uuid4().hex[:12]
        runtime_dir = ROOT_DIR / ".runtime" / "ui" / run_id
        input_dir = runtime_dir / "uploads"
        input_dir.mkdir(parents=True, exist_ok=True)

        created_jobs: list[dict[str, Any]] = []
        for original_name, raw in uploads:
            _validate_upload(original_name, len(raw))
            brief_path = _unique_path(input_dir / original_name)
            brief_path.write_bytes(raw)

            job_id, _ = _create_job(original_name)
            _schedule_job(job_id, brief_path, original_name)
            payload = _job_payload(job_id)
            if payload is not None:
                created_jobs.append(payload)

        return {
            "jobs": created_jobs,
            "accepted": len(created_jobs),
        }

    def _handle_job_cancel(self) -> None:
        path = self.path.rstrip("/")
        parts = path.split("/")
        if len(parts) != 5 or parts[4] != "cancel":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        job_id = parts[3]
        with JOB_STORE_LOCK:
            job = JOB_STORE.get(job_id)
        if not job:
            self._send_json({"error": "Задача не найдена"}, HTTPStatus.NOT_FOUND)
            return

        if job["status"] not in ("queued", "running"):
            self._send_json(
                {"error": f"Задачу в статусе '{job['status']}' нельзя отменить"},
                HTTPStatus.CONFLICT,
            )
            return

        _cancel_job(job_id)
        payload = _job_payload(job_id)
        self._send_json(payload or {"job_id": job_id, "status": "cancelled"}, HTTPStatus.OK)

    def _handle_job_get(self) -> None:
        path = self.path.rstrip("/")
        parts = path.split("/")
        if len(parts) < 4:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        job_id = parts[3]
        if len(parts) == 4:
            payload = _job_payload(job_id)
            if payload is None:
                self._send_json({"error": "Задача не найдена"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload, HTTPStatus.OK)
            return

        if len(parts) == 5 and parts[4] == "download":
            self._send_job_download(job_id)
            return

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def _send_job_download(self, job_id: str) -> None:
        with JOB_STORE_LOCK:
            job = JOB_STORE.get(job_id)
            if not job:
                self._send_json({"error": "Задача не найдена"}, HTTPStatus.NOT_FOUND)
                return
            output_path = job.get("output_path")

        if not output_path:
            self._send_json({"error": "Файл еще не готов"}, HTTPStatus.CONFLICT)
            return

        file_bytes = Path(output_path).read_bytes()
        download_name = _safe_download_name(output_path)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _download_content_type(output_path))
        self.send_header("Content-Disposition", _content_disposition(download_name))
        self.send_header("Content-Length", str(len(file_bytes)))
        self.end_headers()
        self.wfile.write(file_bytes)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        body, content_type = _read_static_file(path)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    load_dotenv()
    configure_logging()
    address = (host, port)
    server = ThreadingHTTPServer(address, B2BUIHandler)
    url = f"http://{html.escape(host)}:{port}"
    logger.info("B2B Script UI is running at %s", url)
    logger.info("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping UI server")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local B2B Script Agent UI")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
