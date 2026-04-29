const form = document.querySelector("#brief-form");
const input = document.querySelector("#brief-input");
const fileName = document.querySelector("#file-name");
const fileCaption = document.querySelector("#file-caption");
const selectedFilesBox = document.querySelector("#selected-files");
const batchHintCount = document.querySelector("#batch-hint-count");
const statusBox = document.querySelector("#status");
const submitButton = document.querySelector("#submit-button");
const dropzoneLabel = document.querySelector(".dropzone__label");
const resetButton = document.querySelector(".filters__action");
const modeButtons = document.querySelectorAll(".mode-switch__item");
const progressValue = document.querySelector("#progress-value");
const progressSummary = document.querySelector("#progress-summary");
const pipelineItems = document.querySelectorAll(".pipeline-item");
const reviewPanel = document.querySelector("#review-panel");
const reviewIssueCount = document.querySelector("#review-issue-count");
const reviewSummary = document.querySelector("#review-summary");
const reviewIssues = document.querySelector("#review-issues");
const reviewFields = document.querySelector("#review-fields");
const queueCount = document.querySelector("#queue-count");
const readyCount = document.querySelector("#ready-count");
const queueList = document.querySelector("#queue-list");
const readyList = document.querySelector("#ready-list");
const selectedJobName = document.querySelector("#selected-job-name");
const selectedJobMessage = document.querySelector("#selected-job-message");
const selectedJobStatus = document.querySelector("#selected-job-status");
const selectedJobPosition = document.querySelector("#selected-job-position");

let selectedJobId = null;
let pollTimer = null;

const idleSummary = "Выберите задачу в очереди, чтобы смотреть прогресс и детали именно по ней.";
const selectedFieldsSummary =
  "После проверки здесь появятся замечания и поля, которые сервис успел понять.";
const statusLabels = {
  queued: "В очереди",
  running: "В работе",
  completed: "Готово",
  needs_revision: "Нужна доработка",
  failed: "Ошибка",
  idle: "Ожидание",
};
const fieldLabels = {
  client_name: "Клиент",
  inn_client: "ИНН заказчика",
  analysis_period: "Период анализа",
  product_words: "Товарные позиции",
  regions: "Регионы",
  okved_list: "ОКВЭД",
  exclusions: "Исключения",
};

const fallbackDownloadName = (job) =>
  job.status === "completed"
    ? job.filename.replace(/\.xlsx$/i, "_script.ipynb")
    : job.filename.replace(/\.xlsx$/i, "_report.html");

const setStatus = (message, mode = "idle") => {
  statusBox.dataset.mode = mode;
  statusBox.querySelector("p").textContent = message;
};

const stopPolling = () => {
  if (pollTimer) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }
};

const schedulePolling = (delay = 1200) => {
  stopPolling();
  pollTimer = window.setTimeout(() => {
    refreshJobs().catch((error) => {
      setStatus(error.message || "Не удалось обновить список задач", "error");
      schedulePolling(2500);
    });
  }, delay);
};

const resetPipelineView = () => {
  progressValue.textContent = "0%";
  progressSummary.textContent = idleSummary;
  pipelineItems.forEach((item) => {
    item.dataset.status = "pending";
    const detailNode = item.querySelector("p");
    detailNode.textContent = detailNode.dataset.default || detailNode.textContent;
  });
};

const hideReview = () => {
  reviewPanel.hidden = true;
  reviewIssueCount.textContent = "0 замечаний";
  reviewSummary.textContent = selectedFieldsSummary;
  reviewIssues.innerHTML = "";
  reviewFields.innerHTML = "";
};

const formatFieldValue = (value) => {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "Не выделено";
  }
  return value || "Не выделено";
};

const severityLabel = (severity) => ({
  critical: "Критично",
  warning: "Нужно уточнить",
  recommendation: "Рекомендация",
}[severity] || severity);

