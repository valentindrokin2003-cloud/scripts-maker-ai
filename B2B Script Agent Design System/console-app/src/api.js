/* =============================================================================
   API client — talks to your Flask backend
   Endpoints (already implemented in your scripts-maker-ai repo):
     GET    /api/jobs
     GET    /api/jobs/:id
     POST   /api/generate          (FormData with "briefs" file fields)
     DELETE /api/jobs/:id/cancel
   ============================================================================= */

const json = async (resp, fallbackMsg) => {
  if (!resp.ok) {
    const payload = await resp.json().catch(() => ({}));
    throw new Error(payload.error || fallbackMsg);
  }
  return resp.json();
};

export async function fetchJobs() {
  const data = await json(await fetch("/api/jobs"), "Не удалось получить очередь");
  // Backend may return either { jobs: [...] } or just [...]
  return Array.isArray(data?.jobs) ? data.jobs : (Array.isArray(data) ? data : []);
}

export async function fetchJob(jobId) {
  return json(await fetch(`/api/jobs/${jobId}`), "Не удалось загрузить детали задачи");
}

export async function submitBriefs(files) {
  const fd = new FormData();
  files.forEach((f) => fd.append("brief", f, f.name));
  return json(
    await fetch("/api/generate", { method: "POST", body: fd }),
    "Не удалось поставить брифы в очередь"
  );
}

export async function cancelJob(jobId) {
  return json(
    await fetch(`/api/jobs/${jobId}/cancel`, { method: "DELETE" }),
    "Не удалось отменить задачу"
  );
}
