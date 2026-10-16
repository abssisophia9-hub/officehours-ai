import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { MarkdownBody, avatarHue, initials } from "../lib/rooms.jsx";

const STOP_WORDS = new Set([
  "the", "and", "for", "you", "your", "what", "how", "why", "can", "not",
  "with", "this", "that", "from", "have", "are", "was", "were", "but",
  "just", "when", "does", "did", "into", "about", "than", "then", "them",
  "they", "its", "out", "off", "too", "very", "any", "all", "who", "our",
]);

function itemsOf(feed) {
  if (Array.isArray(feed)) return feed;
  return feed?.items || [];
}

function askedAgo(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  if (!Number.isFinite(ms)) return "";
  const mins = Math.round(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins === 1 ? "1 minute ago" : `${mins} minutes ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return days === 1 ? "1 day ago" : `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

function snippetOf(body) {
  const line = String(body || "")
    .replace(/[*_`#>[\]()]/g, "")
    .split("\n")
    .map((row) => row.trim())
    .find(Boolean) || "";
  if (line.length <= 140) return line;
  return `${line.slice(0, 137).trim()}…`;
}

function answerLabel(count) {
  const n = Number(count) || 0;
  if (n === 0) return "No answers";
  if (n === 1) return "1 answer";
  return `${n} answers`;
}

function questionState(post) {
  if (post?.status === "solved") return "solved";
  if ((post?.reply_count || 0) > 0) return "answered";
  return "unanswered";
}

function stateLabel(state) {
  if (state === "solved") return "Solved";
  if (state === "answered") return "Answered";
  return "Unanswered";
}

function typeLabel(roomType) {
  if (roomType === "discussion") return "Discussion";
  if (roomType === "article") return "Article";
  return "";
}

function similarQuestions(query, posts) {
  const words = (String(query || "").toLowerCase().match(/[a-z0-9]{3,}/g) || [])
    .filter((word) => !STOP_WORDS.has(word));
  if (!words.length) return [];
  return posts
    .map((post) => {
      const hay = `${post.title} ${post.body}`.toLowerCase();
      const hits = words.filter((word) => hay.includes(word)).length;
      return { post, hits };
    })
    .filter((row) => row.hits > 0)
    .sort((a, b) => b.hits - a.hits || b.post.id - a.post.id)
    .slice(0, 3)
    .map((row) => row.post);
}

function findAccepted(replies) {
  for (const reply of replies || []) {
    if (reply.accepted) return reply;
    const nested = findAccepted(reply.children);
    if (nested) return nested;
  }
  return null;
}

function withoutReply(replies, id) {
  return (replies || [])
    .filter((reply) => reply.id !== id)
    .map((reply) => ({ ...reply, children: withoutReply(reply.children, id) }));
}

function Avatar({ name, seed, size = 36 }) {
  const hue = avatarHue(seed || name);
  return (
    <span
      className="rooms-avatar"
      style={{
        width: size,
        height: size,
        fontSize: Math.max(12, size * 0.36),
        background: `hsl(${hue} 28% 28%)`,
      }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

function Stars({ count }) {
  return (
    <span className="rooms-stars" aria-label={`${count} of 5`}>
      {"★".repeat(count)}
      {"☆".repeat(Math.max(0, 5 - count))}
    </span>
  );
}

function StatusIcon({ state }) {
  if (state === "solved") {
    return (
      <svg className="rooms-icon" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
        <path d="M6.2 10.2 8.7 12.7 13.8 7.4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (state === "answered") {
    return (
      <svg className="rooms-icon" viewBox="0 0 20 20" aria-hidden="true">
        <path d="M4 5.5h12v7.2H8.2L4.8 16v-3.3H4z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg className="rooms-icon" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function StatusMark({ post }) {
  const state = questionState(post);
  return (
    <span className={`rooms-status rooms-status-${state}`}>
      <StatusIcon state={state} />
      {stateLabel(state)}
    </span>
  );
}

export default function StuckRoomPage() {
  const { token, activeCourse, user } = useAuth();
  const [params, setParams] = useSearchParams();
  const view = params.get("view") || "questions";
  const threadId = params.get("post");
  const profileId = params.get("user");

  const [community, setCommunity] = useState(null);
  const [library, setLibrary] = useState([]);
  const [solvedPosts, setSolvedPosts] = useState([]);
  const [thread, setThread] = useState(null);
  const [ranks, setRanks] = useState([]);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [tab, setTab] = useState("newest");
  const [chapterFilter, setChapterFilter] = useState("");

  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [tried, setTried] = useState("");
  const [chapter, setChapter] = useState("");
  const [busy, setBusy] = useState(false);
  const [replyDrafts, setReplyDrafts] = useState({});
  const [replyBusy, setReplyBusy] = useState(null);

  const courseId = activeCourse?.id;

  const loadFeed = useCallback(async () => {
    if (!courseId || !token) return;
    const newest = new URLSearchParams({
      course_id: String(courseId),
      sort: "new",
      limit: "80",
    });
    const solved = new URLSearchParams({
      course_id: String(courseId),
      sort: "new",
      status: "solved",
      limit: "80",
    });
    try {
      const [meta, feed, solvedFeed, board] = await Promise.all([
        api(`/help-room/community/?course_id=${courseId}`, { token }),
        api(`/help-room/?${newest}`, { token }),
        api(`/help-room/?${solved}`, { token }),
        api(`/help-room/ranks/?course_id=${courseId}`, { token }),
      ]);
      setCommunity(meta);
      setLibrary(itemsOf(feed));
      setSolvedPosts(itemsOf(solvedFeed));
      setRanks(Array.isArray(board) ? board : []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoaded(true);
    }
  }, [courseId, token]);

  const loadThread = useCallback(async () => {
    if (!threadId || !token) {
      setThread(null);
      return;
    }
    try {
      setThread(await api(`/help-room/${threadId}`, { token }));
    } catch (err) {
      setError(err.message);
    }
  }, [threadId, token]);

  const loadProfile = useCallback(async () => {
    if (!profileId || !token || !courseId) {
      setProfile(null);
      return;
    }
    try {
      setProfile(
        await api(`/help-room/profile/${profileId}?course_id=${courseId}`, { token }),
      );
    } catch (err) {
      setError(err.message);
    }
  }, [profileId, token, courseId]);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);
  useEffect(() => {
    loadThread();
  }, [loadThread]);
  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const chapters = community?.chapters || [];
  const visiblePosts = useMemo(() => {
    const source = tab === "solved" ? solvedPosts : library;
    return source.filter((post) => {
      if (chapterFilter && post.chapter !== chapterFilter) return false;
      if (tab === "unanswered") {
        return (post.reply_count || 0) === 0 && post.status !== "solved";
      }
      return true;
    });
  }, [tab, solvedPosts, library, chapterFilter]);

  const matches = useMemo(
    () => similarQuestions(title, library),
    [title, library],
  );

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
  }

  const courseLabel = [activeCourse.code, activeCourse.title].filter(Boolean).join(" · ");
  const showingList = !profileId && view !== "create" && view !== "leaderboard" && !threadId;
  const showingThread = Boolean(threadId) && !profileId && view !== "create" && view !== "leaderboard";

  function go(next) {
    setParams(next);
  }

  async function vote(postId, value, isMine) {
    if (isMine) return;
    try {
      const result = await api(`/help-room/${postId}/vote`, {
        method: "POST",
        token,
        body: { value },
      });
      const patch = (item) =>
        item && item.id === postId
          ? {
              ...item,
              score: result.score,
              up_count: result.up_count,
              down_count: result.down_count,
              my_vote: result.my_vote,
              same_here_count: result.same_here_count,
              same_here_by_me: result.my_vote === 1,
            }
          : item;
      setLibrary((prev) => prev.map(patch));
      setSolvedPosts((prev) => prev.map(patch));
      setThread((prev) => (prev && prev.id === postId ? patch(prev) : prev));
    } catch (err) {
      setError(err.message);
    }
  }

  async function expressInterest(postId) {
    try {
      await api(`/help-room/${postId}/interest`, {
        method: "POST",
        token,
        body: { note: "I can help with this question." },
      });
      await loadFeed();
      await loadThread();
    } catch (err) {
      setError(err.message);
    }
  }

  async function publishQuestion(event) {
    event.preventDefault();
    const cleanTitle = title.trim();
    const cleanDetails = details.trim();
    if (!cleanTitle || !cleanDetails) {
      setError("Add a title and the details before posting.");
      return;
    }
    const cleanTried = tried.trim();
    const body = cleanTried
      ? `${cleanDetails}\n\n**What I tried**\n\n${cleanTried}`
      : cleanDetails;
    setBusy(true);
    setError("");
    try {
      const created = await api("/help-room/", {
        method: "POST",
        token,
        body: {
          course_id: courseId,
          title: cleanTitle,
          body,
          chapter: chapter || null,
          room_type: "problem",
        },
      });
      setTitle("");
      setDetails("");
      setTried("");
      setChapter("");
      await loadFeed();
      go({ post: String(created.id) });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitReply(event, parentId) {
    event.preventDefault();
    if (!thread) return;
    const key = parentId ? `c-${parentId}` : `p-${thread.id}`;
    const text = (replyDrafts[key] || "").trim();
    if (!text) return;
    setReplyBusy(key);
    try {
      await api(`/help-room/${thread.id}/replies`, {
        method: "POST",
        token,
        body: { body: text, parent_reply_id: parentId || null },
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
      await api(`/help-room/replies/${replyId}/helpful`, { method: "POST", token });
      await loadThread();
      await loadFeed();
    } catch (err) {
      setError(err.message);
    }
  }

  async function acceptSolution(replyId) {
    try {
      const updated = await api(`/help-room/replies/${replyId}/accept`, {
        method: "POST",
        token,
      });
      setThread(updated);
      await loadFeed();
    } catch (err) {
      setError(err.message);
    }
  }

  const nothingYet = loaded && library.length === 0 && solvedPosts.length === 0 && !chapterFilter && tab === "newest";

  return (
    <div className="rooms-page">
      <header className="rooms-header">
        <p className="rooms-course">{courseLabel}</p>
        <div className="rooms-header-row">
          <div>
            <h1>Ask your classmates</h1>
            <p className="rooms-lede">
              Classmates in this course can answer. Professors and TAs do not answer here.
            </p>
          </div>
          {showingList ? (
            <button type="button" className="rooms-primary" onClick={() => go({ view: "create" })}>
              Ask a question
            </button>
          ) : null}
        </div>
      </header>

      {error ? <p className="rooms-error" role="alert">{error}</p> : null}

      {profileId && profile ? (
        <ProfilePanel
          profile={profile}
          onFollow={async () => {
            const next = await api(
              `/help-room/profile/${profile.user_id}/follow?course_id=${courseId}`,
              { method: "POST", token },
            );
            setProfile(next);
          }}
          onBack={() => go({})}
        />
      ) : view === "create" ? (
        <AskForm
          title={title}
          setTitle={setTitle}
          details={details}
          setDetails={setDetails}
          tried={tried}
          setTried={setTried}
          chapter={chapter}
          setChapter={setChapter}
          chapters={chapters}
          matches={matches}
          askerName={user?.display_name || "you"}
          busy={busy}
          onOpenMatch={(id) => go({ post: String(id) })}
          onCancel={() => go({})}
          onPublish={publishQuestion}
        />
      ) : view === "leaderboard" ? (
        <LeaderboardPanel ranks={ranks} onOpen={(id) => go({ user: String(id) })} onBack={() => go({})} />
      ) : showingThread ? (
        thread ? (
          <ThreadView
            thread={thread}
            onBack={() => go({})}
            onVote={vote}
            onInterest={expressInterest}
            onProfile={(id) => go({ user: String(id) })}
            replyDrafts={replyDrafts}
            setReplyDrafts={setReplyDrafts}
            replyBusy={replyBusy}
            onReply={submitReply}
            onHelpful={markHelpful}
            onAccept={acceptSolution}
          />
        ) : (
          <p className="rooms-lede">Loading this question…</p>
        )
      ) : (
        <div className="rooms-layout">
          <div className="rooms-main">
            <div className="rooms-filters">
              <div className="rooms-tabs" role="tablist" aria-label="Question list">
                {[
                  ["newest", "Newest"],
                  ["unanswered", "Unanswered"],
                  ["solved", "Solved"],
                ].map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={tab === id}
                    className={tab === id ? "rooms-tab is-on" : "rooms-tab"}
                    onClick={() => setTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <label className="rooms-chapter">
                <span className="rooms-sr">Chapter</span>
                <select
                  value={chapterFilter}
                  onChange={(event) => setChapterFilter(event.target.value)}
                >
                  <option value="">All chapters</option>
                  {chapters.map((item) => (
                    <option key={item.label} value={item.label}>
                      {item.post_count > 0 ? `${item.label} (${item.post_count})` : item.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {!loaded ? (
              <p className="rooms-empty">Loading questions…</p>
            ) : nothingYet ? (
              <p className="rooms-empty">
                No questions yet. Ask the first one. Someone in {activeCourse.code} may be stuck on the same thing.
              </p>
            ) : visiblePosts.length === 0 ? (
              <p className="rooms-empty">No questions in this view.</p>
            ) : (
              <ul className="rooms-list">
                {visiblePosts.map((post) => (
                  <li key={post.id}>
                    <button type="button" className="rooms-row" onClick={() => go({ post: String(post.id) })}>
                      <StatusMark post={post} />
                      <span className="rooms-row-copy">
                        <span className="rooms-title">{post.title}</span>
                        {snippetOf(post.body) ? (
                          <span className="rooms-snippet">{snippetOf(post.body)}</span>
                        ) : null}
                      </span>
                      <span className="rooms-meta">
                        {post.chapter ? <span className="rooms-tag">{post.chapter}</span> : null}
                        {typeLabel(post.room_type) ? (
                          <span className="rooms-tag">{typeLabel(post.room_type)}</span>
                        ) : null}
                        <span>{askedAgo(post.created_at)}</span>
                        <span>{answerLabel(post.reply_count)}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <aside className="rooms-side">
            <section className="rooms-rules">
              <h2>Before you post</h2>
              <ul>
                <li>Say where you got stuck, not the finished homework.</li>
                <li>Your name shows, so helpful classmates can be recognized.</li>
                <li>Mark an answer as solved only when it actually unlocked the problem.</li>
              </ul>
              <button type="button" className="rooms-textlink" onClick={() => go({ view: "leaderboard" })}>
                Top helpers
              </button>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}

function AskForm({
  title,
  setTitle,
  details,
  setDetails,
  tried,
  setTried,
  chapter,
  setChapter,
  chapters,
  matches,
  askerName,
  busy,
  onOpenMatch,
  onCancel,
  onPublish,
}) {
  return (
    <form className="rooms-form" onSubmit={onPublish}>
      <button type="button" className="rooms-textlink" onClick={onCancel}>
        Back to questions
      </button>
      <h2>Ask a question</h2>
      <label className="rooms-field">
        <span>Title</span>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={200}
          required
          autoComplete="off"
        />
        <span className="rooms-hint">Be specific: what are you trying to do and what went wrong?</span>
      </label>
      {matches.length ? (
        <div className="rooms-similar">
          <p>Similar questions</p>
          <ul>
            {matches.map((post) => (
              <li key={post.id}>
                <button type="button" onClick={() => onOpenMatch(post.id)}>
                  {post.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="rooms-quiet">
        Not sure? <Link to="/student">Try the Study Agent first</Link>
      </p>
      <label className="rooms-field">
        <span>Details</span>
        <textarea
          value={details}
          onChange={(event) => setDetails(event.target.value)}
          required
          rows={6}
        />
      </label>
      <label className="rooms-field">
        <span>What I tried</span>
        <textarea
          value={tried}
          onChange={(event) => setTried(event.target.value)}
          rows={4}
        />
      </label>
      <label className="rooms-field">
        <span>Chapter</span>
        <select value={chapter} onChange={(event) => setChapter(event.target.value)}>
          <option value="">Optional</option>
          {chapters.map((item) => (
            <option key={item.label} value={item.label}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <p className="rooms-identity">Classmates will see this question from {askerName}.</p>
      <button type="submit" className="rooms-primary" disabled={busy || !title.trim() || !details.trim()}>
        {busy ? "Posting…" : "Post"}
      </button>
    </form>
  );
}

function ThreadView({
  thread,
  onBack,
  onVote,
  onInterest,
  onProfile,
  replyDrafts,
  setReplyDrafts,
  replyBusy,
  onReply,
  onHelpful,
  onAccept,
}) {
  const accepted = findAccepted(thread.replies);
  const others = accepted ? withoutReply(thread.replies, accepted.id) : thread.replies || [];
  const draftKey = `p-${thread.id}`;
  return (
    <article className="rooms-thread">
      <button type="button" className="rooms-textlink" onClick={onBack}>
        Back to questions
      </button>
      <header className="rooms-question">
        <StatusMark post={thread} />
        <h2>{thread.title}</h2>
        <p className="rooms-byline">
          <button
            type="button"
            className="rooms-person"
            onClick={() => thread.author_user_id && onProfile(thread.author_user_id)}
            disabled={!thread.author_user_id}
          >
            <Avatar name={thread.author_display} seed={thread.author_handle} size={28} />
            {thread.author_display}
          </button>
          <span>{askedAgo(thread.created_at)}</span>
          {thread.chapter ? <span className="rooms-tag">{thread.chapter}</span> : null}
          {typeLabel(thread.room_type) ? <span className="rooms-tag">{typeLabel(thread.room_type)}</span> : null}
        </p>
        <MarkdownBody text={thread.body} />
        {thread.files?.length ? (
          <ul className="rooms-files">
            {thread.files.map((file) => (
              <li key={file.id}>{file.original_filename}</li>
            ))}
          </ul>
        ) : null}
        <div className="rooms-actions">
          <button
            type="button"
            className={thread.my_vote === 1 ? "is-on" : ""}
            disabled={thread.is_mine}
            onClick={() => onVote(thread.id, 1, thread.is_mine)}
          >
            Upvote
            <span>{thread.up_count || 0}</span>
          </button>
          <button
            type="button"
            className={thread.my_vote === -1 ? "is-on" : ""}
            disabled={thread.is_mine}
            onClick={() => onVote(thread.id, -1, thread.is_mine)}
          >
            Downvote
            <span>{thread.down_count || 0}</span>
          </button>
          {!thread.is_mine ? (
            <button type="button" onClick={() => onInterest(thread.id)}>
              {thread.interested_by_me ? "You offered to help" : "I can help"}
            </button>
          ) : null}
        </div>
      </header>

      {accepted ? (
        <section className="rooms-solved" aria-label="Solved answer">
          <p className="rooms-status rooms-status-solved">
            <StatusIcon state="solved" />
            Solved
          </p>
          <Answer
            reply={accepted}
            canAccept={false}
            replyDrafts={replyDrafts}
            setReplyDrafts={setReplyDrafts}
            replyBusy={replyBusy}
            onReply={onReply}
            onHelpful={onHelpful}
            onAccept={onAccept}
            onProfile={onProfile}
          />
        </section>
      ) : null}

      {others.length ? (
        <div className="rooms-answers">
          <h3>Other answers</h3>
          {others.map((reply) => (
            <Answer
              key={reply.id}
              reply={reply}
              canAccept={thread.is_mine && thread.room_type === "problem"}
              replyDrafts={replyDrafts}
              setReplyDrafts={setReplyDrafts}
              replyBusy={replyBusy}
              onReply={onReply}
              onHelpful={onHelpful}
              onAccept={onAccept}
              onProfile={onProfile}
            />
          ))}
        </div>
      ) : accepted ? null : (
        <p className="rooms-empty">No answers yet.</p>
      )}

      <form className="rooms-composer" onSubmit={(event) => onReply(event, null)}>
        <label className="rooms-field">
          <span>Your answer</span>
          <textarea
            value={replyDrafts[draftKey] || ""}
            onChange={(event) =>
              setReplyDrafts((prev) => ({ ...prev, [draftKey]: event.target.value }))
            }
            required
            rows={5}
          />
        </label>
        <button type="submit" className="rooms-primary" disabled={replyBusy === draftKey}>
          {replyBusy === draftKey ? "Posting…" : "Post answer"}
        </button>
      </form>
    </article>
  );
}

function Answer({
  reply,
  canAccept,
  replyDrafts,
  setReplyDrafts,
  replyBusy,
  onReply,
  onHelpful,
  onAccept,
  onProfile,
  depth = 0,
}) {
  const [open, setOpen] = useState(false);
  const key = `c-${reply.id}`;
  return (
    <div className="rooms-answer" style={{ marginLeft: Math.min(depth, 4) * 12 }}>
      <p className="rooms-byline">
        <button
          type="button"
          className="rooms-person"
          onClick={() => reply.author_user_id && onProfile(reply.author_user_id)}
        >
          <Avatar name={reply.author_display} seed={reply.author_display} size={28} />
          {reply.author_display}
        </button>
        <span>{askedAgo(reply.created_at)}</span>
      </p>
      <div className="rooms-answer-body">
        <MarkdownBody text={reply.body} />
      </div>
      <div className="rooms-actions">
        <button type="button" disabled={reply.is_mine} onClick={() => onHelpful(reply.id)}>
          {reply.marked_helpful_by_me ? "Marked as helpful" : "This helped me"}
          <span>{reply.helpful_count}</span>
        </button>
        <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
          Reply
        </button>
        {canAccept && !reply.is_mine && !reply.accepted ? (
          <button type="button" onClick={() => onAccept(reply.id)}>
            This solved it
          </button>
        ) : null}
      </div>
      {open ? (
        <form className="rooms-reply" onSubmit={(event) => onReply(event, reply.id)}>
          <label className="rooms-field">
            <span className="rooms-sr">Reply</span>
            <textarea
              value={replyDrafts[key] || ""}
              onChange={(event) =>
                setReplyDrafts((prev) => ({ ...prev, [key]: event.target.value }))
              }
              required
              rows={3}
            />
          </label>
          <button type="submit" className="rooms-secondary" disabled={replyBusy === key}>
            {replyBusy === key ? "Posting…" : "Post reply"}
          </button>
        </form>
      ) : null}
      {(reply.children || []).map((child) => (
        <Answer
          key={child.id}
          reply={child}
          depth={depth + 1}
          canAccept={canAccept}
          replyDrafts={replyDrafts}
          setReplyDrafts={setReplyDrafts}
          replyBusy={replyBusy}
          onReply={onReply}
          onHelpful={onHelpful}
          onAccept={onAccept}
          onProfile={onProfile}
        />
      ))}
    </div>
  );
}

function LeaderboardPanel({ ranks, onOpen, onBack }) {
  return (
    <section className="rooms-board">
      <button type="button" className="rooms-textlink" onClick={onBack}>
        Back to questions
      </button>
      <h2>Top helpers</h2>
      <p className="rooms-lede">Classmates whose answers other people marked as helpful.</p>
      {ranks.length === 0 ? (
        <p className="rooms-empty">No one has an answer marked helpful yet.</p>
      ) : (
        <ul className="rooms-ranklist">
          {ranks.map((row) => (
            <li key={row.user_id}>
              <button type="button" onClick={() => onOpen(row.user_id)}>
                <span className="rooms-rank">{row.rank}</span>
                <Avatar name={row.display_name} seed={row.handle} size={36} />
                <span className="rooms-rank-copy">
                  <strong>{row.display_name}</strong>
                  <span>
                    {row.tier}
                    {" · "}
                    {row.node_points} points
                    {" · "}
                    score {row.rooms_score.toFixed(3)}
                  </span>
                </span>
                <Stars count={row.stars} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ProfilePanel({ profile, onFollow, onBack }) {
  const tiles = [
    ["Questions", profile.rooms],
    ["Answers", profile.solutions],
    ["Accepted", profile.accepted],
    ["Helpful votes", profile.helpful_votes],
    ["Followers", profile.followers],
    ["Following", profile.following],
    ["Profile views", profile.profile_views],
    ["Points", profile.node_points],
  ];
  return (
    <section className="rooms-profile">
      <button type="button" className="rooms-textlink" onClick={onBack}>
        Back to questions
      </button>
      <div className="rooms-profile-head">
        <Avatar name={profile.display_name} seed={profile.handle} size={72} />
        <div>
          <h2>{profile.display_name}</h2>
          <p>
            @{profile.handle} · {profile.role_label}
          </p>
          {profile.bio ? <p>{profile.bio}</p> : null}
          <p className="rooms-byline">
            <span>{profile.tier}</span>
            <Stars count={profile.stars} />
            <span>Score {profile.rooms_score.toFixed(3)}</span>
          </p>
          {!profile.is_me ? (
            <button type="button" className="rooms-secondary" onClick={onFollow}>
              {profile.followed_by_me ? "Following" : "Follow"}
            </button>
          ) : null}
        </div>
      </div>
      <dl className="rooms-tiles">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt>{value}</dt>
            <dd>{label}</dd>
          </div>
        ))}
      </dl>
      {profile.skills?.length ? (
        <p className="rooms-meta">
          {profile.skills.map((skill) => (
            <span key={skill} className="rooms-tag">{skill}</span>
          ))}
        </p>
      ) : null}
    </section>
  );
}
