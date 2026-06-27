import { useState } from "react";
import AnonymousToggle from "./AnonymousToggle.jsx";
import { submitRequest } from "../api/requests.js";

const MAX_LENGTH = 1000;

export default function RequestForm({ checkIn, onSubmitted }) {
  const [text, setText] = useState("");
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
      const result = await submitRequest({ text, anonymous, studentId });
      onSubmitted(result);
    } catch (err) {
      setError(
        "We couldn't reach the server. Please try again or ask a staff member."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl animate-fade-in-up rounded-3xl bg-white p-8 shadow-2xl shadow-indigo-200/40 sm:p-10"
    >
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Ask for help
        </h1>
        <p className="mt-2 text-lg text-slate-500">
          Tell us what you're stuck on. A professor will review it during office
          hours.
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
          <p className="mt-1 text-sm text-emerald-700">
            Choose anonymous below if you do not want this request linked to the
            scanned ID.
          </p>
        </div>
      )}

      <label className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500">
        How would you like to submit?
      </label>
      <AnonymousToggle anonymous={anonymous} onChange={setAnonymous} />

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
          placeholder="e.g. I don't understand how recursion works for the final exam…"
          className="w-full resize-none rounded-2xl border-2 border-slate-200 px-5 py-4 text-lg leading-relaxed outline-none transition focus:border-indigo-500"
        />
        <div className="mt-1 text-right text-sm text-slate-400">
          {text.length}/{MAX_LENGTH}
        </div>
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
            Submitting…
          </>
        ) : (
          "Submit request"
        )}
      </button>
    </form>
  );
}
