import { useState } from "react";
import { fetchRequestStatus } from "../api/status.js";

const STATUS_STYLES = {
  queued: {
    label: "Queued",
    badge: "bg-slate-100 text-slate-700",
    ring: "ring-slate-200",
  },
  under_review: {
    label: "Under review",
    badge: "bg-amber-100 text-amber-800",
    ring: "ring-amber-200",
  },
  action_planned: {
    label: "Update ready",
    badge: "bg-emerald-100 text-emerald-800",
    ring: "ring-emerald-200",
  },
  closed: {
    label: "Closed",
    badge: "bg-slate-200 text-slate-700",
    ring: "ring-slate-300",
  },
};

export default function StatusLookupScreen({ initialCode = "", onBack }) {
  const [requestCode, setRequestCode] = useState(initialCode);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLookup(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!requestCode.trim()) {
      setError("Enter the request code from your confirmation screen.");
      return;
    }

    setLoading(true);
    try {
      const status = await fetchRequestStatus(requestCode);
      setResult(status);
    } catch (lookupError) {
      setError(lookupError.message);
    } finally {
      setLoading(false);
    }
  }

  const style = result ? STATUS_STYLES[result.status] || STATUS_STYLES.queued : null;

  return (
    <section className="glass-panel w-full max-w-2xl animate-fade-in-up p-8 sm:p-10">
      <div className="mb-8">
        <p className="glass-chip mb-3">Anonymous status check</p>
        <h1 className="font-display mt-2 text-3xl font-bold tracking-tight text-aui-ink sm:text-4xl">
          Check your request status
        </h1>
        <p className="mt-3 text-lg leading-8 text-aui-deep/70">
          Enter the request code you received after submitting. No student ID or
          login is required.
        </p>
      </div>

      <form onSubmit={handleLookup} className="space-y-4">
        <label
          htmlFor="requestCode"
          className="block text-sm font-semibold uppercase tracking-wide text-aui-deep/60"
        >
          Request code
        </label>
        <input
          id="requestCode"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={requestCode}
          onChange={(event) => setRequestCode(event.target.value)}
          placeholder="e.g. 42"
          className="field-glass px-5 py-4 text-2xl font-bold tracking-wide text-aui-ink placeholder:text-lg placeholder:font-medium placeholder:tracking-normal"
        />

        {error ? (
          <div className="rounded-2xl border border-red-200/80 bg-red-50/80 px-5 py-4 text-base font-medium text-red-700 backdrop-blur">
            {error}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary flex w-full items-center justify-center px-6 py-5 text-xl disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Checking..." : "Look up status"}
        </button>
      </form>

      {result ? (
        <div className={`mt-8 rounded-2xl border p-6 ring-1 ${style.ring} bg-slate-50`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Request #{result.request_code}
              </p>
              <h2 className="mt-1 text-2xl font-black text-slate-900">
                {result.headline}
              </h2>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-sm font-bold ${style.badge}`}
            >
              {style.label}
            </span>
          </div>

          <p className="mt-4 text-lg leading-8 text-slate-700">{result.message}</p>

          {result.recommended_next_step ? (
            <p className="mt-4 rounded-xl bg-white p-4 text-sm font-semibold text-slate-700">
              Recommended next step: {result.recommended_next_step}
            </p>
          ) : null}

          {result.agenda_hint ? (
            <p className="mt-3 text-sm font-medium text-slate-500">
              When: {result.agenda_hint}
            </p>
          ) : null}

          {result.meeting_title || result.meeting_when || result.meeting_place ? (
            <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
              <p className="font-bold uppercase tracking-wide text-emerald-700">
                Shared group meeting
              </p>
              {result.meeting_title ? (
                <p className="mt-1 text-base font-semibold">{result.meeting_title}</p>
              ) : null}
              {result.meeting_when ? (
                <p className="mt-1">
                  <strong>When:</strong> {result.meeting_when}
                </p>
              ) : null}
              {result.meeting_place ? (
                <p className="mt-1">
                  <strong>Where:</strong> {result.meeting_place}
                </p>
              ) : null}
              <p className="mt-2 text-xs text-emerald-800/80">
                Classmates stuck on the same topic were invited to this same meeting.
              </p>
            </div>
          ) : null}

          <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">
            Privacy-safe view — your identity is never shown on this page.
          </p>
        </div>
      ) : null}

      <button
        type="button"
        onClick={onBack}
        className="mt-6 w-full rounded-2xl border-2 border-slate-200 bg-white px-6 py-4 text-lg font-bold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
      >
        Back to check-in
      </button>
    </section>
  );
}
