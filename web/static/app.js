const MAX_FILES = 10;

const form = document.querySelector("#brief-form");
const input = document.querySelector("#brief-input");
const fileName = document.querySelector("#file-name");
const fileCaption = document.querySelector("#file-caption");
const selectedFilesBox = document.querySelector("#selected-files");
const uploadErrorsBox = document.querySelector("#upload-errors");
const batchHintCount = document.querySelector("#batch-hint-count");
const statusBox = document.querySelector("#status");
const submitButton = document.querySelector("#submit-button");
const dropzoneLabel = document.querySelector(".dropzone__label");
const resetButton = document.querySelector("#reset-button");
const uploadSection = document.querySelector("#upload-section");
const detailsSection = document.querySelector("#details-section");
const progressValue = document.querySelector("#progress-value");
const progressStep = document.querySelector("#progress-step");
const progressSummary = document.querySelector("#progress-summary");
const pipelineItems = document.querySelectorAll(".pipeline-item");
const pipelineCountBadge = document.querySelector("#pipeline-count-badge");
const sidebarStepSummary = document.querySelector("#sidebar-step-summary");
const reviewPanel = document.querySelector("#review-panel");
const reviewIssueCount = document.querySelector("#review-issue-count");
const reviewSummary = document.querySelector("#review-summary");
const reviewIssues = document.querySelector("#review-issues");
const reviewFields = document.querySelector("#review-fields");
const reviewNextSteps = document.querySelector("#review-next-steps");
const reviewActions = document.querySelector("#review-actions");
const queueCount = document.querySelector("#queue-count");
const readyCount = document.querySelector("#ready-count");
const queueList = document.querySelector("#queue-list");
const readyList = document.querySelector("#ready-list");
const queueFilterButtons = [...document.querySelectorAll(".queue-filter")];
const selectedJobName = document.querySelector("#selected-job-name");
const selectedJobMessage = document.querySelector("#selected-job-message");
const selectedJobStatus = document.querySelector("#selected-job-status");
const selectedJobPosition = document.querySelector("#selected-job-position");
const selectedJobUpdated = document.querySelector("#selected-job-updated");
const selectedJobActionStatus = document.querySelector("#selected-job-action-status");
const selectedJobActions = document.querySelector("#selected-job-actions");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

const countNodes = {
  queued: document.querySelector("#count-queued"),
  running: document.querySelector("#count-running"),
  completed: document.querySelector("#count-completed"),
  needs_revision: document.querySelector("#count-needs-revision"),
  failed: document.querySelector("#count-failed"),
  cancelled: document.querySelector("#count-cancelled"),
};

const statusLabels = {
  queued: "В очереди",
  running: "В работе",
  completed: "Готово",
  needs_revision: "Нужна доработка",
  failed: "Ошибка",
  cancelled: "Отменено",
  idle: "Ожидание",
};

const filterLabels = {
  all: "Все",
  running: "В работе",
  queued: "В очереди",
  needs_revision: "Нужна доработка",
  failed: "Ошибка",
  cancelled: "Отменено",
};

const groupLabels = {
  running: "В работе",
  queued: "Ожидают запуска",
  needs_revision: "Нужна доработка",
  failed: "Завершились с ошибкой",
  cancelled: "Отменено",
};

const statusPriority = {
  running: 0,
  queued: 1,
  needs_revision: 2,
  failed: 3,
  cancelled: 4,
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

const severityConfig = {
  critical: {
    label: "Критично",
    title: "Критичные замечания",
  },
  warning: {
    label: "Нужно уточнить",
    title: "Нужно уточнить",
  },
  recommendation: {
    label: "Рекомендации",
    title: "Рекомендации",
  },
};

const idleSummary = "Выберите задачу в очереди, чтобы смотреть прогресс и детали именно по ней.";
const selectedFieldsSummary =
  "После проверки здесь появятся замечания, следующие шаги и поля, которые полезны для исправления.";
const defaultFileCaption =
  "После отправки каждый бриф попадет в очередь. Готовые notebook появятся в отдельном блоке, а проблемные задачи останутся в очереди с деталями и отчетом.";

let selectedJobId = null;
let pollTimer = null;
let activeQueueFilter = "all";
let latestJobs = [];

const fallbackDownloadName = (job) =>
  job.status === "completed"
    ? job.filename.replace(/\.xlsx$/i, "_script.ipynb")
    : job.filename.replace(/\.xlsx$/i, "_report.html");

const pluralizeFiles = (count) => {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return "файл";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return "файла";
  }
  return "файлов";
};