const renderReview = (review) => {
  reviewPanel.hidden = false;
  reviewIssueCount.textContent = `${review.issues.length} замечаний`;
  reviewSummary.textContent =
    "Сервис остановил обработку именно этой задачи. Исправьте замечания и добавьте обновленный бриф в очередь.";

  reviewIssues.innerHTML = "";
  review.issues.forEach((issue) => {
    const item = document.createElement("article");
    item.className = "review-issue";

    const meta = document.createElement("div");
    meta.className = "review-issue__meta";
    const badge = document.createElement("span");
    badge.className = "review-issue__badge";
    badge.dataset.severity = issue.severity;
    badge.textContent = severityLabel(issue.severity);
    meta.appendChild(badge);

    const title = document.createElement("strong");
    title.textContent = issue.title;
    const detail = document.createElement("p");
    detail.textContent = issue.detail;

    item.append(meta, title, detail);
    reviewIssues.appendChild(item);
  });

  reviewFields.innerHTML = "";
  Object.entries(review.extracted_fields || {}).forEach(([key, value]) => {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = fieldLabels[key] || key;
    const description = document.createElement("dd");
    description.textContent = formatFieldValue(value);
    row.append(term, description);
    reviewFields.appendChild(row);
  });
};

const setSelectedFiles = (files) => {
  if (!files.length) {
    fileName.textContent = "Перетащите Excel-брифы сюда или выберите файлы";
    fileCaption.textContent =
      "После отправки каждый бриф появится в очереди. Готовые notebook останутся в отдельном разделе и будут доступны для скачивания.";
    selectedFilesBox.hidden = true;
    selectedFilesBox.innerHTML = "";
    batchHintCount.textContent = "До 10 файлов";
    setStatus("Ожидаю Excel-брифы для запуска обработки.");
    return;
  }

  fileName.textContent =
    files.length === 1 ? files[0].name : `Выбрано файлов: ${files.length}`;
  fileCaption.textContent =
    files.length === 1
      ? "Файл принят. Можно добавить его в очередь."
      : "Пакет принят. После отправки сервис поставит все брифы в очередь и начнет последовательную обработку.";
  selectedFilesBox.hidden = false;
  selectedFilesBox.innerHTML = "";
  files.forEach((file) => {
    const item = document.createElement("span");
    item.className = "selected-files__item";
    item.textContent = file.name;
    selectedFilesBox.appendChild(item);
  });
  batchHintCount.textContent = `${files.length} файл${files.length === 1 ? "" : files.length < 5 ? "а" : "ов"}`;
  setStatus("Файлы приняты. Можно добавить их в очередь.");
};

const setPipelineState = (steps) => {
  pipelineItems.forEach((item) => {
    const step = steps[Number(item.dataset.step)];
    item.dataset.status = step?.status || "pending";
    const detailNode = item.querySelector("p");
    if (step?.detail) {
      detailNode.textContent = step.detail;
    } else {
      detailNode.textContent = detailNode.dataset.default || detailNode.textContent;
    }
  });
};

const setSelectedJobMeta = (job) => {
  if (!job) {
    selectedJobName.textContent = "Нет активной задачи";
    selectedJobMessage.textContent =
      "Выберите элемент из очереди или загрузите новые брифы, чтобы смотреть прогресс и замечания по конкретной задаче.";
    selectedJobStatus.textContent = statusLabels.idle;
    selectedJobStatus.dataset.status = "idle";
    selectedJobPosition.textContent = "Очередь не сформирована";
    return;
  }

  selectedJobName.textContent = job.filename;
  selectedJobMessage.textContent = job.message || "Задача создана.";
  selectedJobStatus.textContent = statusLabels[job.status] || job.status;
  selectedJobStatus.dataset.status = job.status;
  if (job.status === "queued" && job.queue_position) {
    selectedJobPosition.textContent = `Позиция в очереди: ${job.queue_position}`;
  } else if (job.status === "completed") {
    selectedJobPosition.textContent = "Notebook собран и доступен в разделе готовых файлов";
  } else if (job.status === "needs_revision") {
    selectedJobPosition.textContent = "Генерация остановлена до исправления замечаний. Можно скачать отчет.";
  } else if (job.status === "failed") {
    selectedJobPosition.textContent = "Сервис завершил задачу с ошибкой. Можно скачать отчет.";
  } else {
    selectedJobPosition.textContent = "Задача обрабатывается";
  }
};

const renderSelectedJob = (job) => {
  setSelectedJobMeta(job);
  if (!job) {
    resetPipelineView();
    hideReview();
    return;
  }

  progressValue.textContent = `${job.progress}%`;
  progressSummary.textContent = job.message || idleSummary;
  setPipelineState(job.steps || []);

  if (job.review) {
    renderReview(job.review);
  } else {
    hideReview();
  }
};

