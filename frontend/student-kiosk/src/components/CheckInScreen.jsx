import { useEffect, useRef, useState } from "react";
import { parseStudentIdFromScan } from "../utils/scanParser.js";

export default function CheckInScreen({ onContinue }) {
  const [scanValue, setScanValue] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function continueWithScan(event) {
    event.preventDefault();
    const studentId = parseStudentIdFromScan(scanValue);

    if (!studentId) {
      setError("Scan your ID barcode or type your student ID to continue.");
      inputRef.current?.focus();
      return;
    }

    onContinue({ studentId, source: "barcode" });
  }

  function continueAnonymously() {
    onContinue({ studentId: "", source: "anonymous" });
  }

  return (
    <section className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <form
        onSubmit={continueWithScan}
        className="glass-panel animate-fade-in-up p-8 sm:p-10"
      >
        <div className="mb-8">
          <p className="glass-chip mb-4">Check in</p>
          <h1 className="font-display text-3xl font-bold tracking-tight text-aui-ink sm:text-5xl">
            Scan your student ID
          </h1>
          <p className="mt-4 text-lg leading-8 text-aui-deep/70">
            A USB barcode scanner works like a keyboard: scan the ID, then the
            kiosk moves to the question form. You can also type the ID for demo
            mode.
          </p>
        </div>

        <label
          htmlFor="scanValue"
          className="mb-2 block text-sm font-semibold uppercase tracking-wide text-aui-deep/60"
        >
          Student ID / barcode value
        </label>
        <input
          ref={inputRef}
          id="scanValue"
          type="text"
          inputMode="text"
          autoComplete="off"
          value={scanValue}
          onChange={(event) => {
            setScanValue(event.target.value);
            setError("");
          }}
          placeholder="Scan barcode or type 117027"
          className="field-glass px-5 py-5 text-3xl font-bold tracking-wide text-aui-ink placeholder:text-lg placeholder:font-medium placeholder:tracking-normal"
        />

        {error && (
          <div className="mt-4 rounded-2xl border border-red-200/80 bg-red-50/80 px-5 py-4 text-base font-medium text-red-700 backdrop-blur">
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary mt-6 flex w-full items-center justify-center px-6 py-5 text-xl">
          Continue identified
        </button>

        <button
          type="button"
          onClick={continueAnonymously}
          className="btn-ghost mt-3 w-full rounded-2xl px-6 py-5 text-xl"
        >
          Skip check-in and stay anonymous
        </button>
      </form>

      <aside className="glass-panel glass-panel-deep relative overflow-hidden p-8 text-white">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-12 left-8 h-36 w-36 rounded-full bg-aui-sand/30 blur-2xl" />
        <img
          src="/aui-logo.png"
          alt=""
          aria-hidden="true"
          className="mb-6 h-14 w-auto brightness-0 invert opacity-95"
        />
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-100/90">
          Hardware prototype
        </p>
        <h2 className="font-display mt-2 text-3xl font-bold">
          Built for AUI office hours
        </h2>
        <ul className="mt-6 space-y-4 text-lg leading-8 text-emerald-50/95">
          <li>Use any USB barcode scanner in HID keyboard mode.</li>
          <li>Click this field, scan, and the scanner types the value.</li>
          <li>Manual typing simulates hardware for demos.</li>
          <li>Anonymous submissions still store no student ID.</li>
        </ul>
      </aside>
    </section>
  );
}