const formatFieldValue = (value) => {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "Не выделено";
  }
  return value || "Не выделено";
};

const hasMeaningfulValue = (value) => {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return Boolean(String(value || "").trim());
};

const formatUpdatedAt = (timestamp) => {
  if (!timestamp) {
    return "Обновление появится после запуска задачи";
  }

  const date = new Date(timestamp * 1000);
  return `Обновлено ${new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)}`;
};

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

const setDashboardCounts = (counts = {}) => {
  Object.entries(countNodes).forEach(([key, node]) => {
    if (node) {
      node.textContent = String(counts[key] || 0);
    }
  });
};

const syncPipelineSummary = () => {
  const stepCount = pipelineItems.length;
  if (pipelineCountBadge) {
    pipelineCountBadge.textContent = `${stepCount} шагов`;
  }
  if (sidebarStepSummary) {
    sidebarStepSummary.textContent = `${stepCount} шагов от проверки Excel-брифа до готового \`.ipynb\`.`;
  }
  if (progressStep) {
    progressStep.textContent = `Шаг 0 из ${stepCount}`;
  }
};

const getCurrentStepInfo = (job) => {
  const total = pipelineItems.length;

  if (!job) {
    return { current: 0, total };
  }

  const steps = job.steps || [];
  const activeIndex = steps.findIndex((step) => ["active", "review", "error"].includes(step.status));
  if (activeIndex >= 0) {
    return { current: activeIndex + 1, total };
  }

  if (job.status === "completed") {
    return { current: total, total };
  }

  const doneCount = steps.filter((step) => step.status === "done").length;
  return { current: Math.min(doneCount, total), total };
};

const resetPipelineView = () => {
  progressValue.textContent = "0%";
  progressStep.textContent = `Шаг 0 из ${pipelineItems.length}`;
  progressSummary.textContent = idleSummary;
  pipelineItems.forEach((item) => {
    item.dataset.status = "pending";
    const detailNode = item.querySelector("p");
    detailNode.textContent = detailNode.dataset.default || detailNode.textContent;
  });
};

const clearSelectedJobActions = () => {
  selectedJobActions.innerHTML = "";
};

const hideReview = () => {
  reviewPanel.hidden = true;
  reviewIssueCount.textContent = "0 замечаний";
  reviewSummary.textContent = selectedFieldsSummary;
  reviewIssues.innerHTML = "";
  reviewFields.innerHTML = "";
  reviewNextSteps.innerHTML = "";
  reviewActions.innerHTML = "";
};

const severityLabel = (severity) => severityConfig[severity]?.label || severity;

const sortQueueJobs = (jobs) =>
  jobs.slice().sort((left, right) => {
    const priorityDelta = (statusPriority[left.status] ?? 99) - (statusPriority[right.status] ?? 99);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }

    if (left.status === "queued" && right.status === "queued") {
      return (left.queue_position || 9999) - (right.queue_position || 9999);
    }

    return (right.updated_at || 0) - (left.updated_at || 0);
  });

const filterQueueJobs = (jobs) => {
  if (activeQueueFilter === "all") {
    return jobs;
  }
  return jobs.filter((job) => job.status === activeQueueFilter);
};

const getQueueGroupOrder = () => ["running", "queued", "needs_revision", "failed", "cancelled"];

const focusDetailsPanel = () => {
  const behavior = prefersReducedMotion.matches ? "auto" : "smooth";
  detailsSection.scrollIntoView({ block: "start", behavior });
  window.requestAnimationFrame(() => {
    detailsSection.focus({ preventScroll: true });
  });
};

const openCorrectedBriefUpload = () => {
  const behavior = prefersReducedMotion.matches ? "auto" : "smooth";
  uploadSection.scrollIntoView({ block: "start", behavior });
  setStatus("Выберите исправленный Excel-бриф и добавьте его в очередь.", "review");
  input.click();
};

