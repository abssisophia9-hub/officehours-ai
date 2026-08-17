import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { api, apiUpload } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { MarkdownBody, avatarHue, initials, timeAgo } from "../lib/rooms.jsx";

const ROOM_TYPES = [
  {
    id: "problem",
    label: "Problem",
    hint: "An issue or failure that needs a resolution — the missing check, not the write-up.",
  },
  {
    id: "discussion",
    label: "Discussion",
    hint: "Architecture, design review, or a general course topic.",
  },
  {
    id: "article",
    label: "Article",
    hint: "A tutorial or technical guideline you want classmates to reuse.",
  },
];

const SUGGESTED_TAGS = [
  "QuizPrep",
  "StudyGroup",
  "SSE",
  "AUI",
  "OfficeHours",
  "TraceWalk",
];

function Avatar({ name, seed, size = 36 }) {
  const hue = avatarHue(seed || name);
  return (
    <span
      className="rf-avatar"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: `hsl(${hue} 42% 32%)`,
      }}
    >
      {initials(name)}
    </span>
  );
}

function Stars({ count }) {
  return (
    <span className="rf-stars" aria-label={`${count} stars`}>
      {"★".repeat(count)}
      {"☆".repeat(Math.max(0, 5 - count))}
    </span>
  );
}

function VoteColumn({ score, mine, disabled, onVote }) {
  return (
    <div className="rf-vote">
      <button
        type="button"
        className={`rf-vote-btn${mine === 1 ? " is-up" : ""}`}
        disabled={disabled}
        aria-label="Upvote"
        onClick={() => onVote(1)}
      >
        ▲
      </button>
      <span className={`rf-vote-n${mine ? " is-on" : ""}`}>{score}</span>
      <button
        type="button"
        className={`rf-vote-btn${mine === -1 ? " is-down" : ""}`}
        disabled={disabled}
        aria-label="Downvote"
        onClick={() => onVote(-1)}
      >
        ▼
      </button>
    </div>
  );
}

