import { useEffect, useMemo, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import Footer from "./components/Footer.jsx";
import HomePage from "./pages/HomePage.jsx";
import QueuePage from "./pages/QueuePage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import HelpPage from "./pages/HelpPage.jsx";
import { PAGE_META, STATUS_LABEL, SEED_JOBS } from "./data.js";
import { fetchJobs, submitBriefs } from "./api.js";

/**
 * Routing: hash-based. URL like /#/queue is parsed into state.page.
 * If you want clean URLs without #, swap to history.pushState + a real router.
 */
function parseHash() {
  const m = (window.location.hash || "").match(/^#\/(home|queue|analytics|help)$/);
  return m ? m[1] : "home";
}

export default function App() {
  const [page, setPage] = useState(parseHash);
  const [jobs, setJobs] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [filter, setFilter] = useState("all");
  const [files, setFiles] = useState([]);
  const [uploadError, setUploadError] = useState(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  /* ------------------------------------------------------------- routing */
  const onNav = (next) => {
    setPage(next);
    window.location.hash = "#/" + next;
    window.scrollTo({ top: 0 });
  };
  useEffect(() => {
    const onHash = () => setPage(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  /* ---------------------------------------------------------- jobs poll */
  useEffect(() => {
    let cancelled = false;
    let timer;

    const tick = async () => {
      try {
        const list = await fetchJobs();
        if (cancelled) return;
        setJobs(list);
        setBackendDown(false);
        if (list.length && !selectedId) setSelectedId(list[0].job_id);
      } catch (err) {
        // If backend not reachable (dev mode without Flask running),
        // fall back to seed data once so the UI is still demoable.
        if (!cancelled && !backendDown) {
          setBackendDown(true);
          setJobs(SEED_JOBS);
          setSelectedId(SEED_JOBS[0].job_id);
        }
      } finally {
        if (!cancelled) timer = setTimeout(tick, 3000);
      }
    };

    tick();
    return () => { cancelled = true; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ------------------------------------------------------------ counts */
  const counts = useMemo(() => {
    const c = {};
    for (const k of Object.keys(STATUS_LABEL)) c[k] = 0;
    jobs.forEach((j) => { c[j.status] = (c[j.status] || 0) + 1; });
    return c;
  }, [jobs]);

  /* ----------------------------------------------------------- upload */
  const handleSubmit = async () => {
    if (!files.length) return;
    setUploadBusy(true);
    setUploadError(null);
    try {
      await submitBriefs(files);
      setFiles([]);
      // refresh immediately after upload
      const list = await fetchJobs();
      setJobs(list);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadBusy(false);
    }
  };

  const meta = PAGE_META[page];

  return (
    <div className="app">
      <Sidebar page={page} onNav={onNav} counts={counts} />
      <main className="main">
        <Topbar title={meta.title} subtitle={meta.subtitle} />

        {backendDown && (
          <div style={{
            margin: "0 0 20px",
            padding: "10px 14px",
            borderRadius: 12,
            background: "var(--amber-soft)",
            color: "#7a5400",
            fontSize: 13, fontWeight: 600,
          }}>
            Бэкенд недоступен — показываю демо-данные. Запустите Flask и обновите страницу.
          </div>
        )}

        {page === "home" && (
          <HomePage counts={counts} jobs={jobs} onSelect={setSelectedId} onNav={onNav} />
        )}
        {page === "queue" && (
          <QueuePage
            jobs={jobs}
            selectedId={selectedId}
            onSelect={setSelectedId}
            filter={filter}
            onFilter={setFilter}
            files={files}
            onPick={setFiles}
            onSubmit={handleSubmit}
            uploadError={uploadError}
            uploadBusy={uploadBusy}
          />
        )}
        {page === "analytics" && (
          <AnalyticsPage counts={counts} onNav={onNav} />
        )}
        {page === "help" && (
          <HelpPage />
        )}

        <Footer />
      </main>
    </div>
  );
}