const setSelectedJob = (jobId) => {
  selectedJobId = jobId;
  document.querySelectorAll(".job-item").forEach((item) => {
    item.dataset.selected = item.dataset.jobId === jobId ? "true" : "false";
  });
};

const downloadResult = async (downloadUrl, fallbackName = "b2b_script.ipynb") => {
  const response = await fetch(downloadUrl);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Не удалось скачать notebook" }));
    throw new Error(payload.error || "Не удалось скачать notebook");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/);
  const asciiMatch = disposition.match(/filename="([^"]+)"/);
  const downloadName = utfMatch
    ? decodeURIComponent(utfMatch[1])
    : asciiMatch
      ? asciiMatch[1]
      : fallbackName;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return downloadName;
};

const createJobItem = (job, mode) => {
  const article = document.createElement("article");
  article.className = "job-item";
  article.dataset.jobId = job.job_id;
  article.dataset.status = job.status;
  article.dataset.selected = job.job_id === selectedJobId ? "true" : "false";

  const mainButton = document.createElement("button");
  mainButton.type = "button";
  mainButton.className = "job-item__main";
  mainButton.addEventListener("click", () => {
    setSelectedJob(job.job_id);
    refreshSelectedJob().catch((error) => {
      setStatus(error.message || "Не удалось загрузить детали задачи", "error");
    });
  });

  const title = document.createElement("strong");
  title.textContent = job.filename;
  const meta = document.createElement("div");
  meta.className = "job-item__meta";

  const badge = document.createElement("span");
  badge.className = "job-item__badge";
  badge.dataset.status = job.status;
  badge.textContent = statusLabels[job.status] || job.status;

  const message = document.createElement("p");
  if (job.status === "queued" && job.queue_position) {
    message.textContent = `Позиция ${job.queue_position}. ${job.message || ""}`.trim();
  } else {
    message.textContent = job.message || "Задача создана.";
  }

  meta.appendChild(badge);
  if (job.queue_position && mode === "queue") {
    const position = document.createElement("span");
    position.className = "job-item__position";
    position.textContent = `#${job.queue_position}`;
    meta.appendChild(position);
  }

  mainButton.append(title, meta, message);
  article.appendChild(mainButton);

  if (job.download_url) {
    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.className = "job-item__download";
    downloadButton.textContent = job.status === "completed" ? "Скачать" : "Скачать отчет";
    downloadButton.addEventListener("click", async () => {
      try {
        const downloadName = await downloadResult(job.download_url, fallbackDownloadName(job));
        setStatus(`Скачан файл ${downloadName}.`, "success");
      } catch (error) {
        setStatus(error.message || "Не удалось скачать файл", "error");
      }
    });
    article.appendChild(downloadButton);
  }

  return article;
};

const renderJobCollection = (container, jobs, mode, emptyTitle, emptyDetail) => {
  container.innerHTML = "";
  if (!jobs.length) {
    const empty = document.createElement("article");
    empty.className = "job-empty";
    const title = document.createElement("strong");
    title.textContent = emptyTitle;
    const detail = document.createElement("p");
    detail.textContent = emptyDetail;
    empty.append(title, detail);
    container.appendChild(empty);
    return;
  }

  jobs.forEach((job) => {
    container.appendChild(createJobItem(job, mode));
  });
};

const deriveStatusMode = (job) => {
  if (!job) {
    return "idle";
  }
  if (job.status === "running" || job.status === "queued") {
    return "busy";
  }
  if (job.status === "completed") {
    return "success";
  }
  if (job.status === "failed") {
    return "error";
  }
  if (job.status === "needs_revision") {
    return "review";
  }
  return "idle";
};

const chooseDefaultJob = (jobs) =>
  jobs.find((job) => job.status === "running") ||
  jobs.find((job) => job.status === "queued") ||
  jobs.find((job) => job.status === "needs_revision") ||
  jobs.find((job) => job.status === "failed") ||
  jobs.find((job) => job.status === "completed") ||
  null;

