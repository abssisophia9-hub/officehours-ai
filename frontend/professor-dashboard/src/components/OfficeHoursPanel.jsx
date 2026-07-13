import { useEffect, useState } from "react";
import {
  createOfficeHoursWindow,
  deleteOfficeHoursWindow,
  fetchOfficeHours,
} from "../api/officeHours.js";

export default function OfficeHoursPanel() {
  const [windows, setWindows] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({
    day: "Monday",
    start: "09:00",
    end: "10:00",
    location: "",
  });

  useEffect(() => {
    loadWindows();
  }, []);

  async function loadWindows() {
    setStatus("loading");
    setError("");

    try {
      const data = await fetchOfficeHours();
      setWindows(data);
      setStatus("success");
    } catch (loadError) {
      setStatus("error");
      setError(loadError.message);
    }
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function addWindow(event) {
    event.preventDefault();
    if (!draft.start || !draft.end) {
      return;
    }

    setSaving(true);
    setError("");

    try {
      const created = await createOfficeHoursWindow({
        day: draft.day,
        start: draft.start,
        end: draft.end,
        location: draft.location.trim() || "TBD",
      });
      setWindows((current) => [...current, created]);
      setDraft({ day: draft.day, start: "09:00", end: "10:00", location: "" });
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeWindow(windowId) {
    setSaving(true);
    setError("");

    try {
      await deleteOfficeHoursWindow(windowId);
      setWindows((current) => current.filter((window) => window.id !== windowId));
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="glass-panel glass-panel-deep bg-[linear-gradient(160deg,rgba(15,107,69,0.9),rgba(10,79,52,0.96))] p-6 text-white">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-100">
        Availability setup
      </p>
      <h2 className="font-display mt-1 text-2xl font-bold">Office hours</h2>
      <p className="mt-2 text-sm leading-6 text-emerald-50/90">
        Office-hour windows are saved to the backend so recommendation and
        action-plan logic can reference professor availability.
      </p>

      {status === "loading" ? (
        <p className="mt-6 text-sm text-emerald-50/90">Loading saved windows...</p>
      ) : null}

      {error ? (
        <div className="mt-6 rounded-2xl border border-red-300/40 bg-red-500/10 p-4 text-sm font-bold text-red-100">
          {error}
        </div>
      ) : null}

      <div className="mt-6 space-y-3">
        {windows.length === 0 && status === "success" ? (
          <p className="rounded-2xl bg-white/10 p-4 text-sm text-emerald-50/90">
            No office-hour slots saved yet. Add one below.
          </p>
        ) : null}
        {windows.map((window) => (
          <div
            key={window.id}
            className="flex items-center justify-between gap-4 rounded-2xl bg-white/10 p-4 backdrop-blur"
          >
            <div>
              <p className="font-bold">
                {window.day}, {window.start} - {window.end}
              </p>
              <p className="text-sm text-emerald-50/85">{window.location}</p>
            </div>
            <button
              type="button"
              disabled={saving}
              onClick={() => removeWindow(window.id)}
              className="rounded-full bg-white/10 px-3 py-1 text-sm font-bold text-emerald-50 hover:bg-white/20 disabled:opacity-60"
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <form onSubmit={addWindow} className="mt-6 grid gap-3 md:grid-cols-5">
        <label className="md:col-span-1">
          <span className="text-xs font-bold uppercase text-emerald-100">
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
          <span className="text-xs font-bold uppercase text-emerald-100">
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
          disabled={saving}
          className="self-end rounded-xl bg-emerald-400 px-4 py-2 font-black text-emerald-950 hover:bg-emerald-300 disabled:opacity-60"
        >
          {saving ? "Saving..." : "Add slot"}
        </button>
      </form>
    </section>
  );
}

function TimeInput({ label, value, onChange }) {
  return (
    <label>
      <span className="text-xs font-bold uppercase text-emerald-100">
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
