import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const DEFAULT_REACH =
  "Your perspective unlocked it for me — thanks. If you're open to it, I'd like to compare notes.";

const FLAIRS = [
  { id: "stuck", label: "I'm stuck", hint: "Missing one insight" },
  { id: "aha", label: "Aha", hint: "I figured it out — sharing the angle" },
  { id: "vent", label: "This chapter is a lot", hint: "Academic stress, not a crisis" },
  { id: "find_peer", label: "Find a peer", hint: "Looking for someone to compare notes" },
];

const SORTS = [
  { id: "hot", label: "Hot" },
  { id: "new", label: "New" },
  { id: "top", label: "Top" },
  { id: "rising", label: "Rising" },
];

const RULES = [
  "Share the stuck point, not the homework write-up.",
  "“This unlocked it” is for a real aha — not likes.",
  "Grades, integrity, and crises go to Quiet ask.",
  "Staff are not in this room. Compare-notes stays between classmates.",
];

function timeAgo(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.max(1, Math.round(ms / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function flairMeta(id) {
  return FLAIRS.find((item) => item.id === id) || FLAIRS[0];
}

function mapTree(replies, replyId, updater) {
  return (replies || []).map((reply) => {
    if (reply.id === replyId) return updater(reply);
    return { ...reply, children: mapTree(reply.children, replyId, updater) };
  });
}

function VoteRail({ count, active, disabled, onToggle, label }) {
  return (
    <div className="sr-vote">
      <button
        type="button"
        className={`sr-vote-btn${active ? " is-on" : ""}`}
        disabled={disabled}
        aria-label={label}
        onClick={onToggle}
      >
        ▲
      </button>
      <span className={`sr-vote-count${active ? " is-on" : ""}`}>{count}</span>
    </div>
  );
}

function Comment({
  reply,
  depth,
  replyDrafts,
  setReplyDrafts,
  replyAnon,
  setReplyAnon,
  replyBusy,
  reachBusy,
  onReply,
  onHelpful,
  onReach,
}) {
  const [open, setOpen] = useState(false);
  const indent = Math.min(depth, 6);

  return (
    <div className={`sr-comment${depth > 0 ? " is-nested" : ""}`} style={{ marginLeft: indent * 14 }}>
      <div className="sr-comment-rail" />
      <div className="sr-comment-body">
        <p className="sr-meta">
          <span className="sr-author">{reply.author_display}</span>
          {reply.author_karma > 0 ? (
            <span className="sr-karma">{reply.author_karma} helper karma</span>
          ) : null}
          {reply.anonymous ? <span>quiet</span> : null}
          <span>{timeAgo(reply.created_at)}</span>
        </p>
        <p className="sr-comment-text">{reply.body}</p>
        <div className="sr-comment-actions">
          <button
            type="button"
            disabled={reply.is_mine}
            className={`sr-text-btn${reply.marked_helpful_by_me ? " is-on" : ""}`}
            onClick={() => onHelpful(reply.id)}
          >
            {reply.marked_helpful_by_me ? "Unlocked it" : "This unlocked it"} · {reply.helpful_count}
          </button>
          <button type="button" className="sr-text-btn" onClick={() => setOpen((value) => !value)}>
            Reply
          </button>
          {reply.reachable && !reply.reached_out_by_me ? (
            <button
              type="button"
              className="sr-text-btn sr-text-btn-strong"
              disabled={reachBusy === reply.id}
              onClick={() => onReach(reply.id)}
            >
              {reachBusy === reply.id ? "Sending…" : "Thanks — compare notes?"}
            </button>
          ) : null}
          {reply.reached_out_by_me ? <span className="sr-handshake">Handshake sent</span> : null}
        </div>
        {open ? (
          <form className="sr-inline-reply" onSubmit={(event) => onReply(event, reply.id)}>
            <textarea
              className="field-glass min-h-16 w-full px-3 py-2 text-sm"
              placeholder="Reply to this perspective — not the finished write-up…"
              value={replyDrafts[`c-${reply.id}`] || ""}
              onChange={(event) =>
                setReplyDrafts((prev) => ({ ...prev, [`c-${reply.id}`]: event.target.value }))
              }
              required
            />
            <label className="sr-anon">
              <input
                type="checkbox"
                className="accent-aui-forest"
                checked={Boolean(replyAnon[`c-${reply.id}`])}
                onChange={(event) =>
                  setReplyAnon((prev) => ({ ...prev, [`c-${reply.id}`]: event.target.checked }))
                }
              />
              Reply as Classmate
            </label>
            <button type="submit" disabled={replyBusy === `c-${reply.id}`} className="btn-primary px-3 py-1.5 text-xs">
              {replyBusy === `c-${reply.id}` ? "Posting…" : "Comment"}
            </button>
          </form>
        ) : null}
        {(reply.children || []).map((child) => (
          <Comment
            key={child.id}
            reply={child}
            depth={depth + 1}
            replyDrafts={replyDrafts}
            setReplyDrafts={setReplyDrafts}
            replyAnon={replyAnon}
            setReplyAnon={setReplyAnon}
            replyBusy={replyBusy}
            reachBusy={reachBusy}
            onReply={onReply}
            onHelpful={onHelpful}
            onReach={onReach}
          />
        ))}
      </div>
    </div>
  );
}

export default function StuckRoomPage() {
  const { token, activeCourse } = useAuth();
  const [params, setParams] = useSearchParams();
  const threadId = params.get("post");
  const composing = params.get("view") === "submit";

  const [community, setCommunity] = useState(null);
  const [posts, setPosts] = useState([]);
  const [thread, setThread] = useState(null);
  const [ranks, setRanks] = useState([]);
  const [reachOuts, setReachOuts] = useState([]);
  const [sort, setSort] = useState("hot");
  const [flairFilter, setFlairFilter] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [chapter, setChapter] = useState("");
  const [flair, setFlair] = useState("stuck");
  const [anonymous, setAnonymous] = useState(false);
  const [replyDrafts, setReplyDrafts] = useState({});
  const [replyAnon, setReplyAnon] = useState({});
  const [replyBusy, setReplyBusy] = useState(null);
  const [reachBusy, setReachBusy] = useState(null);

  const courseId = activeCourse?.id;
  const incoming = useMemo(
    () => reachOuts.filter((row) => row.is_incoming),
    [reachOuts],
  );

  const loadFeed = useCallback(async () => {
    if (!courseId || !token) return;
    const flairQuery = flairFilter ? `&flair=${flairFilter}` : "";
    try {
      const [meta, feed, board, handshakes] = await Promise.all([
        api(`/help-room/community/?course_id=${courseId}`, { token }),
        api(`/help-room/?course_id=${courseId}&sort=${sort}${flairQuery}`, { token }),
        api(`/help-room/ranks/?course_id=${courseId}`, { token }),
        api(`/help-room/reach-outs/?course_id=${courseId}`, { token }),
      ]);
      setCommunity(meta);
      setPosts(feed);
      setRanks(board);
      setReachOuts(handshakes);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [courseId, token, sort, flairFilter]);

  const loadThread = useCallback(async () => {
    if (!threadId || !token) {
      setThread(null);
      return;
    }
    try {
      const item = await api(`/help-room/${threadId}`, { token });
      setThread(item);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [threadId, token]);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  useEffect(() => {
    loadThread();
  }, [loadThread]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
  }

  const name = community?.community_name || `r/${String(activeCourse.code || "").replace(/\s+/g, "")}`;

  function openThread(id) {
    setParams({ post: String(id) });
  }

  function openSubmit() {
    setParams({ view: "submit" });
  }

  function backToFeed() {
    setParams({});
  }

  async function submitPost(event) {
    event.preventDefault();
    if (!title.trim() || !body.trim()) {
      setError("Give it a title, then describe the stuck point.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await api("/help-room/", {
        method: "POST",
        token,
        body: {
          course_id: courseId,
          title: title.trim(),
          body: body.trim(),
          chapter: chapter.trim() || null,
          flair,
          anonymous,
        },
      });
      setTitle("");
      setBody("");
      setChapter("");
      setFlair("stuck");
      setAnonymous(false);
      await loadFeed();
      setParams({ post: String(created.id) });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function voteSameHere(postId, isMine) {
    if (isMine) return;
    try {
      const result = await api(`/help-room/${postId}/same-here`, { method: "POST", token });
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId
            ? { ...post, same_here_by_me: result.marked, same_here_count: result.same_here_count }
            : post,
        ),
      );
      setThread((prev) =>
        prev && prev.id === postId
          ? { ...prev, same_here_by_me: result.marked, same_here_count: result.same_here_count }
          : prev,
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function submitReply(event, parentReplyId) {
    event.preventDefault();
    if (!thread) return;
    const key = parentReplyId ? `c-${parentReplyId}` : `p-${thread.id}`;
    const text = (replyDrafts[key] || "").trim();
    if (!text) return;
    setReplyBusy(key);
    try {
      await api(`/help-room/${thread.id}/replies`, {
        method: "POST",
        token,
        body: {
          body: text,
          anonymous: Boolean(replyAnon[key]),
          parent_reply_id: parentReplyId || null,
        },
      });
      setReplyDrafts((prev) => ({ ...prev, [key]: "" }));
      await loadThread();
      await loadFeed();
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
      setThread((prev) =>
        prev
          ? {
              ...prev,
              replies: mapTree(prev.replies, replyId, (reply) => ({
                ...reply,
                marked_helpful_by_me: result.marked,
                helpful_count: result.helpful_count,
                reachable: result.reachable,
                reached_out_by_me: result.reached_out_by_me,
              })),
            }
          : prev,
      );
      const board = await api(`/help-room/ranks/?course_id=${courseId}`, { token });
      setRanks(board);
    } catch (err) {
      setError(err.message);
    }
  }

  async function reachOut(replyId) {
    setReachBusy(replyId);
    try {
      await api(`/help-room/replies/${replyId}/reach-out`, {
        method: "POST",
        token,
        body: { note: DEFAULT_REACH },
      });
      await loadThread();
      await loadFeed();
    } catch (err) {
      setError(err.message);
    } finally {
      setReachBusy(null);
    }
  }

  async function removeMine(postId) {
    try {
      await api(`/help-room/${postId}`, { method: "DELETE", token });
      setPosts((prev) => prev.filter((post) => post.id !== postId));
      if (String(postId) === String(threadId)) backToFeed();
    } catch (err) {
      setError(err.message);
    }
  }

  const initials = (activeCourse.code || "OH").replace(/\s+/g, "").slice(0, 2).toUpperCase();

  return (
    <div className="sr-page">
      <div className="sr-banner">
        <div className="sr-banner-wash" />
      </div>

      <div className="sr-head">
        <div className="sr-avatar" aria-hidden="true">
          {initials}
        </div>
        <div className="sr-head-copy">
          <p className="sr-kicker">Stuck Room · classmates only</p>
          <h1>{name}</h1>
          <p>
            {activeCourse.code} — {activeCourse.title}. Share what you are stuck on, rank the
            people who truly unlocked it, and find a peer when the chapter is a lot.
          </p>
        </div>
        <button type="button" className="btn-primary px-5 py-2.5 text-sm" onClick={openSubmit}>
          Create post
        </button>
      </div>

      <div className="sr-layout">
        <div>
          {error ? <p className="sr-error">{error}</p> : null}

          {threadId && thread ? (
            <article className="sr-card sr-thread">
              <button type="button" className="sr-back" onClick={backToFeed}>
                ← Back to {name}
              </button>
              <div className="sr-post">
                <VoteRail
                  count={thread.same_here_count}
                  active={thread.same_here_by_me}
                  disabled={thread.is_mine}
                  label="Same here"
                  onToggle={() => voteSameHere(thread.id, thread.is_mine)}
                />
                <div className="sr-post-main">
                  <p className="sr-meta">
                    <span className={`sr-flair sr-flair-${thread.flair}`}>{flairMeta(thread.flair).label}</span>
                    <span>Posted by {thread.author_display}</span>
                    {thread.author_karma > 0 ? (
                      <span className="sr-karma">{thread.author_karma} helper karma</span>
                    ) : null}
                    <span>{timeAgo(thread.created_at)}</span>
                    {thread.chapter ? <span>{thread.chapter}</span> : null}
                    {thread.is_mine ? (
                      <button type="button" className="sr-text-btn sr-danger" onClick={() => removeMine(thread.id)}>
                        Delete
                      </button>
                    ) : null}
                  </p>
                  <h2>{thread.title}</h2>
                  <p className="sr-body">{thread.body}</p>
                  {thread.similar_chapter_count > 0 ? (
                    <p className="sr-solidarity">
                      {thread.similar_chapter_count} other classmate
                      {thread.similar_chapter_count === 1 ? " is" : "s are"} on {thread.chapter}{" "}
                      — you are not the only one.
                    </p>
                  ) : null}
                  <p className="sr-meta">
                    <span>{thread.reply_count} comment{thread.reply_count === 1 ? "" : "s"}</span>
                    <span>{thread.unlocked_count} aha mark{thread.unlocked_count === 1 ? "" : "s"}</span>
                  </p>
                </div>
              </div>

              <form className="sr-composer sr-composer-inline" onSubmit={(event) => submitReply(event, null)}>
                <p className="sr-composer-label">Comment as a classmate</p>
                <textarea
                  className="field-glass min-h-20 w-full px-3 py-2 text-sm"
                  placeholder="A simpler approach, a missing check, or a study-peer offer…"
                  value={replyDrafts[`p-${thread.id}`] || ""}
                  onChange={(event) =>
                    setReplyDrafts((prev) => ({ ...prev, [`p-${thread.id}`]: event.target.value }))
                  }
                  required
                />
                <div className="sr-composer-row">
                  <label className="sr-anon">
                    <input
                      type="checkbox"
                      className="accent-aui-forest"
                      checked={Boolean(replyAnon[`p-${thread.id}`])}
                      onChange={(event) =>
                        setReplyAnon((prev) => ({ ...prev, [`p-${thread.id}`]: event.target.checked }))
                      }
                    />
                    Comment as Classmate
                  </label>
                  <button type="submit" disabled={replyBusy === `p-${thread.id}`} className="btn-primary px-4 py-2 text-sm">
                    {replyBusy === `p-${thread.id}` ? "Posting…" : "Comment"}
                  </button>
                </div>
              </form>

              <div className="sr-comments">
                {(thread.replies || []).length === 0 ? (
                  <p className="bh-card-note">No comments yet. The first perspective often is the aha.</p>
                ) : (
                  (thread.replies || []).map((reply) => (
                    <Comment
                      key={reply.id}
                      reply={reply}
                      depth={0}
                      replyDrafts={replyDrafts}
                      setReplyDrafts={setReplyDrafts}
                      replyAnon={replyAnon}
                      setReplyAnon={setReplyAnon}
                      replyBusy={replyBusy}
                      reachBusy={reachBusy}
                      onReply={submitReply}
                      onHelpful={markHelpful}
                      onReach={reachOut}
                    />
                  ))
                )}
              </div>
            </article>
          ) : composing ? (
            <form className="sr-card sr-submit" onSubmit={submitPost}>
              <button type="button" className="sr-back" onClick={backToFeed}>
                ← Cancel
              </button>
              <h2>Create a post</h2>
              <p className="bh-card-note">
                This is a course community, not a homework dump. Staff never sit in the room.
              </p>
              <div className="sr-flair-picks">
                {FLAIRS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`sr-flair-pick sr-flair-${item.id}${flair === item.id ? " is-on" : ""}`}
                    onClick={() => setFlair(item.id)}
                  >
                    <strong>{item.label}</strong>
                    <span>{item.hint}</span>
                  </button>
                ))}
              </div>
              <input
                className="field-glass w-full px-4 py-2.5 text-sm"
                placeholder="Title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
              <input
                className="field-glass w-full px-4 py-2.5 text-sm"
                placeholder="Chapter / topic (optional)"
                value={chapter}
                onChange={(event) => setChapter(event.target.value)}
              />
              <textarea
                className="field-glass min-h-36 w-full px-4 py-2.5 text-sm"
                placeholder="What have you already tried? What feels one insight away?"
                value={body}
                onChange={(event) => setBody(event.target.value)}
                required
              />
              <label className="sr-anon">
                <input
                  type="checkbox"
                  className="accent-aui-forest"
                  checked={anonymous}
                  onChange={(event) => setAnonymous(event.target.checked)}
                />
                Post as Classmate (hide my name)
              </label>
              <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm">
                {busy ? "Posting…" : "Post"}
              </button>
            </form>
          ) : (
            <>
              <div className="sr-toolbar">
                <div className="sr-sorts">
                  {SORTS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`sr-sort${sort === item.id ? " is-on" : ""}`}
                      onClick={() => setSort(item.id)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                <div className="sr-filters">
                  <button
                    type="button"
                    className={`sr-chip${!flairFilter ? " is-on" : ""}`}
                    onClick={() => setFlairFilter("")}
                  >
                    All
                  </button>
                  {FLAIRS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`sr-chip sr-flair-${item.id}${flairFilter === item.id ? " is-on" : ""}`}
                      onClick={() => setFlairFilter(item.id)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {posts.length === 0 ? (
                <div className="sr-card sr-empty">
                  <h2>No posts in {name} yet</h2>
                  <p>
                    Be the first to say what you are stuck on — classmates already solved the
                    same snag, and asking here is often easier than waiting days alone.
                  </p>
                  <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm" onClick={openSubmit}>
                    Create the first post
                  </button>
                </div>
              ) : (
                <div className="sr-feed">
                  {posts.map((post) => (
                    <article key={post.id} className="sr-card sr-row">
                      <VoteRail
                        count={post.same_here_count}
                        active={post.same_here_by_me}
                        disabled={post.is_mine}
                        label="Same here"
                        onToggle={() => voteSameHere(post.id, post.is_mine)}
                      />
                      <button type="button" className="sr-row-main" onClick={() => openThread(post.id)}>
                        <p className="sr-meta">
                          <span className={`sr-flair sr-flair-${post.flair}`}>{flairMeta(post.flair).label}</span>
                          <span>Posted by {post.author_display}</span>
                          {post.author_karma > 0 ? (
                            <span className="sr-karma">{post.author_karma} helper karma</span>
                          ) : null}
                          <span>{timeAgo(post.created_at)}</span>
                          {post.chapter ? <span>{post.chapter}</span> : null}
                        </p>
                        <h2>{post.title}</h2>
                        <p className="sr-preview">{post.body}</p>
                        <p className="sr-meta">
                          <span>
                            {post.reply_count} comment{post.reply_count === 1 ? "" : "s"}
                          </span>
                          <span>
                            {post.unlocked_count} aha{post.unlocked_count === 1 ? "" : "s"}
                          </span>
                        </p>
                      </button>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <aside className="sr-side">
          <section className="sr-card">
            <h3>About community</h3>
            <p>
              A course subreddit for {activeCourse.code}: stuck points, ahas, academic stress,
              and finding a peer. Not Quiet ask. Not file notes. Not a staff chat.
            </p>
            <dl className="sr-stats">
              <div>
                <dt>{community?.classmate_count ?? "—"}</dt>
                <dd>Classmates</dd>
              </div>
              <div>
                <dt>{community?.post_count ?? posts.length}</dt>
                <dd>Posts</dd>
              </div>
              <div>
                <dt>{community?.helper_count ?? ranks.length}</dt>
                <dd>Helpers</dd>
              </div>
            </dl>
          </section>

          <section className="sr-card">
            <h3>{name} rules</h3>
            <ol>
              {RULES.map((rule, index) => (
                <li key={rule}>
                  <span>{index + 1}</span>
                  {rule}
                </li>
              ))}
            </ol>
          </section>

          <section className="sr-card">
            <h3>Top helpers</h3>
            <p className="bh-card-note">
              Ranked by unique “this unlocked it” marks — the true-help signal, not upvotes.
            </p>
            {ranks.length === 0 ? (
              <p className="mt-2 text-sm text-aui-deep/70">No helper karma yet.</p>
            ) : (
              <ol className="sr-ranks">
                {ranks.slice(0, 8).map((row) => (
                  <li key={row.user_id}>
                    <span className="sr-rank-n">#{row.rank}</span>
                    <span className="sr-rank-name">{row.display_name}</span>
                    <span className="sr-rank-pts">{row.helpful_points}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {incoming.length > 0 ? (
            <section className="sr-card sr-inbox">
              <h3>Compare-notes pings</h3>
              <p className="bh-card-note">Named handshake after an aha. Staff never see this.</p>
              <ul>
                {incoming.map((row) => (
                  <li key={row.id}>
                    <strong>{row.from_display}</strong>
                    <span>{row.post_title}</span>
                    <p>{row.note}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <p className="sr-quiet">
            Need staff instead?{" "}
            <Link to="/student#ask">Quiet ask</Link>
          </p>
        </aside>
      </div>
    </div>
  );
}