const refreshSelectedJob = async () => {
  if (!selectedJobId) {
    renderSelectedJob(null);
    return;
  }

  const response = await fetch(`/api/jobs/${selectedJobId}`);
  if (!response.ok) {
    if (response.status === 404) {
      selectedJobId = null;
      renderSelectedJob(null);
      return;
    }
    const payload = await response.json().catch(() => ({ error: "Не удалось получить статус задачи" }));
    throw new Error(payload.error || "Не удалось получить статус задачи");
  }

  const payload = await response.json();
  renderSelectedJob(payload);
  setStatus(payload.message || "Состояние задач обновлено.", deriveStatusMode(payload));
};

const refreshJobs = async () => {
  const response = await fetch("/api/jobs");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Не удалось получить очередь задач" }));
    throw new Error(payload.error || "Не удалось получить очередь задач");
  }

  const payload = await response.json();
  const allJobs = payload.jobs || [];
  const queueJobs = allJobs.filter((job) => job.status !== "completed");
  const readyJobs = allJobs.filter((job) => job.status === "completed").slice().reverse();

  queueCount.textContent = `${queueJobs.length} задач`;
  readyCount.textContent = `${readyJobs.length} файлов`;

  renderJobCollection(
    queueList,
    queueJobs,
    "queue",
    "Очередь пуста",
    "Добавьте один или несколько `.xlsx`, и здесь появятся задачи с прогрессом и статусами."
  );
  renderJobCollection(
    readyList,
    readyJobs,
    "ready",
    "Пока пусто",
    "Когда обработка завершится успешно, готовые `.ipynb` появятся здесь."
  );

  const stillExists = allJobs.some((job) => job.job_id === selectedJobId);
  if (!stillExists) {
    const nextJob = chooseDefaultJob(queueJobs.length ? queueJobs : readyJobs);
    selectedJobId = nextJob?.job_id || null;
  }

  document.querySelectorAll(".job-item").forEach((item) => {
    item.dataset.selected = item.dataset.jobId === selectedJobId ? "true" : "false";
  });

  await refreshSelectedJob();

  const hasActiveJobs = allJobs.some((job) => ["queued", "running"].includes(job.status));
  schedulePolling(hasActiveJobs ? 1200 : 3000);
};

const addDroppedFiles = (files) => {
  const transfer = new DataTransfer();
  files.forEach((file) => transfer.items.add(file));
  input.files = transfer.files;
  setSelectedFiles([...transfer.files]);
};

input.addEventListener("change", () => {
  setSelectedFiles([...input.files]);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzoneLabel.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzoneLabel.dataset.drag = "true";
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzoneLabel.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzoneLabel.dataset.drag = "false";
  });
});

dropzoneLabel.addEventListener("drop", (event) => {
  const files = [...event.dataTransfer.files].filter((file) => /\.xlsx$/i.test(file.name));
  if (!files.length) {
    return;
  }
  addDroppedFiles(files);
});

resetButton.addEventListener("click", () => {
  input.value = "";
  setSelectedFiles([]);
  setStatus("Выбор файлов очищен. Очередь и готовые notebook сохранены.", "idle");
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    modeButtons.forEach((item) => item.classList.remove("mode-switch__item--active"));
    button.classList.add("mode-switch__item--active");
    const target = document.getElementById(button.dataset.target);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const files = [...input.files];
  if (!files.length) {
    setStatus("Сначала выберите хотя бы один Excel-бриф.", "error");
    return;
  }

  submitButton.disabled = true;
  setStatus("Загружаю пакет брифов и добавляю задачи в очередь...", "busy");

  const payload = new FormData();
  files.forEach((file) => payload.append("brief", file));

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: payload,
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({ error: "Не удалось поставить задачи в очередь" }));
      throw new Error(errorPayload.error || "Не удалось поставить задачи в очередь");
    }

    const batch = await response.json();
    const acceptedJobs = batch.jobs || [];
    if (acceptedJobs.length) {
      selectedJobId = acceptedJobs[0].job_id;
    }

    input.value = "";
    setSelectedFiles([]);
    setStatus(`В очередь добавлено задач: ${acceptedJobs.length}.`, "success");
    await refreshJobs();
  } catch (error) {
    setStatus(error.message || "Не удалось поставить задачи в очередь", "error");
  } finally {
    submitButton.disabled = false;
  }
});

resetPipelineView();
hideReview();
setSelectedFiles([]);
refreshJobs().catch((error) => {
  setStatus(error.message || "Не удалось получить начальное состояние очереди", "error");
});
