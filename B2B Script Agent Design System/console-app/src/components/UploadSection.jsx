import { useRef, useState } from "react";
import Icon from "./Icon.jsx";

export default function UploadSection({ files, onPick, onSubmit, error, busy, dropRef }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);

  const handle = (list) => {
    const next = Array.from(list || [])
      .filter((f) => f.name.toLowerCase().endsWith(".xlsx"))
      .slice(0, 10);
    onPick(next);
  };

  return (
    <section className="card" ref={dropRef}>
      <div className="spread">
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--ink)", letterSpacing: "-0.02em" }}>
            Загрузка брифа
          </h2>
          <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--ink-faint)" }}>
            Поддерживаются .xlsx-брифы со стандартной шапкой.
          </p>
        </div>
        <span className="status-pill" data-status="running">7 шагов · DeepSeek</span>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); if (files.length) onSubmit(); }}>
        <div
          className="dz"
          data-drag={drag ? "true" : undefined}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
          style={{ cursor: "pointer" }}
        >
          <div className="dz__icon"><Icon name="upload" size={28} /></div>
          <div>
            <div className="dz__title">
              {files.length ? `Выбрано: ${files.length} из 10` : "Перетащите .xlsx сюда или нажмите для выбора"}
            </div>
            <div className="dz__sub">
              Подходит любой бриф из CRM или ручной выгрузки. Каждый файл попадёт в общую очередь
              и обработается по одному.
            </div>
            {files.length > 0 && (
              <div className="dz__files">
                {files.map((f) => (
                  <span key={f.name} className="dz__chip">
                    <Icon name="file" size={14} /> {f.name}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            className="dz__cta"
            type="submit"
            disabled={!files.length || busy}
            onClick={(e) => e.stopPropagation()}
          >
            {busy
              ? "Отправляем…"
              : (<><Icon name="plus" size={16} /> В очередь</>)}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            multiple
            style={{ display: "none" }}
            onChange={(e) => handle(e.target.files)}
          />
        </div>
      </form>

      <div className="upload-meta">
        <div className="upload-meta__item"><span>Формат</span><strong>.xlsx</strong></div>
        <div className="upload-meta__item"><span>Лимит</span><strong>До 10 файлов</strong></div>
        <div className="upload-meta__item"><span>Обработка</span><strong>Последовательно</strong></div>
        <div className="upload-meta__item"><span>Модель</span><strong>DeepSeek-chat</strong></div>
      </div>

      {error && (
        <div style={{
          marginTop: 12, padding: "12px 14px", borderRadius: 14,
          background: "var(--rose-soft)", color: "var(--rose)",
          fontSize: 13, fontWeight: 600,
        }}>
          {error}
        </div>
      )}
    </section>
  );
}
