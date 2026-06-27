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
    <section className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <form
        onSubmit={continueWithScan}
        className="animate-fade-in-up rounded-3xl bg-white p-8 shadow-2xl shadow-indigo-200/40 sm:p-10"
      >
        <div className="mb-8">
          <p className="text-sm font-bold uppercase tracking-wide text-indigo-600">
            Check in
          </p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Scan your student ID barcode
          </h1>
          <p className="mt-4 text-lg leading-8 text-slate-500">
            A USB barcode scanner works like a keyboard: scan the ID, then the
            kiosk will move to the question form. You can also type the ID for
            demo mode.
          </p>
        </div>

        <label
          htmlFor="scanValue"
          className="mb-2 block text-sm font-semibold uppercase tracking-wide text-slate-500"
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
          className="w-full rounded-2xl border-2 border-slate-200 px-5 py-5 text-3xl font-bold tracking-wide text-slate-900 outline-none transition placeholder:text-lg placeholder:font-medium placeholder:tracking-normal focus:border-indigo-500"
        />

        {error && (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-base font-medium text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          className="mt-6 flex w-full items-center justify-center rounded-2xl bg-indigo-600 px-6 py-5 text-xl font-bold text-white shadow-lg shadow-indigo-300 transition hover:bg-indigo-700 active:scale-[0.99]"
        >
          Continue identified
        </button>

        <button
          type="button"
          onClick={continueAnonymously}
          className="mt-3 w-full rounded-2xl border-2 border-slate-200 bg-white px-6 py-5 text-xl font-bold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 active:scale-[0.99]"
        >
          Skip check-in and stay anonymous
        </button>
      </form>

      <aside className="rounded-3xl border border-emerald-100 bg-emerald-950 p-8 text-white shadow-2xl shadow-emerald-200/40">
        <p className="text-sm font-bold uppercase tracking-wide text-emerald-200">
          Hardware prototype
        </p>
        <h2 className="mt-2 text-3xl font-black">Works with cheap scanners</h2>
        <ul className="mt-6 space-y-4 text-lg leading-8 text-emerald-50">
          <li>Use any USB barcode scanner in HID keyboard mode.</li>
          <li>Click this field, scan, and the scanner types the value.</li>
          <li>Manual typing simulates hardware for demos.</li>
          <li>Anonymous submissions still store no student ID.</li>
        </ul>
      </aside>
    </section>
  );
}
