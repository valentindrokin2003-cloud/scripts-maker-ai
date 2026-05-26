import { useRef } from "react";
import UploadSection from "../components/UploadSection.jsx";
import Queue from "../components/Queue.jsx";
import PipelineCard from "../components/PipelineCard.jsx";
import Templates from "../components/Templates.jsx";

export default function QueuePage({
  jobs, selectedId, onSelect, filter, onFilter,
  files, onPick, onSubmit, uploadError, uploadBusy,
}) {
  const dropRef = useRef(null);
  const selected = jobs.find((j) => j.job_id === selectedId) || null;

  return (
    <div>
      <div className="section">
        <UploadSection
          files={files}
          onPick={onPick}
          onSubmit={onSubmit}
          error={uploadError}
          busy={uploadBusy}
          dropRef={dropRef}
        />
      </div>
      <div className="section split">
        <Queue
          jobs={jobs}
          filter={filter}
          onFilter={onFilter}
          selectedId={selectedId}
          onSelect={onSelect}
          subtitle="Выберите задачу — её прогресс появится справа."
        />
        <PipelineCard job={selected} />
      </div>
      <Templates />
    </div>
  );
}