const downloadResult = async (downloadUrl, fallbackName = "b2b_script.ipynb") => {
  const response = await fetch(downloadUrl);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Не удалось скачать файл" }));
    throw new Error(payload.error || "Не удалось скачать файл");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/);
  const asciiMatch = disposition.match(/filename=\"([^\"]+)\"/);
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

const createActionButton = ({ label, variant = "secondary", handler }) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = variant === "primary" ? "primary-action primary-action--inline" : "secondary-action";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
};

const handleJobDownload = async (job) => {
  try {
    const downloadName = await downloadResult(job.download_url, fallbackDownloadName(job));
    setStatus(`Скачан файл ${downloadName}.`, "success");
  } catch (error) {
    setStatus(error.message || "Не удалось скачать файл", "error");
  }
};

const handleJobCancel = async (job) => {
  try {
    const response = await fetch(`/api/jobs/${job.job_id}/cancel`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ error: "Не удалось отменить задачу" }));
      throw new Error(payload.error || "Не удалось отменить задачу");
    }
    setStatus("Задача отменена.", "idle");
    await refreshJobs();
  } catch (error) {
    setStatus(error.message || "Не удалось отменить задачу", "error");
  }
};

const getJobActionConfig = (job) => {
  if (!job) {
    return {
      hint: "Действие появится после проверки или завершения задачи.",
      buttons: [],
      queueLabel: "Ожидает загрузки или выбора",
    };
  }

  if (job.status === "completed" && job.download_url) {
    return {
      hint: "Notebook готов. Его можно скачать повторно в любой момент текущей сессии.",
      buttons: [
        {
          label: "Скачать notebook",
          variant: "primary",
          handler: () => handleJobDownload(job),
        },
      ],
      queueLabel: "Скачать notebook",
    };
  }

  if (job.status === "needs_revision") {
    return {
      hint: "Скачайте отчет, исправьте исходный `.xlsx` и загрузите обновленный бриф повторно.",
      buttons: [
        job.download_url
          ? {
              label: "Скачать отчет",
              variant: "primary",
              handler: () => handleJobDownload(job),
            }
          : null,
        {
          label: "Загрузить исправленный бриф",
          variant: "secondary",
          handler: openCorrectedBriefUpload,
        },
      ].filter(Boolean),
      queueLabel: job.download_url ? "Скачать отчет" : "Исправить бриф",
    };
  }

  if (job.status === "failed") {
    return {
      hint: "Скачайте отчет об ошибке, проверьте входные данные и поставьте задачу заново.",
      buttons: job.download_url
        ? [
            {
              label: "Скачать отчет",
              variant: "primary",
              handler: () => handleJobDownload(job),
            },
          ]
        : [],
      queueLabel: job.download_url ? "Скачать отчет" : "Проверить причину",
    };
  }

  if (job.status === "running") {
    return {
      hint: "Задача уже выполняется. Следите за шагами ниже, обновление происходит автоматически.",
      buttons: [
        {
          label: "Отменить задачу",
          variant: "secondary",
          handler: () => handleJobCancel(job),
        },
      ],
      queueLabel: "Смотреть прогресс",
    };
  }

  if (job.status === "queued") {
    return {
      hint: "Задача ожидает запуск. Пока можно следить за позиций в очереди или отменить.",
      buttons: [
        {
          label: "Снять с очереди",
          variant: "secondary",
          handler: () => handleJobCancel(job),
        },
      ],
      queueLabel: "Ждать запуска",
    };
  }

  if (job.status === "cancelled") {
    return {
      hint: "Задача была отменена. Загрузите бриф заново, если нужно повторить обработку.",
      buttons: [],
      queueLabel: "Отменено",
    };
  }

  return {
    hint: "Задача ожидает запуск. Пока можно следить за позицией в очереди и последним сообщением.",
    buttons: [],
    queueLabel: "Ждать запуска",
  };
};

const setPipelineState = (steps) => {
  pipelineItems.forEach((item) => {
    const step = steps[Number(item.dataset.step)];
    item.dataset.status = step?.status || "pending";
    const detailNode = item.querySelector("p");
    detailNode.textContent = step?.detail || detailNode.dataset.default || detailNode.textContent;
  });
};

