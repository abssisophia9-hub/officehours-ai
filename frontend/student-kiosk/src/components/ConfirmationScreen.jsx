export default function ConfirmationScreen({ result, onReset, onCheckStatus }) {
  return (
    <div className="w-full max-w-2xl animate-fade-in-up rounded-3xl bg-white p-8 text-center shadow-2xl shadow-emerald-200/40 sm:p-10">
      <div className="mx-auto mb-6 flex h-24 w-24 animate-pop-in items-center justify-center rounded-full bg-emerald-100">
        <svg
          className="h-12 w-12 text-emerald-600"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      </div>

      <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
        Request submitted
      </h1>
      <p className="mt-2 text-lg text-slate-500">
        Thanks! Your question is now in the queue for review.
      </p>

      <div className="mt-8 rounded-2xl border border-slate-100 bg-slate-50 p-6 text-left">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Request
          </span>
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-bold text-indigo-700">
            #{result.id}
          </span>
        </div>
        <p className="mt-3 text-lg leading-relaxed text-slate-800">
          “{result.text}”
        </p>
        <p className="mt-4 text-sm font-medium text-slate-500">
          {result.anonymous
            ? "Submitted anonymously"
            : `Submitted as ${result.student_id}`}
        </p>
        <p className="mt-3 text-sm leading-6 text-indigo-700">
          Save code #{result.id} to check status later without signing in.
        </p>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={onCheckStatus}
          className="rounded-2xl border-2 border-indigo-200 bg-indigo-50 px-6 py-5 text-lg font-bold text-indigo-800 transition hover:border-indigo-300 hover:bg-indigo-100 active:scale-[0.99]"
        >
          Check status now
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-2xl bg-slate-900 px-6 py-5 text-lg font-bold text-white shadow-lg transition hover:bg-slate-800 active:scale-[0.99]"
        >
          Submit another question
        </button>
      </div>
    </div>
  );
}
