import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function HelpRoomFeed({ token, courseId, courseCode }) {
  const [posts, setPosts] = useState([]);
  const [ranks, setRanks] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [chapter, setChapter] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [replyDrafts, setReplyDrafts] = useState({});
  const [replyAnon, setReplyAnon] = useState({});
  const [replyBusy, setReplyBusy] = useState(null);

  const load = useCallback(async () => {
    if (!courseId || !token) return;
    try {
      const [feed, board] = await Promise.all([
        api(`/help-room/?course_id=${courseId}`, { token }),
        api(`/help-room/ranks/?course_id=${courseId}`, { token }),
      ]);
      setPosts(feed);
      setRanks(board);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [courseId, token]);

  useEffect(() => {
    load();
  }, [load]);

  async function submitPost(event) {
    event.preventDefault();
    if (!title.trim() || !body.trim()) {
      setError("Say what you are stuck on, then describe the missing perspective.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/help-room/", {
        method: "POST",
        token,
        body: {
          course_id: courseId,
          title: title.trim(),
          body: body.trim(),
          chapter: chapter.trim() || null,
          anonymous,
        },
      });
      setTitle("");
      setBody("");
      setChapter("");
      setAnonymous(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitReply(event, postId) {
    event.preventDefault();
    const text = (replyDrafts[postId] || "").trim();
    if (!text) return;
    setReplyBusy(postId);
    try {
      await api(`/help-room/${postId}/replies`, {
        method: "POST",
        token,
        body: {
          body: text,
          anonymous: Boolean(replyAnon[postId]),
        },
      });
      setReplyDrafts((prev) => ({ ...prev, [postId]: "" }));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setReplyBusy(null);
    }
  }

  async function markHelpful(replyId) {
    try {
      const result = await api(`/help-room/replies/${replyId}/helpful`, {
        method: "POST",
        token,
      });
      setPosts((prev) =>
        prev.map((post) => ({
          ...post,
          replies: (post.replies || []).map((reply) =>
            reply.id === replyId
              ? {
                  ...reply,
                  marked_helpful_by_me: result.marked,
                  helpful_count: result.helpful_count,
                }
              : reply,
          ),
        })),
      );
      const board = await api(`/help-room/ranks/?course_id=${courseId}`, { token });
      setRanks(board);
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeMine(postId) {
    try {
      await api(`/help-room/${postId}`, { method: "DELETE", token });
      setPosts((prev) => prev.filter((post) => post.id !== postId));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section id="stuck-room" className="bh-card mt-5 scroll-mt-6">
      <div className="bh-card-title">
        <h2>Stuck Room</h2>
      </div>
      <p className="bh-card-note">
        Course-only thread for {courseCode}: post what you are stuck on, and
        classmates share a simpler approach or a missing perspective — the “aha”
        that was one sentence away. This is not Quiet ask (staff) and not
        Classmate notes (files). Do not paste homework answers. Grades, integrity,
        and personal crises stay on Quiet ask.
      </p>

      {ranks.length > 0 ? (
        <div className="mt-4 rounded-xl border border-aui-forest/20 bg-[#f3faf5] p-3 sm:p-4">
          <p className="text-sm font-semibold text-aui-ink">Helpful classmates</p>
          <p className="mt-1 text-xs text-aui-deep/70">
            Points come from unique “this unlocked it” marks — not likes, not
            self-votes. Anonymous replies still credit your account.
          </p>
          <ol className="mt-3 space-y-1.5 text-sm">
            {ranks.slice(0, 8).map((row) => (
              <li key={row.user_id} className="flex flex-wrap items-baseline gap-2">
                <span className="bh-pill bh-pill-green">#{row.rank}</span>
                <span className="font-semibold text-aui-ink">{row.display_name}</span>
                <span className="text-xs text-aui-deep/70">
                  {row.helpful_points} helpful point
                  {row.helpful_points === 1 ? "" : "s"}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <p className="mt-3 text-xs text-aui-deep/65">
          No helpful ranks yet — a classmate’s mark on your reply is how you
          appear here.
        </p>
      )}

      <form
        onSubmit={submitPost}
        className="mt-4 space-y-3 rounded-xl border border-aui-forest/20 bg-[#f3faf5] p-3 sm:p-4"
      >
        <p className="text-sm font-semibold text-aui-ink">I am stuck on…</p>
        <input
          className="field-glass w-full px-4 py-2.5 text-sm"
          placeholder="Short title (e.g. AVL imbalance after insert)"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
        />
        <input
          className="field-glass w-full px-4 py-2.5 text-sm"
          placeholder="Optional chapter / topic (e.g. Chapter 5 — AVL)"
          value={chapter}
          onChange={(event) => setChapter(event.target.value)}
        />
        <textarea
          className="field-glass min-h-24 w-full px-4 py-2.5 text-sm"
          placeholder="What have you already tried? What feels one insight away?"
          value={body}
          onChange={(event) => setBody(event.target.value)}
          required
        />
        <label className="flex cursor-pointer items-center gap-2 text-sm text-aui-ink">
          <input
            type="checkbox"
            className="h-4 w-4 accent-aui-forest"
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
          />
          Post as Classmate (hide my name on the thread)
        </label>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm">
          {busy ? "Posting…" : "Post to Stuck Room"}
        </button>
      </form>

      <div className="mt-5 space-y-4">
        {posts.length === 0 ? (
          <p className="bh-card-note">
            No stuck threads yet in {courseCode}. Asking here is often easier than
            waiting days alone — classmates already solved the same snag.
          </p>
        ) : (
          posts.map((post) => (
            <article
              key={post.id}
              className="overflow-hidden rounded-2xl border border-[#d7e0d9] bg-white"
            >
              <div className="space-y-2 px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold text-aui-ink">
                      {post.title}
                    </h3>
                    <p className="mt-0.5 text-xs text-aui-deep/70">
                      {post.author_display}
                      {post.anonymous ? " · quiet" : ""}
                      {post.chapter ? ` · ${post.chapter}` : ""} ·{" "}
                      {new Date(post.created_at).toLocaleString()}
                    </p>
                  </div>
                  {post.is_mine ? (
                    <button
                      type="button"
                      className="text-xs text-red-700 underline"
                      onClick={() => removeMine(post.id)}
                    >
                      Delete
                    </button>
                  ) : null}
                </div>
                <p className="whitespace-pre-wrap text-sm text-aui-deep">{post.body}</p>

                <div className="mt-3 space-y-3 rounded-xl bg-[#f7faf7] p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-aui-deep/55">
                    Perspectives · {post.reply_count}
                  </p>
                  {(post.replies || []).length === 0 ? (
                    <p className="text-xs text-aui-deep/70">
                      Share an approach that unlocked it for you — not the finished
                      homework write-up.
                    </p>
                  ) : (
                    (post.replies || []).map((reply) => (
                      <div key={reply.id} className="text-sm">
                        <p>
                          <span className="font-semibold text-aui-ink">
                            {reply.author_display}
                          </span>
                          <span className="text-aui-deep/80"> — {reply.body}</span>
                        </p>
                        <button
                          type="button"
                          disabled={reply.is_mine}
                          className={`mt-1 btn-ghost px-3 py-1 text-xs ${
                            reply.marked_helpful_by_me
                              ? "border-aui-forest text-aui-forest"
                              : ""
                          }`}
                          onClick={() => markHelpful(reply.id)}
                        >
                          {reply.marked_helpful_by_me
                            ? "Unlocked it"
                            : "This unlocked it"}{" "}
                          · {reply.helpful_count}
                        </button>
                      </div>
                    ))
                  )}
                  <form
                    onSubmit={(event) => submitReply(event, post.id)}
                    className="space-y-2 pt-1"
                  >
                    <textarea
                      className="field-glass min-h-16 w-full px-3 py-2 text-sm"
                      placeholder="A simpler approach or a new angle…"
                      value={replyDrafts[post.id] || ""}
                      onChange={(event) =>
                        setReplyDrafts((prev) => ({
                          ...prev,
                          [post.id]: event.target.value,
                        }))
                      }
                      required
                    />
                    <label className="flex items-center gap-2 text-xs text-aui-deep">
                      <input
                        type="checkbox"
                        className="accent-aui-forest"
                        checked={Boolean(replyAnon[post.id])}
                        onChange={(event) =>
                          setReplyAnon((prev) => ({
                            ...prev,
                            [post.id]: event.target.checked,
                          }))
                        }
                      />
                      Reply as Classmate
                    </label>
                    <button
                      type="submit"
                      disabled={replyBusy === post.id}
                      className="btn-ghost px-3 py-1.5 text-xs"
                    >
                      {replyBusy === post.id ? "Posting…" : "Share perspective"}
                    </button>
                  </form>
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
