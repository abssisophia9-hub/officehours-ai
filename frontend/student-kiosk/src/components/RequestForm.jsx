import { useState } from "react";
import AnonymousToggle from "./AnonymousToggle.jsx";
import { submitRequest } from "../api/requests.js";

const MAX_LENGTH = 2000;
const CODE_MAX = 4000;

export default function RequestForm({ checkIn, onSubmitted }) {
  const [text, setText] = useState("");
  const [studentName, setStudentName] = useState("");
  const [course, setCourse] = useState("CS 400");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [anonymous, setAnonymous] = useState(!checkIn?.studentId);
  const [studentId, setStudentId] = useState(checkIn?.studentId || "");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const scannedStudentId = checkIn?.studentId || "";

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (!text.trim()) {
      setError("Please type your question before submitting.");
      return;
    }

    if (!anonymous && !studentId.trim()) {
      setError("Please enter your student ID, or switch to anonymous.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await submitRequest({
        text,
        anonymous,
        studentId,
        studentName,
        course,
        codeSnippet,
      });
      onSubmitted(result);
    } catch (err) {
      setError(
        "We couldn't reach the server. Please try again or ask a staff member.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-3xl animate-fade-in-up rounded-3xl bg-white p-8 shadow-2xl shadow-indigo-200/40 sm:p-10"
    >
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Ask for help
        </h1>
        <p className="mt-2 text-lg text-slate-500">
          Oracle agents analyze your question, match a TA, and draft a teaching
          plan — professor still approves what enters the student KB.
        </p>
      </div>

      {scannedStudentId && (
        <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4">
          <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">
            Checked in
          </p>
          <p className="mt-1 text-lg font-bold text-emerald-950">
            Student ID {scannedStudentId}
          </p>
        </div>
      )}

      <label className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500">
        How would you like to submit?
      </label>
      <AnonymousToggle anonymous={anonymous} onChange={setAnonymous} />

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500">
            Name {anonymous ? "(optional)" : ""}
          </span>
          <input
            value={studentName}
            onChange={(event) => setStudentName(event.target.value)}
            placeholder="Alex Smith"
            className="w-full rounded-2xl border-2 border-slate-200 px-5 py-4 text-lg outline-none transition focus:border-indigo-500"
          />
        </label>
        <label className="block">
          <span className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500">
            Course
          </span>
          <input
            value={course}
            onChange={(event) => setCourse(event.target.value)}
            placeholder="CS 400"
            className="w-full rounded-2xl border-2 border-slate-200 px-5 py-4 text-lg outline-none transition focus:border-indigo-500"
          />
        </label>
      </div>

      {!anonymous && (
        <div className="mt-5 animate-fade-in-up">
          <label
            htmlFor="studentId"
            className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500"
          >
            Student ID
          </label>
          <input
            id="studentId"
            type="text"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            placeholder="e.g. 117027"
            className="w-full rounded-2xl border-2 border-slate-200 px-5 py-4 text-lg outline-none transition focus:border-indigo-500"
          />
        </div>
      )}

      <div className="mt-6">
        <label
          htmlFor="question"
          className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500"
        >
          Your question
        </label>
        <textarea
          id="question"
          value={text}
          maxLength={MAX_LENGTH}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="e.g. I'm getting infinite recursion in my red-black tree delete fixup…"
          className="w-full resize-none rounded-2xl border-2 border-slate-200 px-5 py-4 text-lg leading-relaxed outline-none transition focus:border-indigo-500"
        />
        <div className="mt-1 text-right text-sm text-slate-400">
          {text.length}/{MAX_LENGTH}
        </div>
      </div>

      <div className="mt-4">
        <label
          htmlFor="code"
          className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500"
        >
          Code (optional)
        </label>
        <textarea
          id="code"
          value={codeSnippet}
          maxLength={CODE_MAX}
          onChange={(e) => setCodeSnippet(e.target.value)}
          rows={6}
          placeholder="Paste a short snippet if it helps explain the bug…"
          className="w-full resize-y rounded-2xl border-2 border-slate-200 px-5 py-4 font-mono text-sm leading-relaxed outline-none transition focus:border-indigo-500"
        />
      </div>

      {error && (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-base font-medium text-red-700">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="mt-6 flex w-full items-center justify-center gap-3 rounded-2xl bg-indigo-600 px-6 py-5 text-xl font-bold text-white shadow-lg shadow-indigo-300 transition hover:bg-indigo-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? (
          <>
            <span className="h-6 w-6 animate-spin rounded-full border-[3px] border-white/40 border-t-white" />
            Running Oracle agents…
          </>
        ) : (
          "Submit Question"
        )}
      </button>
    </form>
  );
}
