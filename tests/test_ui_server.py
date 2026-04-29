import pytest
from pathlib import Path

from src.models import BriefIssue, BriefReview
from ui_server import (
    JOB_QUEUE,
    JOB_STORE,
    _append_job_progress,
    _content_disposition,
    _create_job,
    _download_content_type,
    _extract_brief_upload,
    _extract_brief_uploads,
    _fail_job,
    _finish_job,
    _job_payload,
    _jobs_payload,
    _mark_job_needs_revision,
    _safe_download_name,
    _step_index_from_message,
    _step_title_from_message,
    _validate_upload,
)


def test_validate_upload_accepts_xlsx():
    _validate_upload("brief.xlsx", 1024)


def test_validate_upload_rejects_non_xlsx():
    with pytest.raises(ValueError, match="xlsx"):
        _validate_upload("brief.xls", 1024)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(ValueError, match="пустой"):
        _validate_upload("brief.xlsx", 0)


def test_validate_upload_reads_size_limit_from_env(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "5")

    with pytest.raises(ValueError, match="Лимит"):
        _validate_upload("brief.xlsx", 6)


def test_safe_download_name_removes_unsafe_quotes():
    assert _safe_download_name('ООО "Ромашка"_script.ipynb') == "ООО Ромашка_script.ipynb"


def test_content_disposition_has_ascii_fallback_and_utf8_name():
    header = _content_disposition("ООО Ромашка_script.ipynb")

    header.encode("latin-1")
    assert 'filename="script.ipynb"' in header
    assert "filename*=UTF-8''%D0%9E%D0%9E%D0%9E%20%D0%A0%D0%BE%D0%BC%D0%B0%D1%88%D0%BA%D0%B0_script.ipynb" in header


def test_download_content_type_supports_notebook_and_html():
    assert _download_content_type("output/ui/result.ipynb") == "application/vnd.jupyter"
    assert _download_content_type("output/ui/result.html") == "text/html; charset=utf-8"


def test_extract_brief_upload_reads_multipart_file():
    boundary = "----b2b-test"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="brief"; filename="brief.xlsx"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n"
        "\r\n"
    ).encode("utf-8") + b"xlsx-bytes" + f"\r\n--{boundary}--\r\n".encode("utf-8")

    filename, payload = _extract_brief_upload(f"multipart/form-data; boundary={boundary}", body)

    assert filename == "brief.xlsx"
    assert payload == b"xlsx-bytes"


def test_extract_brief_uploads_reads_multiple_files():
    boundary = "----b2b-batch"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="brief"; filename="brief-1.xlsx"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n"
        "\r\n"
    ).encode("utf-8") + b"first" + (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="brief"; filename="brief-2.xlsx"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n"
        "\r\n"
    ).encode("utf-8") + b"second" + f"\r\n--{boundary}--\r\n".encode("utf-8")

    uploads = _extract_brief_uploads(f"multipart/form-data; boundary={boundary}", body)

    assert uploads == [
        ("brief-1.xlsx", b"first"),
        ("brief-2.xlsx", b"second"),
    ]


def test_step_parsing_helpers_extract_index_and_title():
    message = "[3/6] Resolving dates..."

    assert _step_index_from_message(message) == 2
    assert _step_title_from_message(message) == "Resolving dates..."


def test_job_progress_payload_tracks_active_and_completed_steps():
    job_id, _ = _create_job("brief.xlsx")
    try:
        _append_job_progress(job_id, "[1/7] Reading Excel brief: brief.xlsx")
        _append_job_progress(job_id, "[2/7] Extracting fields...")

        payload = _job_payload(job_id)

        assert payload is not None
        assert payload["status"] == "running"
        assert payload["progress"] == 28
        assert payload["steps"][0]["status"] == "done"
        assert payload["steps"][1]["status"] == "active"
    finally:
        JOB_STORE.pop(job_id, None)


def test_job_completion_and_failure_payloads():
    completed_job_id, _ = _create_job("brief.xlsx")
    failed_job_id, _ = _create_job("brief2.xlsx")
    review_job_id, _ = _create_job("brief3.xlsx")
    try:
        _finish_job(completed_job_id, "output/ui/result.ipynb")
        completed_payload = _job_payload(completed_job_id)
        assert completed_payload is not None
        assert completed_payload["status"] == "completed"
        assert completed_payload["download_url"] == f"/api/jobs/{completed_job_id}/download"

        _append_job_progress(failed_job_id, "[2/6] Extracting fields...")
        _fail_job(failed_job_id, "Ошибка генерации")
        failed_payload = _job_payload(failed_job_id)
        assert failed_payload is not None
        assert failed_payload["status"] == "failed"
        assert failed_payload["error"] == "Ошибка генерации"
        assert failed_payload["steps"][1]["status"] == "error"
        assert failed_payload["download_url"] == f"/api/jobs/{failed_job_id}/download"
        failed_report_path = JOB_STORE[failed_job_id]["output_path"]
        assert failed_report_path.endswith(".html")
        assert Path(failed_report_path).read_text(encoding="utf-8").find("Ошибка генерации") != -1

        _mark_job_needs_revision(
            review_job_id,
            BriefReview(
                status="needs_revision",
                issues=[
                    BriefIssue(
                        severity="warning",
                        title="Период неясен",
                        detail="Уточните период анализа",
                        field_name="analysis_period",
                    )
                ],
                extracted_fields={"client_name": "ООО Ромашка"},
            ),
        )
        review_payload = _job_payload(review_job_id)
        assert review_payload is not None
        assert review_payload["status"] == "needs_revision"
        assert review_payload["review"]["issues"][0]["title"] == "Период неясен"
        assert review_payload["steps"][2]["status"] == "review"
        assert review_payload["download_url"] == f"/api/jobs/{review_job_id}/download"
        review_report_path = JOB_STORE[review_job_id]["output_path"]
        assert review_report_path.endswith(".html")
        assert Path(review_report_path).read_text(encoding="utf-8").find("Период неясен") != -1
    finally:
        for job_id in (completed_job_id, failed_job_id, review_job_id):
            output_path = JOB_STORE.get(job_id, {}).get("output_path")
            if output_path and Path(output_path).suffix == ".html":
                Path(output_path).unlink(missing_ok=True)
        JOB_STORE.pop(completed_job_id, None)
        JOB_STORE.pop(failed_job_id, None)
        JOB_STORE.pop(review_job_id, None)


def test_jobs_payload_returns_sorted_job_summaries():
    first_job_id, first_job = _create_job("first.xlsx")
    second_job_id, second_job = _create_job("second.xlsx")
    try:
        first_job["created_at"] = 1
        second_job["created_at"] = 2
        first_job["job_id"] = first_job_id
        second_job["job_id"] = second_job_id
        first_job["status"] = "completed"
        first_job["output_path"] = "output/ui/first.ipynb"
        second_job["status"] = "queued"
        second_job["queue_position"] = 1
        JOB_QUEUE.clear()

        payload = _jobs_payload()

        assert [job["job_id"] for job in payload["jobs"]] == [first_job_id, second_job_id]
        assert payload["counts"]["completed"] == 1
        assert payload["counts"]["queued"] == 1
        assert payload["jobs"][0]["download_url"] == f"/api/jobs/{first_job_id}/download"
        assert payload["jobs"][1]["queue_position"] == 1
    finally:
        JOB_STORE.pop(first_job_id, None)
        JOB_STORE.pop(second_job_id, None)