export default function StuckRoomPage() {
  const { token, activeCourse } = useAuth();
  const [params, setParams] = useSearchParams();
  const view = params.get("view") || "rooms";
  const threadId = params.get("post");
  const profileId = params.get("user");

  const [community, setCommunity] = useState(null);
  const [posts, setPosts] = useState([]);
  const [thread, setThread] = useState(null);
  const [ranks, setRanks] = useState([]);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [chapterFilter, setChapterFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [sort, setSort] = useState("hot");

  const [step, setStep] = useState(1);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [roomType, setRoomType] = useState("problem");
  const [chapter, setChapter] = useState("");
  const [tagDraft, setTagDraft] = useState("");
  const [tags, setTags] = useState([]);
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [replyDrafts, setReplyDrafts] = useState({});
  const [replyBusy, setReplyBusy] = useState(null);

  const courseId = activeCourse?.id;

  const loadFeed = useCallback(async () => {
    if (!courseId || !token) return;
    const qs = new URLSearchParams({ course_id: String(courseId), sort });
    if (chapterFilter) qs.set("chapter", chapterFilter);
    if (typeFilter) qs.set("room_type", typeFilter);
    try {
      const [meta, feed, board] = await Promise.all([
        api(`/help-room/community/?course_id=${courseId}`, { token }),
        api(`/help-room/?${qs}`, { token }),
        api(`/help-room/ranks/?course_id=${courseId}`, { token }),
      ]);
      setCommunity(meta);
      setPosts(feed);
      setRanks(board);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [courseId, token, sort, chapterFilter, typeFilter]);

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

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
  }

  const name = community?.community_name || `r/${String(activeCourse.code || "").replace(/\s+/g, "")}`;

  function go(next) {
    setParams(next);
  }

  function addTag(raw) {
    const tokenTag = String(raw || "")
      .replace(/[^A-Za-z0-9_]/g, "")
      .slice(0, 40);
    if (!tokenTag || tags.includes(tokenTag)) return;
    setTags((prev) => [...prev, tokenTag].slice(0, 8));
    setTagDraft("");
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
        item.id === postId
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
      setPosts((prev) => prev.map(patch));
      setThread((prev) => (prev ? patch(prev) : prev));
    } catch (err) {
      setError(err.message);
    }
  }

  async function expressInterest(postId) {
    try {
      await api(`/help-room/${postId}/interest`, {
        method: "POST",
        token,
        body: { note: "I can help with this room — happy to compare notes." },
      });
      await loadFeed();
      await loadThread();
    } catch (err) {
      setError(err.message);
    }
  }

  async function publishRoom(event) {
    event.preventDefault();
    if (!title.trim() || !body.trim() || !chapter) {
      setError("Title, description, and a chapter are required to publish.");
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
          chapter,
          room_type: roomType,
          tags,
        },
      });
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        await apiUpload(`/help-room/${created.id}/files`, { token, formData: form });
      }
      setTitle("");
      setBody("");
      setChapter("");
      setTags([]);
      setFiles([]);
      setStep(1);
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

  const chapters = community?.chapters || [];
  const resolutionPct = Math.round((community?.resolution_rate || 0) * 100);

  return (
    <div className="rf-page">
      <header className="rf-top">
        <div>
          <p className="rf-kicker">AUI Rooms · {activeCourse.code} classmates only</p>
          <h1>{name}</h1>
        </div>
        <button type="button" className="btn-primary px-5 py-2.5 text-sm" onClick={() => go({ view: "create" })}>
          Initialize Room
        </button>
      </header>

      {error ? <p className="rf-error">{error}</p> : null}

      <div className="rf-layout">
        <aside className="rf-left">
          <nav className="rf-side-nav">
            <button type="button" className={view === "rooms" && !threadId && !profileId ? "is-on" : ""} onClick={() => go({})}>
              Rooms
            </button>
            <button type="button" className={view === "fields" ? "is-on" : ""} onClick={() => go({ view: "fields" })}>
              Chapters
            </button>
            <button
              type="button"
              className={view === "leaderboard" ? "is-on" : ""}
              onClick={() => go({ view: "leaderboard" })}
            >
              Leaderboard
            </button>
          </nav>
          <div className="rf-card">
            <h3>Chapters</h3>
            <p className="bh-card-note">
              {community?.chapter_source === "syllabus+canvas"
                ? "Syllabus outline for this course, plus Canvas modules from the linked LMS course."
                : "Syllabus outline for this course. Canvas modules join this list when the course is linked."}
            </p>
            <ul className="rf-chapter-list">
              <li>
                <button type="button" className={!chapterFilter ? "is-on" : ""} onClick={() => setChapterFilter("")}>
                  All chapters <span>{community?.post_count || 0}</span>
                </button>
              </li>
              {chapters.map((item) => (
                <li key={item.label}>
                  <button
                    type="button"
                    className={chapterFilter === item.label ? "is-on" : ""}
                    onClick={() => {
                      setChapterFilter(item.label);
                      go({});
                    }}
                  >
                    {item.label} <span>{item.post_count}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <div className="rf-main">
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
            <CreateWizard
              step={step}
              setStep={setStep}
              title={title}
              setTitle={setTitle}
              body={body}
              setBody={setBody}
              roomType={roomType}
              setRoomType={setRoomType}
              chapter={chapter}
              setChapter={setChapter}
              chapters={chapters}
              chapterSource={community?.chapter_source}
              tags={tags}
              tagDraft={tagDraft}
              setTagDraft={setTagDraft}
              addTag={addTag}
              setTags={setTags}
              files={files}
              setFiles={setFiles}
              busy={busy}
              onCancel={() => go({})}
              onPublish={publishRoom}
            />
          ) : view === "leaderboard" ? (
            <LeaderboardPanel ranks={ranks} onOpen={(id) => go({ user: String(id) })} />
          ) : view === "fields" ? (
            <FieldsGrid
              chapters={chapters}
              chapterSource={community?.chapter_source}
              onPick={(label) => {
                setChapterFilter(label);
                go({});
              }}
            />
          ) : threadId && thread ? (
            <ThreadView
              thread={thread}
              name={name}
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
            <Feed
              posts={posts}
              sort={sort}
              setSort={setSort}
              typeFilter={typeFilter}
              setTypeFilter={setTypeFilter}
              onOpen={(id) => go({ post: String(id) })}
              onVote={vote}
              onInterest={expressInterest}
              onProfile={(id) => go({ user: String(id) })}
              onCreate={() => go({ view: "create" })}
              courseCode={activeCourse.code}
            />
          )}
        </div>

        <aside className="rf-right">
          <div className="rf-card rf-pulse">
            <h3>Community Pulse</h3>
            <dl>
              <div>
                <dt>{community?.classmate_count ?? "—"}</dt>
                <dd>Classmates</dd>
              </div>
              <div>
                <dt>{community?.open_count ?? community?.post_count ?? 0}</dt>
                <dd>Active rooms</dd>
              </div>
              <div>
                <dt>{resolutionPct}%</dt>
                <dd>Resolution</dd>
              </div>
            </dl>
            <button type="button" className="btn-primary mt-4 w-full px-4 py-2.5 text-sm" onClick={() => go({ view: "create" })}>
              Initialize Room
            </button>
          </div>
          <div className="rf-card">
            <h3>Room rules</h3>
            <ol className="rf-rules">
              <li>Share the stuck point, not the homework write-up.</li>
              <li>Rooms are named — helpers show on the leaderboard.</li>
              <li>Accept a solution only when it truly unlocked it.</li>
              <li>Grades, integrity, and crises go to Quiet ask.</li>
              <li>Staff are not in this room.</li>
            </ol>
            <p className="rf-quiet">
              Need staff? <Link to="/student#ask">Quiet ask</Link>
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Feed({
  posts,
  sort,
  setSort,
  typeFilter,
  setTypeFilter,
  onOpen,
  onVote,
  onInterest,
  onProfile,
  onCreate,
  courseCode,
}) {
  return (
    <>
      <div className="rf-toolbar">
        {["hot", "new", "top"].map((key) => (
          <button key={key} type="button" className={sort === key ? "is-on" : ""} onClick={() => setSort(key)}>
            {key[0].toUpperCase() + key.slice(1)}
          </button>
        ))}
        <span className="rf-toolbar-gap" />
        <button type="button" className={!typeFilter ? "is-on" : ""} onClick={() => setTypeFilter("")}>
          All
        </button>
        {ROOM_TYPES.map((item) => (
          <button
            key={item.id}
            type="button"
            className={typeFilter === item.id ? "is-on" : ""}
            onClick={() => setTypeFilter(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {posts.length === 0 ? (
        <div className="rf-card">
          <h2>No rooms yet in {courseCode}</h2>
          <p className="bh-card-note">Initialize a Problem, Discussion, or Article so classmates can offer help.</p>
          <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm" onClick={onCreate}>
            Initialize Room
          </button>
        </div>
      ) : (
        <div className="rf-feed">
          {posts.map((post) => (
            <RoomCard
              key={post.id}
              post={post}
              onOpen={() => onOpen(post.id)}
              onVote={(value) => onVote(post.id, value, post.is_mine)}
              onInterest={() => onInterest(post.id)}
              onProfile={() => post.author_user_id && onProfile(post.author_user_id)}
            />
          ))}
        </div>
      )}
    </>
  );
}

function RoomCard({ post, onOpen, onVote, onInterest, onProfile }) {
  return (
    <article className="rf-card rf-room-card">
      <VoteColumn score={post.score} mine={post.my_vote} disabled={post.is_mine} onVote={onVote} />
      <div className="rf-room-body">
        <div className="rf-badges">
          <span className={`rf-type rf-type-${post.room_type}`}>{post.room_type}</span>
          <span className={`rf-status rf-status-${post.status}`}>{post.status}</span>
          {post.chapter ? <span className="rf-field">{post.chapter}</span> : null}
        </div>
        <button type="button" className="rf-title-btn" onClick={onOpen}>
          <h2>{post.title}</h2>
        </button>
        <p className="rf-snippet">{post.body}</p>
        {post.tags?.length ? (
          <p className="rf-tags">
            {post.tags.map((tag) => (
              <span key={tag}>#{tag}</span>
            ))}
          </p>
        ) : null}
        <div className="rf-meta-row">
          <button type="button" className="rf-author" onClick={onProfile} disabled={!post.author_user_id}>
            <Avatar name={post.author_display} seed={post.author_handle || post.author_display} size={28} />
            <span>{post.author_display}</span>
            {post.author_handle ? <em>@{post.author_handle}</em> : null}
          </button>
          <span>{timeAgo(post.created_at)}</span>
          <span>
            {post.reply_count} solution{post.reply_count === 1 ? "" : "s"}
          </span>
          {!post.is_mine ? (
            <button
              type="button"
              className={`rf-interest${post.interested_by_me ? " is-on" : ""}`}
              onClick={onInterest}
            >
              {post.interested_by_me ? "Interest sent" : "Express Interest"}
            </button>
          ) : (
            <span className="rf-interest-count">{post.interest_count} interested</span>
          )}
        </div>
      </div>
    </article>
  );
}

function ThreadView({
  thread,
  name,
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
  return (
    <article className="rf-card">
      <button type="button" className="rf-back" onClick={onBack}>
        ← Back to {name}
      </button>
      <div className="rf-room-card rf-thread-head">
        <VoteColumn
          score={thread.score}
          mine={thread.my_vote}
          disabled={thread.is_mine}
          onVote={(value) => onVote(thread.id, value, thread.is_mine)}
        />
        <div className="rf-room-body">
          <div className="rf-badges">
            <span className={`rf-type rf-type-${thread.room_type}`}>{thread.room_type}</span>
            <span className={`rf-status rf-status-${thread.status}`}>{thread.status}</span>
            {thread.chapter ? <span className="rf-field">{thread.chapter}</span> : null}
          </div>
          <h2>{thread.title}</h2>
          <MarkdownBody text={thread.body} />
          {thread.tags?.length ? (
            <p className="rf-tags">
              {thread.tags.map((tag) => (
                <span key={tag}>#{tag}</span>
              ))}
            </p>
          ) : null}
          {thread.files?.length ? (
            <ul className="rf-files">
              {thread.files.map((file) => (
                <li key={file.id}>{file.original_filename}</li>
              ))}
            </ul>
          ) : null}
          <div className="rf-meta-row">
            <button type="button" className="rf-author" onClick={() => thread.author_user_id && onProfile(thread.author_user_id)}>
              <Avatar name={thread.author_display} seed={thread.author_handle} size={28} />
              {thread.author_display}
            </button>
            <span>{timeAgo(thread.created_at)}</span>
            {!thread.is_mine ? (
              <button type="button" className="rf-interest" onClick={() => onInterest(thread.id)}>
                {thread.interested_by_me ? "Interest sent" : "Express Interest"}
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <form className="rf-composer" onSubmit={(event) => onReply(event, null)}>
        <textarea
          className="field-glass min-h-20 w-full px-3 py-2 text-sm"
          placeholder="Offer a solution or perspective — not the finished write-up."
          value={replyDrafts[`p-${thread.id}`] || ""}
          onChange={(event) =>
            setReplyDrafts((prev) => ({ ...prev, [`p-${thread.id}`]: event.target.value }))
          }
          required
        />
        <button type="submit" className="btn-primary px-4 py-2 text-sm" disabled={replyBusy === `p-${thread.id}`}>
          {replyBusy === `p-${thread.id}` ? "Posting…" : "Post solution"}
        </button>
      </form>

      <div className="rf-comments">
        {(thread.replies || []).map((reply) => (
          <Comment
            key={reply.id}
            reply={reply}
            depth={0}
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
    </article>
  );
}

function Comment({
  reply,
  depth,
  canAccept,
  replyDrafts,
  setReplyDrafts,
  replyBusy,
  onReply,
  onHelpful,
  onAccept,
  onProfile,
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rf-comment" style={{ marginLeft: Math.min(depth, 5) * 16 }}>
      <button type="button" className="rf-author" onClick={() => reply.author_user_id && onProfile(reply.author_user_id)}>
        <Avatar name={reply.author_display} seed={reply.author_display} size={26} />
        <strong>{reply.author_display}</strong>
      </button>
      {reply.accepted ? <span className="rf-accepted">Accepted</span> : null}
      <p>{reply.body}</p>
      <div className="rf-comment-actions">
        <button type="button" disabled={reply.is_mine} onClick={() => onHelpful(reply.id)}>
          {reply.marked_helpful_by_me ? "Helpful" : "Helpful vote"} · {reply.helpful_count}
        </button>
        <button type="button" onClick={() => setOpen((value) => !value)}>
          Reply
        </button>
        {canAccept && !reply.is_mine ? (
          <button type="button" onClick={() => onAccept(reply.id)}>
            Accept solution
          </button>
        ) : null}
      </div>
      {open ? (
        <form onSubmit={(event) => onReply(event, reply.id)}>
          <textarea
            className="field-glass mt-2 min-h-16 w-full px-3 py-2 text-sm"
            value={replyDrafts[`c-${reply.id}`] || ""}
            onChange={(event) =>
              setReplyDrafts((prev) => ({ ...prev, [`c-${reply.id}`]: event.target.value }))
            }
            required
          />
          <button type="submit" className="btn-ghost mt-2 px-3 py-1.5 text-xs" disabled={replyBusy === `c-${reply.id}`}>
            Comment
          </button>
        </form>
      ) : null}
      {(reply.children || []).map((child) => (
        <Comment
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

function CreateWizard({
  step,
  setStep,
  title,
  setTitle,
  body,
  setBody,
  roomType,
  setRoomType,
  chapter,
  setChapter,
  chapters,
  chapterSource,
  tags,
  tagDraft,
  setTagDraft,
  addTag,
  setTags,
  files,
  setFiles,
  busy,
  onCancel,
  onPublish,
}) {
  return (
    <form className="rf-wizard" onSubmit={onPublish}>
      <div className="rf-wizard-main">
        <button type="button" className="rf-back" onClick={onCancel}>
          ← Cancel
        </button>
        <p className="rf-kicker">Create a Room · Step {step} of 3</p>
        {step === 1 ? (
          <>
            <h2>General information</h2>
            <input
              className="field-glass w-full px-4 py-2.5 text-sm"
              placeholder="Title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
            />
            <textarea
              className="field-glass min-h-48 w-full px-4 py-2.5 text-sm"
              placeholder="Description (Markdown supported: **bold**, `code`, lists)"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              required
            />
            <p className="bh-card-note">
              Rooms are named. Helping here puts you on the course leaderboard.
              Need to ask staff privately? Use Quiet ask.
            </p>
          </>
        ) : null}
        {step === 2 ? (
          <>
            <h2>Classification type</h2>
            <div className="rf-type-grid">
              {ROOM_TYPES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`rf-type-pick${roomType === item.id ? " is-on" : ""}`}
                  onClick={() => setRoomType(item.id)}
                >
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}
        {step === 3 ? (
          <>
            <h2>Select course chapter</h2>
            <p className="bh-card-note">
              {chapterSource === "syllabus+canvas"
                ? "These chapters come from this course’s syllabus, plus Canvas modules from the linked LMS course. You pick one — you don’t type the list."
                : "These chapters come from this course’s syllabus. Canvas modules join the list when the professor links the LMS course. You pick one — you don’t type the list."}
            </p>
            <div className="rf-chapter-grid">
              {chapters.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className={chapter === item.label ? "is-on" : ""}
                  onClick={() => setChapter(item.label)}
                >
                  {item.label}
                  {item.source === "canvas" || item.source === "both" ? (
                    <small className="rf-src">Canvas</small>
                  ) : null}
                </button>
              ))}
            </div>
          </>
        ) : null}
        <div className="rf-wizard-nav">
          {step > 1 ? (
            <button type="button" className="btn-ghost px-4 py-2 text-sm" onClick={() => setStep(step - 1)}>
              Back
            </button>
          ) : null}
          {step < 3 ? (
            <button
              type="button"
              className="btn-primary px-5 py-2 text-sm"
              onClick={() => {
                if (step === 1 && (!title.trim() || !body.trim())) return;
                setStep(step + 1);
              }}
            >
              Continue
            </button>
          ) : (
            <button type="submit" className="btn-primary px-5 py-2 text-sm" disabled={busy || !chapter}>
              {busy ? "Publishing…" : "Publish Room"}
            </button>
          )}
        </div>
      </div>
      <aside className="rf-wizard-side">
        <div className="rf-card">
          <h3>Room tags</h3>
          <p className="bh-card-note">Hashtags for discoverability inside this course.</p>
          <div className="rf-tag-row">
            <input
              className="field-glass px-3 py-2 text-sm"
              placeholder="#Hashing"
              value={tagDraft}
              onChange={(event) => setTagDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addTag(tagDraft);
                }
              }}
            />
            <button type="button" className="btn-ghost px-3 py-2 text-xs" onClick={() => addTag(tagDraft)}>
              Add
            </button>
          </div>
          <div className="rf-tags">
            {tags.map((tag) => (
              <button key={tag} type="button" onClick={() => setTags(tags.filter((item) => item !== tag))}>
                #{tag} ×
              </button>
            ))}
          </div>
          <div className="rf-suggest">
            {SUGGESTED_TAGS.map((tag) => (
              <button key={tag} type="button" onClick={() => addTag(tag)}>
                #{tag}
              </button>
            ))}
          </div>
        </div>
        <div className="rf-card">
          <h3>Attachments</h3>
          <p className="bh-card-note">CSV, PDF, MATLAB, STEP, PNG, ZIP · 10 MB max</p>
          <label className="rf-drop">
            Drop files or browse
            <input
              type="file"
              multiple
              hidden
              onChange={(event) => setFiles([...files, ...Array.from(event.target.files || [])])}
            />
          </label>
          <ul className="rf-files">
            {files.map((file) => (
              <li key={file.name}>
                {file.name} · {Math.round(file.size / 1024)} KB
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </form>
  );
}

function FieldsGrid({ chapters, chapterSource, onPick }) {
  return (
    <div className="rf-card">
      <h2>Course chapters</h2>
      <p className="bh-card-note">
        {chapterSource === "syllabus+canvas"
          ? "Syllabus outline for this course, plus Canvas modules from the linked LMS course. Students do not add chapters here."
          : "Syllabus outline for this course. Canvas modules join this list when the course is linked. Students do not add chapters here."}
      </p>
      <div className="rf-chapter-grid mt-4">
        {chapters.map((item) => (
          <button key={item.label} type="button" onClick={() => onPick(item.label)}>
            <strong>{item.label}</strong>
            <span>
              {item.post_count} rooms
              {item.source === "canvas" || item.source === "both" ? " · Canvas" : ""}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function LeaderboardPanel({ ranks, onOpen }) {
  const top = ranks.slice(0, 3);
  const rest = ranks.slice(3);
  return (
    <div className="rf-card">
      <h2>Leaderboard</h2>
      <p className="bh-card-note">
        Ranked by Hilbert Weight ŵ (quality over volume). Score(W) is ŵ; Base is Node Points.
      </p>
      <div className="rf-podium">
        {top.map((row, index) => (
          <button key={row.user_id} type="button" className={`rf-podium-slot place-${index + 1}`} onClick={() => onOpen(row.user_id)}>
            <Avatar name={row.display_name} seed={row.handle} size={index === 0 ? 72 : 56} />
            <strong>{row.display_name}</strong>
            <span className="rf-tier">{row.tier}</span>
            <Stars count={row.stars} />
            <em>{row.rooms_score.toFixed(3)}</em>
          </button>
        ))}
      </div>
      <table className="rf-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Classmate</th>
            <th>Level</th>
            <th>Points</th>
            <th>Score(W)</th>
          </tr>
        </thead>
        <tbody>
          {ranks.map((row) => (
            <tr key={row.user_id}>
              <td>{row.rank}</td>
              <td>
                <button type="button" className="rf-author" onClick={() => onOpen(row.user_id)}>
                  <Avatar name={row.display_name} seed={row.handle} size={28} />
                  {row.display_name}
                </button>
              </td>
              <td>{row.tier}</td>
              <td>
                ⚡ {row.node_points}
              </td>
              <td>
                {row.hilbert_weight.toFixed(3)}
                <small>Base {row.node_points}</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rest.length === 0 ? <p className="bh-card-note mt-3">View All Rankings — everyone in this course is already listed.</p> : null}
    </div>
  );
}

function ProfilePanel({ profile, onFollow, onBack }) {
  const tiles = [
    ["Rooms", profile.rooms],
    ["Solutions", profile.solutions],
    ["Accepted", profile.accepted],
    ["Helpful votes", profile.helpful_votes],
    ["Followers", profile.followers],
    ["Following", profile.following],
    ["Profile views", profile.profile_views],
    ["Legacy score", profile.node_points],
  ];
  return (
    <div className="rf-card">
      <button type="button" className="rf-back" onClick={onBack}>
        ← Back to rooms
      </button>
      <div className="rf-profile-head">
        <Avatar name={profile.display_name} seed={profile.handle} size={84} />
        <div>
          <h2>{profile.display_name}</h2>
          <p>
            @{profile.handle} · {profile.role_label}
          </p>
          {profile.bio ? <p className="rf-bio">{profile.bio}</p> : null}
          {!profile.is_me ? (
            <button type="button" className="btn-primary mt-3 px-4 py-2 text-sm" onClick={onFollow}>
              {profile.followed_by_me ? "Following" : "Follow"}
            </button>
          ) : null}
        </div>
        <div className="rf-scorebox">
          <p className="rf-kicker">ROOMS score</p>
          <strong>{profile.rooms_score.toFixed(3)}</strong>
          <span className="rf-tier">{profile.tier}</span>
          <Stars count={profile.stars} />
          <p>
            Hilbert Weight ŵ {profile.hilbert_weight.toFixed(3)}
            <br />
            Node Points {profile.node_points}
          </p>
        </div>
      </div>
      <div className="rf-tiles">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt>{value}</dt>
            <dd>{label}</dd>
          </div>
        ))}
      </div>
      {profile.skills?.length ? (
        <p className="rf-tags mt-4">
          {profile.skills.map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </p>
      ) : null}
    </div>
  );
}
