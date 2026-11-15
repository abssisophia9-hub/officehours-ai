import { useCallback, useEffect, useId, useRef, useState } from "react";
import { API_BASE, api, apiUpload } from "../api/client.js";

function formatBytes(size) {
  if (!size && size !== 0) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchAuthedBlobUrl(path, token) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Could not load file (${response.status})`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

const COURSE_TOPICS = [
  "Trees & red-black",
  "Hashing",
  "Heaps",
  "Amortized analysis",
  "Graphs",
  "Main ideas from class",
  "Other",
];

const PAGE_SIZE = 8;

function parseAbout(about) {
  const text = String(about || "");
  const week = (text.match(/Week\s+(\d+)/i) || [])[1] || "";
  const lecture = (text.match(/Lecture\s+(\d+)/i) || [])[1] || "";
  const topicMatch = text.match(/Topic:\s*([^·|]+)/i);
  const topic = (topicMatch?.[1] || "").trim();
  return { week, lecture, topic, raw: text };
}

function fileTypeOf(note) {
  const name = String(note.original_filename || "").toLowerCase();
  if (note.is_image || /\.(png|jpe?g|webp|gif)$/.test(name)) return "image";
  if (/\.pdf$/.test(name)) return "pdf";
  if (/\.(docx?|txt|md)$/.test(name)) return "doc";
  return "other";
}

export default function PeerNotesFeed({ token, courseId, courseCode }) {
  const [notes, setNotes] = useState([]);
  const [previews, setPreviews] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [week, setWeek] = useState("");
  const [lecture, setLecture] = useState("");
  const [topic, setTopic] = useState(COURSE_TOPICS[0]);
  const [caption, setCaption] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);
  const fileInputId = useId();
  const [openComments, setOpenComments] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentBody, setCommentBody] = useState("");
  const [commentAnon, setCommentAnon] = useState(false);
  const [commentBusy, setCommentBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [filterWeek, setFilterWeek] = useState("");
  const [filterLecture, setFilterLecture] = useState("");
  const [filterTopic, setFilterTopic] = useState("");
  const [filterType, setFilterType] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [mineOnly, setMineOnly] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const loadFeed = useCallback(async () => {
    if (!courseId || !token) return;
    try {
      const feed = await api(`/peer-notes/?course_id=${courseId}`, { token });
      setNotes(feed);
      setError("");
      const nextPreviews = {};
      await Promise.all(
        feed
          .filter((note) => note.is_image && note.preview_url)
          .map(async (note) => {
            try {
              nextPreviews[note.id] = await fetchAuthedBlobUrl(
                note.preview_url,
                token,
              );
            } catch {
              // preview optional
            }
          }),
      );
      setPreviews((prev) => {
        Object.values(prev).forEach((url) => URL.revokeObjectURL(url));
        return nextPreviews;
      });
    } catch (err) {
      setError(err.message);
    }
  }, [courseId, token]);

  useEffect(() => {
    loadFeed();
    return () => {
      setPreviews((prev) => {
        Object.values(prev).forEach((url) => URL.revokeObjectURL(url));
        return {};
      });
    };
  }, [loadFeed]);

  async function shareNote(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a file to share.");
      return;
    }
    if (!week.trim() || !lecture.trim() || !topic.trim()) {
      setError("Add week, lecture number, and topic before uploading.");
      return;
    }
    const about = `Week ${week.trim()} · Lecture ${lecture.trim()} · Topic: ${topic.trim()}`;
    setBusy(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("course_id", String(courseId));
      formData.append("title", title.trim());
      formData.append("about", about);
      if (caption.trim()) formData.append("caption", caption.trim());
      formData.append("anonymous", anonymous ? "true" : "false");
      formData.append("file", file);
      await apiUpload("/peer-notes/", { token, formData });
      setTitle("");
      setWeek("");
      setLecture("");
      setTopic(COURSE_TOPICS[0]);
      setCaption("");
      setAnonymous(false);
      setFile(null);
      event.target.reset?.();
      await loadFeed();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleLike(noteId) {
    try {
      const result = await api(`/peer-notes/${noteId}/like`, {
        method: "POST",
        token,
      });
      setNotes((prev) =>
        prev.map((note) =>
          note.id === noteId
            ? {
                ...note,
                liked_by_me: result.liked,
                like_count: result.like_count,
              }
            : note,
        ),
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function openNoteComments(noteId) {
    if (openComments === noteId) {
      setOpenComments(null);
      return;
    }
    setOpenComments(noteId);
    setCommentBody("");
    try {
      const rows = await api(`/peer-notes/${noteId}/comments`, { token });
      setComments(rows);
    } catch (err) {
      setError(err.message);
    }
  }

  async function submitComment(event) {
    event.preventDefault();
    if (!openComments || !commentBody.trim()) return;
    setCommentBusy(true);
    try {
      await api(`/peer-notes/${openComments}/comments`, {
        method: "POST",
        token,
        body: { body: commentBody.trim(), anonymous: commentAnon },
      });
      const rows = await api(`/peer-notes/${openComments}/comments`, { token });
      setComments(rows);
      setCommentBody("");
      setNotes((prev) =>
        prev.map((note) =>
          note.id === openComments
            ? { ...note, comment_count: rows.length }
            : note,
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setCommentBusy(false);
    }
  }

  async function downloadNote(note) {
    try {
      const url = await fetchAuthedBlobUrl(note.download_url, token);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = note.original_filename || "notes";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeMine(noteId) {
    try {
      await api(`/peer-notes/${noteId}`, { method: "DELETE", token });
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
      if (openComments === noteId) setOpenComments(null);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section id="peer-notes" className="bh-card scroll-mt-6">
      <div className="bh-card-title">
        <h2>Share with classmates</h2>
      </div>
      <p className="bh-card-note">
        Share study notes with classmates in {courseCode}. Describe what they
        cover, then upload - like, comment, and download for your own use. These
        do not train the study agent (that stays professor-approved).
      </p>

      {/* Applied: Purpose; Agency; Familiarity; Simplicity — not minimalism; Feedback (5). */}
      <form
        onSubmit={shareNote}
        className="mt-4 space-y-3 rounded-xl border border-aui-forest/20 bg-[#f3faf5] p-3 sm:p-4"
      >
        <p className="text-sm font-semibold text-aui-ink">Share your notes</p>
        <input
          className="field-glass w-full px-4 py-2.5 text-sm"
          placeholder="Title (e.g. AVL rotations cheatsheet)"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
        />
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="text-xs font-semibold text-aui-ink">
            Week #
            <input
              className="field-glass mt-1 w-full px-3 py-2 text-sm"
              inputMode="numeric"
              value={week}
              onChange={(event) => setWeek(event.target.value)}
              required
            />
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Lecture #
            <input
              className="field-glass mt-1 w-full px-3 py-2 text-sm"
              inputMode="numeric"
              value={lecture}
              onChange={(event) => setLecture(event.target.value)}
              required
            />
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Topic
            <select
              className="field-glass mt-1 w-full px-3 py-2 text-sm"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              required
            >
              {COURSE_TOPICS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <textarea
          className="field-glass min-h-16 w-full px-4 py-2.5 text-sm"
          placeholder="Optional caption for classmates"
          value={caption}
          onChange={(event) => setCaption(event.target.value)}
        />
        <label className="flex cursor-pointer items-center gap-2 text-sm text-aui-ink">
          <input
            type="checkbox"
            className="h-4 w-4 accent-aui-forest"
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
          />
          Post as Classmate (hide my name)
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            id={fileInputId}
            type="file"
            accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
            className="sr-only"
            aria-label="Choose a notes file to share"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button
            type="button"
            className="btn-ghost px-3 py-2 text-sm"
            aria-controls={fileInputId}
            onClick={() => fileInputRef.current?.click()}
          >
            Choose file
          </button>
          {file ? (
            <span className="inline-flex max-w-full items-center gap-2 rounded-lg border border-aui-forest/25 bg-white px-2.5 py-1.5 text-sm text-aui-ink">
              <span className="truncate" title={file.name}>
                {file.name}
              </span>
              <button
                type="button"
                className="bh-inbox-close shrink-0"
                aria-label="Remove selected file"
                onClick={() => {
                  setFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
              >
                ×
              </button>
            </span>
          ) : (
            <span className="text-sm text-aui-deep/70">No file selected</span>
          )}
        </div>
        <p className="text-xs text-aui-deep/85">
          PDF, DOCX, TXT/MD, or images · 20 MB max
        </p>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="btn-primary px-5 py-2.5 text-sm"
        >
          {busy ? "Sharing…" : "Share with classmates"}
        </button>
      </form>

      <div className="mt-5 space-y-3">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs font-semibold text-aui-ink">
            Search
            <input
              className="field-glass mt-1 block w-44 px-3 py-2 text-sm"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setVisibleCount(PAGE_SIZE);
              }}
              placeholder="Title or topic"
            />
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Week
            <input
              className="field-glass mt-1 block w-20 px-3 py-2 text-sm"
              value={filterWeek}
              onChange={(event) => {
                setFilterWeek(event.target.value);
                setVisibleCount(PAGE_SIZE);
              }}
            />
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Lecture
            <input
              className="field-glass mt-1 block w-20 px-3 py-2 text-sm"
              value={filterLecture}
              onChange={(event) => {
                setFilterLecture(event.target.value);
                setVisibleCount(PAGE_SIZE);
              }}
            />
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Topic
            <select
              className="field-glass mt-1 block w-40 px-3 py-2 text-sm"
              value={filterTopic}
              onChange={(event) => {
                setFilterTopic(event.target.value);
                setVisibleCount(PAGE_SIZE);
              }}
            >
              <option value="">All</option>
              {COURSE_TOPICS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            File type
            <select
              className="field-glass mt-1 block w-28 px-3 py-2 text-sm"
              value={filterType}
              onChange={(event) => {
                setFilterType(event.target.value);
                setVisibleCount(PAGE_SIZE);
              }}
            >
              <option value="">All</option>
              <option value="pdf">PDF</option>
              <option value="image">Image</option>
              <option value="doc">Doc / text</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-aui-ink">
            Sort
            <select
              className="field-glass mt-1 block w-32 px-3 py-2 text-sm"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
            >
              <option value="newest">Newest</option>
              <option value="liked">Most liked</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-aui-ink">
            <input
              type="checkbox"
              className="h-4 w-4 accent-aui-forest"
              checked={mineOnly}
              onChange={(event) => {
                setMineOnly(event.target.checked);
                setVisibleCount(PAGE_SIZE);
              }}
            />
            My notes
          </label>
        </div>
        {(() => {
          const filtered = notes
            .filter((note) => {
              const meta = parseAbout(note.about);
              if (mineOnly && !note.is_mine) return false;
              if (filterWeek && meta.week !== String(filterWeek).trim()) return false;
              if (filterLecture && meta.lecture !== String(filterLecture).trim()) {
                return false;
              }
              if (
                filterTopic &&
                !meta.topic.toLowerCase().includes(filterTopic.toLowerCase()) &&
                !(note.about || "").toLowerCase().includes(filterTopic.toLowerCase())
              ) {
                return false;
              }
              if (filterType && fileTypeOf(note) !== filterType) return false;
              if (search.trim()) {
                const q = search.trim().toLowerCase();
                const blob = `${note.title} ${note.about} ${note.caption || ""}`.toLowerCase();
                if (!blob.includes(q)) return false;
              }
              return true;
            })
            .sort((a, b) => {
              if (sortBy === "liked") {
                return (b.like_count || 0) - (a.like_count || 0) || b.id - a.id;
              }
              return (
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime() ||
                b.id - a.id
              );
            });
          const shown = filtered.slice(0, visibleCount);
          return (
            <>
              <p className="text-sm text-aui-deep/80">
                {filtered.length} result{filtered.length === 1 ? "" : "s"}
              </p>
              <div className="space-y-4">
        {notes.length === 0 ? (
          <p className="bh-card-note">
            No classmate notes yet - be the first to share for {courseCode}.
          </p>
        ) : filtered.length === 0 ? (
          <p className="bh-card-note">No notes match these filters.</p>
        ) : (
          shown.map((note) => (
            <article
              key={note.id}
              className="overflow-hidden rounded-2xl border border-[#d7e0d9] bg-white"
            >
              {note.is_image ? (
                <div className="flex max-h-80 items-center justify-center overflow-hidden bg-[#eef3ef]">
                  {previews[note.id] ? (
                    <img
                      src={previews[note.id]}
                      alt={note.title}
                      className="max-h-80 w-full object-contain"
                    />
                  ) : (
                    <p className="px-4 py-10 text-sm text-aui-deep/60">
                      Image preview loading…
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-3 border-b border-[#e7eee8] bg-[#f7faf7] px-4 py-3 text-sm text-aui-deep">
                  <span className="bh-pill bh-pill-gray">
                    {note.original_filename}
                  </span>
                  <span>{formatBytes(note.byte_size)}</span>
                </div>
              )}
              <div className="space-y-2 px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold text-aui-ink">
                      {note.title}
                    </h3>
                    <p className="mt-0.5 text-xs text-aui-deep/70">
                      {note.author_display}
                      {note.anonymous ? " · quiet" : ""} ·{" "}
                      {new Date(note.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <p className="text-sm text-aui-deep">
                  <span className="font-medium text-aui-ink">About: </span>
                  {note.about}
                </p>
                {note.caption ? (
                  <p className="text-sm text-aui-deep/90">{note.caption}</p>
                ) : null}
                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    type="button"
                    className={`btn-ghost px-3 py-1.5 text-xs ${
                      note.liked_by_me ? "border-aui-forest text-aui-forest" : ""
                    }`}
                    onClick={() => toggleLike(note.id)}
                  >
                    {note.liked_by_me ? "Liked" : "Like"} · {note.like_count}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost px-3 py-1.5 text-xs"
                    onClick={() => openNoteComments(note.id)}
                  >
                    Comments · {note.comment_count}
                  </button>
                  <button
                    type="button"
                    className="btn-primary px-3 py-1.5 text-xs"
                    onClick={() => downloadNote(note)}
                  >
                    Download
                  </button>
                  {note.is_mine ? (
                    <button
                      type="button"
                      className="btn-ghost peer-note-delete px-3 py-1.5 text-xs font-semibold text-red-700"
                      data-testid="peer-note-delete"
                      title="Delete your note"
                      aria-label={`Delete note ${note.title}`}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Delete “${note.title}”? The file, likes, and comments are removed.`,
                          )
                        ) {
                          removeMine(note.id);
                        }
                      }}
                    >
                      <span aria-hidden="true" className="peer-note-delete-icon">
                        ⌫
                      </span>
                      <span>Delete</span>
                    </button>
                  ) : null}
                </div>
                {openComments === note.id ? (
                  <div className="mt-3 space-y-2 rounded-xl bg-[#f7faf7] p-3">
                    {comments.length === 0 ? (
                      <p className="text-xs text-aui-deep/70">No comments yet.</p>
                    ) : (
                      comments.map((row) => (
                        <div key={row.id} className="text-sm">
                          <span className="font-semibold text-aui-ink">
                            {row.author_display}
                          </span>
                          <span className="text-aui-deep/80"> - {row.body}</span>
                        </div>
                      ))
                    )}
                    <form onSubmit={submitComment} className="space-y-2 pt-1">
                      <input
                        className="field-glass w-full px-3 py-2 text-sm"
                        placeholder="Add a comment…"
                        value={commentBody}
                        onChange={(event) => setCommentBody(event.target.value)}
                        required
                      />
                      <label className="flex items-center gap-2 text-xs text-aui-deep">
                        <input
                          type="checkbox"
                          className="accent-aui-forest"
                          checked={commentAnon}
                          onChange={(event) =>
                            setCommentAnon(event.target.checked)
                          }
                        />
                        Comment as Classmate
                      </label>
                      <button
                        type="submit"
                        disabled={commentBusy}
                        className="btn-ghost px-3 py-1.5 text-xs"
                      >
                        {commentBusy ? "Posting…" : "Post comment"}
                      </button>
                    </form>
                  </div>
                ) : null}
              </div>
            </article>
          ))
        )}
              </div>
              {filtered.length > visibleCount ? (
                <button
                  type="button"
                  className="btn-ghost px-4 py-2 text-sm"
                  onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
                >
                  Load more
                </button>
              ) : null}
            </>
          );
        })()}
      </div>
    </section>
  );
}