const setSelectedJobMeta = (job) => {
  clearSelectedJobActions();

  if (!job) {
    selectedJobName.textContent = "Нет активной задачи";
    selectedJobMessage.textContent =
      "Выберите элемент из очереди или загрузите новые брифы, чтобы смотреть прогресс и замечания по конкретной задаче.";
    selectedJobStatus.textContent = statusLabels.idle;
    selectedJobStatus.dataset.status = "idle";
    selectedJobPosition.textContent = "Очередь не сформирована";
    selectedJobUpdated.textContent = "Обновление появится после запуска задачи";
    selectedJobActionStatus.textContent = "Действие появится после проверки или завершения задачи.";
    return;
  }

  const actionConfig = getJobActionConfig(job);

  selectedJobName.textContent = job.filename;
  selectedJobMessage.textContent = job.message || "Задача создана.";
  selectedJobStatus.textContent = statusLabels[job.status] || job.status;
  selectedJobStatus.dataset.status = job.status;
  selectedJobUpdated.textContent = formatUpdatedAt(job.updated_at);
  selectedJobActionStatus.textContent = actionConfig.hint;

  if (job.status === "queued" && job.queue_position) {
    selectedJobPosition.textContent = `Позиция в очереди: ${job.queue_position}`;
  } else if (job.status === "completed") {
    selectedJobPosition.textContent = "Notebook собран и доступен в блоке готовых файлов";
  } else if (job.status === "needs_revision") {
    selectedJobPosition.textContent = "Генерация остановлена до исправления замечаний";
  } else if (job.status === "failed") {
    selectedJobPosition.textContent = "Сервис завершил задачу с ошибкой";
  } else if (job.status === "cancelled") {
    selectedJobPosition.textContent = "Задача отменена пользователем";
  } else {
    selectedJobPosition.textContent = "Задача обрабатывается";
  }

  actionConfig.buttons.forEach((config) => {
    selectedJobActions.appendChild(createActionButton(config));
  });
};

const renderSelectedJob = (job) => {
  setSelectedJobMeta(job);
  if (!job) {
    resetPipelineView();
    hideReview();
    return;
  }

  const { current, total } = getCurrentStepInfo(job);
  progressValue.textContent = `${job.progress}%`;
  progressStep.textContent = `Шаг ${current} из ${total}`;
  progressSummary.textContent = job.message || idleSummary;
  setPipelineState(job.steps || []);

  if (job.review) {
    renderReview(job);
  } else {
    hideReview();
  }
};

const setSelectedJob = (jobId) => {
  selectedJobId = jobId;
  document.querySelectorAll(".job-item").forEach((item) => {
    item.dataset.selected = item.dataset.jobId === jobId ? "true" : "false";
  });
  document.querySelectorAll(".job-item__main").forEach((button) => {
    if (button.dataset.jobId === jobId) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
  });
};

const applyQueueFilter = (filter) => {
  activeQueueFilter = filter;
  queueFilterButtons.forEach((button) => {
    const isSelected = button.dataset.filter === filter;
    button.setAttribute("aria-selected", String(isSelected));
    button.tabIndex = isSelected ? 0 : -1;
    if (isSelected) {
      queueList.setAttribute("aria-labelledby", button.id);
    }
  });
  renderQueueView();
};

const createQueueEmptyState = (title, detail) => {
  const empty = document.createElement("article");
  empty.className = "job-empty";
  const heading = document.createElement("strong");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.textContent = detail;
  empty.append(heading, copy);
  return empty;
};

