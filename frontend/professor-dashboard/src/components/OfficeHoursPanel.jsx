import { useState } from "react";

const DEFAULT_WINDOWS = [
  { day: "Monday", start: "10:00", end: "11:30", location: "Room 204" },
  { day: "Wednesday", start: "14:00", end: "15:30", location: "Zoom" },
];

export default function OfficeHoursPanel() {
  const [windows, setWindows] = useState(DEFAULT_WINDOWS);
  const [draft, setDraft] = useState({
    day: "Monday",
    start: "09:00",
    end: "10:00",
    location: "",
  });

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function addWindow(event) {
    event.preventDefault();
    if (!draft.start || !draft.end) {
      return;
    }

    setWindows((current) => [
      ...current,
      { ...draft, location: draft.location.trim() || "TBD" },
    ]);
    setDraft({ day: draft.day, start: "09:00", end: "10:00", location: "" });
  }

  function removeWindow(indexToRemove) {
    setWindows((current) =>
      current.filter((_, index) => index !== indexToRemove),
    );
  }

  return (
    <section className="rounded-3xl border border-indigo-100 bg-indigo-950 p-6 text-white shadow-sm">
      <p className="text-sm font-semibold uppercase tracking-wide text-indigo-200">
        Availability setup
      </p>
      <h2 className="mt-1 text-2xl font-black">Office hours</h2>
      <p className="mt-2 text-sm leading-6 text-indigo-100">
        Professors should specify office-hour windows in this dashboard. The
        backend should persist these windows before recommendation logic uses
        them to suggest group sessions or 1:1 follow-ups.
      </p>

      <div className="mt-6 space-y-3">
        {windows.map((window, index) => (
          <div
            key={`${window.day}-${window.start}-${index}`}
            className="flex items-center justify-between gap-4 rounded-2xl bg-white/10 p-4"
          >
            <div>
              <p className="font-bold">
                {window.day}, {window.start} - {window.end}
              </p>
              <p className="text-sm text-indigo-100">{window.location}</p>
            </div>
            <button
              type="button"
              onClick={() => removeWindow(index)}
              className="rounded-full bg-white/10 px-3 py-1 text-sm font-bold text-indigo-50 hover:bg-white/20"
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <form onSubmit={addWindow} className="mt-6 grid gap-3 md:grid-cols-5">
        <label className="md:col-span-1">
          <span className="text-xs font-bold uppercase text-indigo-200">
            Day
          </span>
          <select
            value={draft.day}
            onChange={(event) => updateDraft("day", event.target.value)}
            className="mt-1 w-full rounded-xl border-0 bg-white px-3 py-2 text-slate-950"
          >
            {[
              "Monday",
              "Tuesday",
              "Wednesday",
              "Thursday",
              "Friday",
            ].map((day) => (
              <option key={day}>{day}</option>
            ))}
          </select>
        </label>

        <TimeInput
          label="Start"
          value={draft.start}
          onChange={(value) => updateDraft("start", value)}
        />
        <TimeInput
          label="End"
          value={draft.end}
          onChange={(value) => updateDraft("end", value)}
        />

        <label className="md:col-span-1">
          <span className="text-xs font-bold uppercase text-indigo-200">
            Location
          </span>
          <input
            value={draft.location}
            onChange={(event) => updateDraft("location", event.target.value)}
            placeholder="Room or link"
            className="mt-1 w-full rounded-xl border-0 bg-white px-3 py-2 text-slate-950 placeholder:text-slate-400"
          />
        </label>

        <button
          type="submit"
          className="self-end rounded-xl bg-emerald-400 px-4 py-2 font-black text-emerald-950 hover:bg-emerald-300"
        >
          Add slot
        </button>
      </form>
    </section>
  );
}

function TimeInput({ label, value, onChange }) {
  return (
    <label>
      <span className="text-xs font-bold uppercase text-indigo-200">
        {label}
      </span>
      <input
        type="time"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-xl border-0 bg-white px-3 py-2 text-slate-950"
      />
    </label>
  );
}
