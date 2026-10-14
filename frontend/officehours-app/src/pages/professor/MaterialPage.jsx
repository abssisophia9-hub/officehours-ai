import { useEffect, useId, useRef, useState } from "react";
import { api, apiUpload } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useProfessorData, waitingUploads } from "./ProfessorData.jsx";

const STATUS_LABEL = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  partly_approved: "Partly approved",
};

const STATUS_RANK = {
  pending: 0,
  partly_approved: 1,
  approved: 2,
  rejected: 3,
};

function needsApproval(upload) {
  return upload.status === "pending" || upload.status === "partly_approved";
}

function canvasStatusLine(info) {
  if (!info) return "Checking Canvas…";
  if (info.mode === "live") return "Connected to Canvas";
  if (info.mode === "local" && info.canvas_course_id) {
    return "Connected to the demo Canvas mirror";
  }
  return "Canvas isn't connected";
}

function sortedUploads(uploads) {
  return [...uploads].sort(
    (a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9),
  );
}

export default function MaterialPage() {
  const { token, activeCourse } = useAuth();
  const { uploads, entries, canvasInfo, error, setError, ready, reload } = useProfessorData();
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState("");
  const [rowNotes, setRowNotes] = useState({});
  const [openMenu, setOpenMenu] = useState(null);
  const [reviewId, setReviewId] = useState(null);
  const [rejectId, setRejectId] = useState(null);
  const [busyId, setBusyId] = useState("");
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importNote, setImportNote] = useState("");
  const [materialTitle, setMaterialTitle] = useState("");
  const [materialContent, setMaterialContent] = useState("");
  const [pasting, setPasting] = useState(false);

  useEffect(() => {
    setDuplicateWarning("");
    setRowNotes({});
    setOpenMenu(null);
    setReviewId(null);
    setRejectId(null);
    setCanvasOpen(false);
    setPasteOpen(false);
    setImportNote("");
    setMaterialTitle("");
    setMaterialContent("");
  }, [activeCourse?.id]);

  const waiting = waitingUploads(uploads);
  const rows = sortedUploads(uploads);
  const statusLine = !ready
    ? "Loading material…"
    : error && uploads.length === 0
      ? "Files could not be loaded."
      : waiting.length === 1
        ? "1 file waits for your approval. Students can't see it yet."
        : waiting.length > 1
          ? `${waiting.length} files wait for your approval. Students can't see them yet.`
          : "Everything is approved.";

  function note(uploadId, text) {
    setRowNotes((prev) => ({ ...prev, [uploadId]: text }));
  }

  async function uploadChosen(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const known = new Set(uploads.map((item) => (item.filename || "").toLowerCase()));
    const dupes = files.filter((file) => known.has(file.name.toLowerCase()));
    if (dupes.length === 1) {
      setDuplicateWarning(
        `${dupes[0].name} is already in this list. This upload is a separate copy. Students can't see it until you approve it.`,
      );
    } else if (dupes.length > 1) {
      setDuplicateWarning(
        `${dupes.map((file) => file.name).join(", ")} are already in this list. Each upload is a separate copy. Students can't see them until you approve them.`,
      );
    } else {
      setDuplicateWarning("");
    }
    setUploading(true);
    setError("");
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("course_id", String(activeCourse.id));
        formData.append("auto_approve", "false");
        formData.append("file", file);
        const result = await apiUpload("/knowledge/materials/upload", { token, formData });
        if (result.upload_id) {
          note(
            result.upload_id,
            "Uploaded. Students can't see it until you approve it.",
          );
        }
      }
      await reload();
    } catch (err) {
      setError(err.message || "The upload failed. Try again.");
    } finally {
      setUploading(false);
    }
  }

  async function approveUpload(upload) {
    setBusyId(upload.upload_id);
    setError("");
    setRejectId(null);
    try {
      const result = await api(`/knowledge/uploads/${upload.upload_id}/approve`, {
        method: "POST",
        token,
      });
      const seen = result.approved_count ?? upload.chunk_count;
      await reload();
      note(
        upload.upload_id,
        `Approved. Students can now see ${seen} of ${seen} chunks.`,
      );
    } catch (err) {
      setError(err.message || "Could not approve that file.");
    } finally {
      setBusyId("");
    }
  }

  async function rejectUpload(upload) {
    setBusyId(upload.upload_id);
    setError("");
    try {
      await api(`/knowledge/uploads/${upload.upload_id}/reject`, {
        method: "POST",
        token,
      });
      setRejectId(null);
      await reload();
      note(upload.upload_id, "Rejected. Students can't see this file.");
    } catch (err) {
      setError(err.message || "Could not reject that file.");
    } finally {
      setBusyId("");
    }
  }

  async function approveChunk(entry, upload) {
    setBusyId(`chunk-${entry.id}`);
    setError("");
    try {
      await api(`/knowledge/${entry.id}`, {
        method: "PATCH",
        token,
        body: { status: "approved" },
      });
      const next = Math.min(upload.chunk_count, (upload.approved_count || 0) + 1);
      await reload();
      note(
        upload.upload_id,
        `Approved. Students can now see ${next} of ${upload.chunk_count} chunks.`,
      );
    } catch (err) {
      setError(err.message || "Could not approve that chunk.");
    } finally {
      setBusyId("");
    }
  }

  async function importCanvas() {
    setImporting(true);
    setError("");
    setImportNote("");
    try {
      const result = await api("/knowledge/canvas/sync", {
        method: "POST",
        token,
        body: { course_id: activeCourse.id, auto_approve: false },
      });
      if ((result.chunks_created || 0) > 0) {
        setImportNote(
          "Imported. These files are pending. Students can't see them until you approve each one.",
        );
      } else {
        setImportNote("No new Canvas files. Students only see what you already approved.");
      }
      await reload();
    } catch (err) {
      setError(err.message || "Could not import from Canvas.");
    } finally {
      setImporting(false);
    }
  }

  async function pasteMaterial(event) {
    event.preventDefault();
    setPasting(true);
    setError("");
    try {
      const result = await api("/knowledge/materials", {
        method: "POST",
        token,
        body: {
          title: materialTitle,
          content: materialContent,
          course_id: activeCourse.id,
          course: activeCourse.code,
          source: "slides",
          auto_approve: false,
        },
      });
      if (result.upload_id) {
        note(result.upload_id, "Saved. Students can't see it until you approve it.");
      }
      setMaterialTitle("");
      setMaterialContent("");
      setPasteOpen(false);
      await reload();
    } catch (err) {
      setError(err.message || "Could not save that text.");
    } finally {
      setPasting(false);
    }
  }

  const canvasFiles = canvasInfo?.available_files || [];

  return (
    <div className="pf-page">
      <header className="pf-head">
        <h1>Material</h1>
        <button
          type="button"
          className="btn-primary pf-primary"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? "Uploading…" : "Upload file"}
        </button>
        <input
          ref={fileRef}
          className="pf-file-input"
          type="file"
          tabIndex={-1}
          accept=".pdf,.docx,.txt,.md,.vtt,.srt"
          onChange={(event) => {
            const chosen = Array.from(event.target.files || []);
            event.target.value = "";
            uploadChosen(chosen);
          }}
        />
      </header>

      <p className={`pf-status${waiting.length ? " pf-status-wait" : ""}`} role="status">
        {statusLine}
      </p>
      {error ? (
        <p className="pf-error" role="alert">
          {error}
        </p>
      ) : null}
      {duplicateWarning ? (
        <p className="pf-warn" role="status">
          {duplicateWarning}
        </p>
      ) : null}

      {ready && rows.length === 0 ? <p className="pf-line">No files yet.</p> : null}

      {rows.length > 0 ? (
        <div className="pf-files" role="table" aria-label="Course material">
          <div className="pf-file pf-file-head" role="row">
            <span role="columnheader">File</span>
            <span role="columnheader">Status</span>
            <span role="columnheader">Students see</span>
            <span role="columnheader">Actions</span>
          </div>
          {rows.map((upload) => (
            <FileRow
              key={upload.upload_id}
              upload={upload}
              entries={entries.filter((entry) => entry.upload_id === upload.upload_id)}
              noteText={rowNotes[upload.upload_id] || ""}
              menuOpen={openMenu === upload.upload_id}
              reviewOpen={reviewId === upload.upload_id}
              rejectOpen={rejectId === upload.upload_id}
              busy={busyId === upload.upload_id}
              chunkBusyId={busyId}
              onToggleMenu={() => {
                setRejectId(null);
                setOpenMenu((current) => (current === upload.upload_id ? null : upload.upload_id));
              }}
              onCloseMenu={() => setOpenMenu(null)}
              onReview={() => {
                setReviewId((current) => (current === upload.upload_id ? null : upload.upload_id));
                setOpenMenu(null);
              }}
              onAskReject={() => {
                setOpenMenu(null);
                setRejectId(upload.upload_id);
              }}
              onCancelReject={() => setRejectId(null)}
              onApprove={() => approveUpload(upload)}
              onReject={() => rejectUpload(upload)}
              onApproveChunk={(entry) => approveChunk(entry, upload)}
            />
          ))}
        </div>
      ) : null}

      <div className="pf-secondary">
        <button
          type="button"
          className="pf-quiet"
          aria-expanded={canvasOpen}
          onClick={() => setCanvasOpen((open) => !open)}
        >
          Import from Canvas
        </button>
        <button
          type="button"
          className="pf-quiet"
          aria-expanded={pasteOpen}
          onClick={() => setPasteOpen((open) => !open)}
        >
          Paste text
        </button>
      </div>

      {canvasOpen ? (
        <section className="pf-panel" aria-label="Import from Canvas">
          <p>{canvasStatusLine(canvasInfo)}</p>
          {canvasFiles.length > 0 ? (
            <p className="pf-line">
              {canvasFiles.length === 1 ? "1 Canvas file" : `${canvasFiles.length} Canvas files`}
            </p>
          ) : null}
          {canvasFiles.length > 0 ? (
            <ul className="pf-plain-list">
              {canvasFiles.map((file) => (
                <li key={file.external_id}>
                  {file.module ? `${file.module}. ` : ""}
                  {file.title}
                </li>
              ))}
            </ul>
          ) : null}
          <button type="button" className="btn-ghost pf-btn" disabled={importing} onClick={importCanvas}>
            {importing ? "Importing…" : "Import"}
          </button>
          {importNote ? (
            <p className="pf-note" role="status">
              {importNote}
            </p>
          ) : null}
        </section>
      ) : null}

      {pasteOpen ? (
        <form className="pf-panel" onSubmit={pasteMaterial} aria-label="Paste text">
          <label className="pf-label">
            Title
            <input
              className="field-glass"
              value={materialTitle}
              onChange={(event) => setMaterialTitle(event.target.value)}
              required
              minLength={2}
            />
          </label>
          <label className="pf-label">
            Text
            <textarea
              className="field-glass"
              value={materialContent}
              onChange={(event) => setMaterialContent(event.target.value)}
              required
              minLength={20}
              rows={6}
            />
          </label>
          <button type="submit" className="btn-ghost pf-btn" disabled={pasting}>
            {pasting ? "Saving…" : "Add this text"}
          </button>
        </form>
      ) : null}
    </div>
  );
}