const createJobItem = (job) => {
  const article = document.createElement("article");
  article.className = "job-item";
  article.dataset.jobId = job.job_id;
  article.dataset.status = job.status;
  article.dataset.selected = job.job_id === selectedJobId ? "true" : "false";

  const mainButton = document.createElement("button");
  mainButton.type = "button";
  mainButton.className = "job-item__main";
  mainButton.dataset.jobId = job.job_id;
  if (job.job_id === selectedJobId) {
    mainButton.setAttribute("aria-current", "true");
  }
  mainButton.addEventListener("click", () => {
    setSelectedJob(job.job_id);
    refreshSelectedJob().catch((error) => {
      setStatus(error.message || "Не удалось загрузить детали задачи", "error");
    });
    focusDetailsPanel();
  });

  const header = document.createElement("div");
  header.className = "job-item__header";
  const title = document.createElement("strong");
  title.textContent = job.filename;
  const badge = document.createElement("span");
  badge.className = "job-item__badge";
  badge.dataset.status = job.status;
  badge.textContent = statusLabels[job.status] || job.status;
  header.append(title, badge);

  const facts = document.createElement("div");
  facts.className = "job-item__facts";

  const position = document.createElement("span");
  position.className = "job-item__position";
  if (job.status === "queued" && job.queue_position) {
    position.textContent = `Позиция ${job.queue_position}`;
  } else if (job.status === "running") {
    position.textContent = "Выполняется сейчас";
  } else if (job.status === "needs_revision") {
    position.textContent = "Ожидает исправлений";
  } else if (job.status === "cancelled") {
    position.textContent = "Отменена";
  } else {
    position.textContent = "Требует внимания";
  }

  const updated = document.createElement("span");
  updated.className = "job-item__updated";
  updated.textContent = formatUpdatedAt(job.updated_at);

  const action = document.createElement("span");
  action.className = "job-item__action";
  action.textContent = getJobActionConfig(job).queueLabel;

  facts.append(position, updated, action);

  const message = document.createElement("p");
  message.className = "job-item__message";
  message.textContent = job.message || "Задача создана.";

  mainButton.append(header, facts, message);
  article.appendChild(mainButton);

  if (job.download_url && ["needs_revision", "failed"].includes(job.status)) {
    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.className = "job-item__download";
    downloadButton.textContent = "Скачать отчет";
    downloadButton.addEventListener("click", () => {
      handleJobDownload(job);
    });
    article.appendChild(downloadButton);
  }

  if (job.cancellable) {
    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "job-item__cancel";
    cancelButton.textContent = job.status === "queued" ? "Снять" : "Отменить";
    cancelButton.addEventListener("click", () => {
      handleJobCancel(job);
    });
    article.appendChild(cancelButton);
  }

  return article;
};

const renderQueueView = () => {
  const queueJobs = sortQueueJobs(latestJobs.filter((job) => job.status !== "completed"));
  const filteredJobs = filterQueueJobs(queueJobs);

  queueList.innerHTML = "";

  if (!queueJobs.length) {
    queueList.appendChild(
      createQueueEmptyState(
        "Очередь пуста",
        "Добавьте один или несколько `.xlsx`, и здесь появятся задачи с прогрессом."
      )
    );
    return;
  }

  if (!filteredJobs.length) {
    queueList.appendChild(
      createQueueEmptyState(
        "Нет задач в выбранном статусе",
        "Смените фильтр или дождитесь следующего обновления очереди."
      )
    );
    return;
  }

  const shouldGroup = activeQueueFilter === "all";
  if (!shouldGroup) {
    filteredJobs.forEach((job) => {
      queueList.appendChild(createJobItem(job));
    });
    return;
  }

  getQueueGroupOrder().forEach((status) => {
    const groupJobs = filteredJobs.filter((job) => job.status === status);
    if (!groupJobs.length) {
      return;
    }

    const section = document.createElement("section");
    section.className = "job-group";
    section.dataset.status = status;

    const header = document.createElement("div");
    header.className = "job-group__header";
    const title = document.createElement("h3");
    title.textContent = groupLabels[status];
    const count = document.createElement("span");
    count.className = "job-group__count";
    count.textContent = `${groupJobs.length}`;
    header.append(title, count);

    const list = document.createElement("div");
    list.className = "job-group__list";
    groupJobs.forEach((job) => {
      list.appendChild(createJobItem(job));
    });

    section.append(header, list);
    queueList.appendChild(section);
  });
};

