import { useCallback, useEffect, useState } from "react";
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

export default function PeerNotesFeed({ token, courseId, courseCode }) {
  const [notes, setNotes] = useState([]);
  const [previews, setPreviews] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [about, setAbout] = useState("");
  const [caption, setCaption] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [file, setFile] = useState(null);
  const [openComments, setOpenComments] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentBody, setCommentBody] = useState("");
  const [commentAnon, setCommentAnon] = useState(false);
  const [commentBusy, setCommentBusy] = useState(false);

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
    if (!about.trim()) {
      setError("Say what your notes are about before uploading.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("course_id", String(courseId));
      formData.append("title", title.trim());
      formData.append("about", about.trim());
      if (caption.trim()) formData.append("caption", caption.trim());
      formData.append("anonymous", anonymous ? "true" : "false");
      formData.append("file", file);
      await apiUpload("/peer-notes/", { token, formData });
      setTitle("");
      setAbout("");
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
    <section id="peer-notes" className="bh-card mt-5 scroll-mt-6">
      <div className="bh-card-title">
        <h2>Classmate notes</h2>
      </div>
      <p className="bh-card-note">
        Share study notes with classmates in {courseCode}. Describe what they
        cover, then upload — like, comment, and download for your own use. These
        do not train the study agent (that stays professor-approved).
      </p>

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
        <textarea
          className="field-glass min-h-20 w-full px-4 py-2.5 text-sm"
          placeholder="What are these notes about? (week, lecture, topic…)"
          value={about}
          onChange={(event) => setAbout(event.target.value)}
          required
        />
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
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
          className="block w-full text-sm text-aui-deep"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
          required
        />
        <p className="text-xs text-aui-deep/65">
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

      <div className="mt-5 space-y-4">
        {notes.length === 0 ? (
          <p className="bh-card-note">
            No classmate notes yet — be the first to share for {courseCode}.
          </p>
        ) : (
          notes.map((note) => (
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
                  {note.is_mine ? (
                    <button
                      type="button"
                      className="text-xs text-red-700 underline"
                      onClick={() => removeMine(note.id)}
                    >
                      Delete
                    </button>
                  ) : null}
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
                          <span className="text-aui-deep/80"> — {row.body}</span>
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
    </section>
  );
}