function FileRow({
  upload,
  entries,
  noteText,
  menuOpen,
  reviewOpen,
  rejectOpen,
  busy,
  chunkBusyId,
  onToggleMenu,
  onCloseMenu,
  onReview,
  onAskReject,
  onCancelReject,
  onApprove,
  onReject,
  onApproveChunk,
}) {
  const menuId = useId();
  const menuRef = useRef(null);
  const moreRef = useRef(null);
  const rejectRef = useRef(null);
  const label = STATUS_LABEL[upload.status] || "Pending";
  const waiting = needsApproval(upload);
  const chunks = [...entries].sort(
    (a, b) => (a.page_number || 0) - (b.page_number || 0) || (a.chunk_index || 0) - (b.chunk_index || 0),
  );

  useEffect(() => {
    if (!menuOpen) return undefined;
    menuRef.current?.querySelector("[role='menuitem']")?.focus();
    function onDoc(event) {
      if (menuRef.current?.contains(event.target) || moreRef.current?.contains(event.target)) return;
      onCloseMenu();
    }
    function onKey(event) {
      if (event.key === "Escape") {
        onCloseMenu();
        moreRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen, onCloseMenu]);

  useEffect(() => {
    if (rejectOpen) rejectRef.current?.focus();
  }, [rejectOpen]);

  function onMenuKey(event) {
    const items = [...(menuRef.current?.querySelectorAll("[role='menuitem']") || [])];
    const index = items.indexOf(document.activeElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      items[(index + 1) % items.length]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      items[(index - 1 + items.length) % items.length]?.focus();
    }
  }

  return (
    <article className="pf-file-block">
      <div className="pf-file" role="row">
        <p className="pf-filename" role="cell">
          {upload.filename}
        </p>
        <p className="pf-cell" role="cell">
          <span className={`pf-state${waiting ? " pf-state-wait" : ""}`}>{label}</span>
        </p>
        <p className="pf-cell" role="cell">
          <span className="pf-cell-label">Students see</span>
          {upload.approved_count} of {upload.chunk_count}
        </p>
        <div className="pf-actions" role="cell">
          {waiting ? (
            <button type="button" className="pf-approve" disabled={busy} onClick={onApprove}>
              Approve
            </button>
          ) : null}
          <button
            ref={moreRef}
            type="button"
            className="btn-ghost pf-btn"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            onClick={onToggleMenu}
          >
            More
          </button>
          {menuOpen ? (
            <div ref={menuRef} id={menuId} className="pf-menu" role="menu" onKeyDown={onMenuKey}>
              <button type="button" className="pf-menu-item" role="menuitem" onClick={onReview}>
                {reviewOpen ? "Hide chunks" : "Review chunks"}
              </button>
              {upload.status !== "rejected" ? (
                <button type="button" className="pf-menu-item" role="menuitem" onClick={onAskReject}>
                  Reject
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
      {noteText ? (
        <p className="pf-note" role="status">
          {noteText}
        </p>
      ) : null}
      {rejectOpen ? (
        <div className="pf-confirm" role="alertdialog" aria-label={`Reject ${upload.filename}`}>
          <p>Reject {upload.filename}? Students won't see it.</p>
          <div className="pf-actions">
            <button ref={rejectRef} type="button" className="pf-approve" disabled={busy} onClick={onReject}>
              Reject
            </button>
            <button type="button" className="btn-ghost pf-btn" onClick={onCancelReject}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      {reviewOpen ? (
        <ul className="pf-chunks">
          {chunks.length === 0 ? <li>No chunks loaded for this file.</li> : null}
          {chunks.map((entry) => (
            <li key={entry.id}>
              <p className="pf-chunk-page">
                {entry.page_number != null ? `Page ${entry.page_number}` : "Page —"}
              </p>
              <p className="pf-chunk-text">{entry.answer_draft}</p>
              {entry.status === "approved" ? (
                <p className="pf-line">Approved</p>
              ) : (
                <button
                  type="button"
                  className="pf-approve"
                  disabled={chunkBusyId === `chunk-${entry.id}`}
                  onClick={() => onApproveChunk(entry)}
                >
                  Approve
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