const renderReadyList = (jobs) => {
  readyList.innerHTML = "";

  if (!jobs.length) {
    readyList.appendChild(
      createQueueEmptyState(
        "Пока пусто",
        "Когда обработка завершится успешно, готовые `.ipynb` появятся здесь."
      )
    );
    return;
  }

  jobs.forEach((job) => {
    const article = document.createElement("article");
    article.className = "job-item";
    article.dataset.jobId = job.job_id;
    article.dataset.status = "completed";
    article.dataset.selected = job.job_id === selectedJobId ? "true" : "false";

    const mainButton = document.createElement("button");
    mainButton.type = "button";
    mainButton.className = "job-item__main";
    mainButton.dataset.jobId = job.job_id;
    if (job.job_id === selectedJobId) {
      mainButton.setAttribute("aria-current", "true");
    }
    mainButton.addEventListener("click", () => {
      setSelectedJob(job.job_id);
      refreshSelectedJob().catch((error) => {
        setStatus(error.message || "Не удалось загрузить детали задачи", "error");
      });
      focusDetailsPanel();
    });

    const header = document.createElement("div");
    header.className = "job-item__header";
    const title = document.createElement("strong");
    title.textContent = job.filename;
    const badge = document.createElement("span");
    badge.className = "job-item__badge";
    badge.dataset.status = "completed";
    badge.textContent = statusLabels.completed;
    header.append(title, badge);

    const facts = document.createElement("div");
    facts.className = "job-item__facts";

    const readyNote = document.createElement("span");
    readyNote.className = "job-item__position";
    readyNote.textContent = "Notebook собран";

    const updated = document.createElement("span");
    updated.className = "job-item__updated";
    updated.textContent = formatUpdatedAt(job.updated_at);

    const action = document.createElement("span");
    action.className = "job-item__action";
    action.textContent = "Скачать notebook";

    facts.append(readyNote, updated, action);

    const message = document.createElement("p");
    message.className = "job-item__message";
    message.textContent = job.message || "Notebook готов к скачиванию.";

    mainButton.append(header, facts, message);

    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.className = "job-item__download";
    downloadButton.textContent = "Скачать";
    downloadButton.addEventListener("click", () => {
      handleJobDownload(job);
    });

    article.append(mainButton, downloadButton);
    readyList.appendChild(article);
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
  if (job.status === "cancelled") {
    return "idle";
  }
  return "idle";
};

const chooseDefaultJob = (jobs) =>
  jobs.find((job) => job.status === "running") ||
  jobs.find((job) => job.status === "needs_revision") ||
  jobs.find((job) => job.status === "queued") ||
  jobs.find((job) => job.status === "failed") ||
  jobs.find((job) => job.status === "completed") ||
  null;

const buildIssueAction = (issue) => {
  if (issue.field_name && fieldLabels[issue.field_name]) {
    return `Исправьте поле «${fieldLabels[issue.field_name]}» в исходном Excel-брифе и загрузите обновленный файл.`;
  }
  if (issue.severity === "critical") {
    return "Исправьте это замечание до повторной загрузки, иначе генерация снова остановится.";
  }
  if (issue.severity === "warning") {
    return "Уточните формулировку в брифе, чтобы сервис смог пройти проверку качества.";
  }
  return "Проверьте рекомендацию перед повторной загрузкой, чтобы снизить риск новой остановки.";
};

const collectReviewFields = (review) => {
  const extractedFields = review.extracted_fields || {};
  const issueFields = review.issues
    .map((issue) => issue.field_name)
    .filter((fieldName) => fieldName && hasMeaningfulValue(extractedFields[fieldName]));
  const fallbackKeys = [
    "client_name",
    "analysis_period",
    "product_words",
    "regions",
    "okved_list",
    "exclusions",
    "inn_client",
  ];

  const seen = new Set();
  const keys = [...issueFields, ...fallbackKeys].filter((key) => {
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return hasMeaningfulValue(extractedFields[key]);
  });

  return keys.slice(0, 6).map((key) => [key, extractedFields[key]]);
};

const buildReviewNextSteps = (review) => {
  const steps = [];
  const criticalCount = review.issues.filter((issue) => issue.severity === "critical").length;
  const warningCount = review.issues.filter((issue) => issue.severity === "warning").length;
  const recommendationCount = review.issues.filter((issue) => issue.severity === "recommendation").length;

  if (criticalCount) {
    steps.push("Сначала исправьте критичные поля в исходном Excel-брифе.");
  }
  if (warningCount) {
    steps.push("Уточните спорные или неполные поля, которые блокируют продолжение пайплайна.");
  }
  if (recommendationCount) {
    steps.push("Проверьте рекомендации, чтобы уменьшить риск повторной остановки.");
  }
  steps.push("Загрузите исправленный `.xlsx` в очередь через верхний блок.");

  return steps;
};

const renderReview = (job) => {
  const review = job.review;
  reviewPanel.hidden = false;
  reviewIssueCount.textContent = `${review.issues.length} замечаний`;
  reviewSummary.textContent =
    "Сервис остановил обработку этой задачи и уже собрал ориентиры для правки. Ниже видно, что именно исправить и что сделать дальше.";

  reviewIssues.innerHTML = "";
  ["critical", "warning", "recommendation"].forEach((severity) => {
    const issues = review.issues.filter((issue) => issue.severity === severity);
    if (!issues.length) {
      return;
    }

    const group = document.createElement("section");
    group.className = "review-issue-group";
    group.dataset.severity = severity;

    const header = document.createElement("div");
    header.className = "review-issue-group__header";
    const title = document.createElement("h5");
    title.textContent = severityConfig[severity].title;
    const count = document.createElement("span");
    count.className = "review-issue-group__count";
    count.textContent = `${issues.length}`;
    header.append(title, count);

    const list = document.createElement("div");
    list.className = "review-issue-group__list";

    issues.forEach((issue) => {
      const item = document.createElement("article");
      item.className = "review-issue";

      const meta = document.createElement("div");
      meta.className = "review-issue__meta";
      const badge = document.createElement("span");
      badge.className = "review-issue__badge";
      badge.dataset.severity = issue.severity;
      badge.textContent = severityLabel(issue.severity);
      meta.appendChild(badge);

      const titleNode = document.createElement("strong");
      titleNode.textContent = issue.title;

      const detail = document.createElement("p");
      detail.textContent = issue.detail;

      const action = document.createElement("p");
      action.className = "review-issue__action";
      action.textContent = buildIssueAction(issue);

      item.append(meta, titleNode, detail, action);
      list.appendChild(item);
    });

    group.append(header, list);
    reviewIssues.appendChild(group);
  });

  reviewFields.innerHTML = "";
  const reviewFieldEntries = collectReviewFields(review);
  if (!reviewFieldEntries.length) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = "Поля для проверки";
    const description = document.createElement("dd");
    description.textContent = "Сервис не сохранил полезные для правки поля. Ориентируйтесь на замечания и отчет.";
    row.append(term, description);
    reviewFields.appendChild(row);
  }

  reviewFieldEntries.forEach(([key, value]) => {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = fieldLabels[key] || key;
    const description = document.createElement("dd");
    description.textContent = formatFieldValue(value);
    row.append(term, description);
    reviewFields.appendChild(row);
  });

  reviewNextSteps.innerHTML = "";
  const stepsTitle = document.createElement("h4");
  stepsTitle.textContent = "Что делать дальше";
  const stepsList = document.createElement("ol");
  buildReviewNextSteps(review).forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    stepsList.appendChild(item);
  });
  reviewNextSteps.append(stepsTitle, stepsList);

  reviewActions.innerHTML = "";
  const actionConfig = getJobActionConfig(job);
  actionConfig.buttons.forEach((config) => {
    reviewActions.appendChild(createActionButton(config));
  });
};

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
  const queueJobs = sortQueueJobs(allJobs.filter((job) => job.status !== "completed"));
  const readyJobs = allJobs.filter((job) => job.status === "completed").slice().reverse();

  latestJobs = allJobs;
  setDashboardCounts(payload.counts || {});
  queueCount.textContent = `${queueJobs.length} задач`;
  readyCount.textContent = `${readyJobs.length} файлов`;

  renderQueueView();
  renderReadyList(readyJobs);

  const stillExists = allJobs.some((job) => job.job_id === selectedJobId);
  if (!stillExists) {
    const nextJob = chooseDefaultJob(queueJobs.length ? queueJobs : readyJobs);
    selectedJobId = nextJob?.job_id || null;
  }

  setSelectedJob(selectedJobId);
  updateQueueFilterLabels(payload.counts || {}, queueJobs.length);
  await refreshSelectedJob();

  const hasActiveJobs = allJobs.some((job) => ["queued", "running"].includes(job.status));
  schedulePolling(hasActiveJobs ? 1200 : 3000);};

const updateQueueFilterLabels = (counts, totalQueueJobs) => {
  queueFilterButtons.forEach((button) => {
    const filter = button.dataset.filter;
    const count = filter === "all" ? totalQueueJobs : counts[filter] || 0;
    button.textContent = `${filterLabels[filter]} · ${count}`;
  });
};

const renderUploadErrors = (errors) => {
  uploadErrorsBox.innerHTML = "";
  uploadErrorsBox.hidden = !errors.length;

  errors.forEach((message) => {
    const item = document.createElement("p");
    item.className = "upload-errors__item";
    item.textContent = message;
    uploadErrorsBox.appendChild(item);
  });
};

const setSelectedFiles = (files) => {
  const count = files.length;
  batchHintCount.textContent = `${count} из ${MAX_FILES} ${pluralizeFiles(MAX_FILES)}`;

  if (!count) {
    fileName.textContent = "Перетащите `.xlsx` сюда или выберите файлы";
    fileCaption.textContent = defaultFileCaption;
    selectedFilesBox.hidden = true;
    selectedFilesBox.innerHTML = "";
    setStatus("Ожидаю Excel-брифы для запуска очереди.");
    return;
  }

  fileName.textContent = count === 1 ? files[0].name : `Выбрано ${count} ${pluralizeFiles(count)}`;
  fileCaption.textContent =
    count === 1
      ? "Файл готов к постановке в очередь."
      : "Пакет готов. После отправки сервис начнет последовательную обработку файлов.";
  selectedFilesBox.hidden = false;
  selectedFilesBox.innerHTML = "";

  files.forEach((file) => {
    const item = document.createElement("span");
    item.className = "selected-files__item";
    item.textContent = file.name;
    selectedFilesBox.appendChild(item);
  });

  setStatus("Файлы приняты. Можно добавить их в очередь.");
};

const validateFiles = (files) => {
  const validFiles = [];
  const errors = [];

  files.forEach((file) => {
    if (!/\.xlsx$/i.test(file.name)) {
      errors.push(`${file.name}: поддерживаются только файлы .xlsx.`);
      return;
    }
    if (file.size === 0) {
      errors.push(`${file.name}: пустой файл, добавьте непустой Excel-бриф.`);
      return;
    }
    validFiles.push(file);
  });

  if (validFiles.length > MAX_FILES) {
    errors.push(`Превышен лимит: можно поставить в очередь не больше ${MAX_FILES} файлов за раз.`);
  }

  return {
    validFiles: validFiles.slice(0, MAX_FILES),
    errors,
  };
};

const syncInputFiles = (files) => {
  const transfer = new DataTransfer();
  files.forEach((file) => transfer.items.add(file));
  input.files = transfer.files;
};

const applyFileSelection = (files) => {
  const { validFiles, errors } = validateFiles(files);

  syncInputFiles(validFiles);
  renderUploadErrors(errors);
  setSelectedFiles(validFiles);

  if (errors.length && validFiles.length) {
    setStatus("Часть файлов не добавлена. Проверьте ограничения и повторите попытку.", "review");
  } else if (errors.length) {
    setStatus("Выбор файлов содержит ошибки. Исправьте их и попробуйте снова.", "error");
  }
};

input.addEventListener("change", () => {
  applyFileSelection([...input.files]);
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
  applyFileSelection([...event.dataTransfer.files]);
});

dropzoneLabel.addEventListener("keydown", (event) => {
  if (!["Enter", " "].includes(event.key)) {
    return;
  }

  event.preventDefault();
  input.click();
});

resetButton.addEventListener("click", () => {
  input.value = "";
  renderUploadErrors([]);
  setSelectedFiles([]);
  setStatus("Выбор файлов очищен. Очередь и готовые notebook сохранены.", "idle");
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
    renderUploadErrors([]);
    setSelectedFiles([]);
    setStatus(`В очередь добавлено задач: ${acceptedJobs.length}.`, "success");
    await refreshJobs();
  } catch (error) {
    setStatus(error.message || "Не удалось поставить задачи в очередь", "error");
  } finally {
    submitButton.disabled = false;
  }
});

queueFilterButtons.forEach((button, index) => {
  button.tabIndex = index === 0 ? 0 : -1;
  button.addEventListener("click", () => {
    applyQueueFilter(button.dataset.filter);
  });
  button.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }

    event.preventDefault();
    const currentIndex = queueFilterButtons.indexOf(button);
    let nextIndex = currentIndex;

    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % queueFilterButtons.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + queueFilterButtons.length) % queueFilterButtons.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = queueFilterButtons.length - 1;
    }

    queueFilterButtons[nextIndex].focus();
    applyQueueFilter(queueFilterButtons[nextIndex].dataset.filter);
  });
});

syncPipelineSummary();
resetPipelineView();
hideReview();
renderUploadErrors([]);
setSelectedFiles([]);
setDashboardCounts();
applyQueueFilter(activeQueueFilter);
refreshJobs().catch((error) => {
  setStatus(error.message || "Не удалось получить начальное состояние очереди", "error");
});
