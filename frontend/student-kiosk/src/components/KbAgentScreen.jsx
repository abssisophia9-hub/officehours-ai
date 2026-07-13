import { useState } from "react";
import { askKbAgent } from "../api/agent.js";

export default function KbAgentScreen({ onBack }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Ask a course question. I only answer from professor-approved knowledge — drafts waiting for review stay hidden.",
    },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || busy) {
      return;
    }

    setBusy(true);
    setError("");
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setQuestion("");

    try {
      const result = await askKbAgent(trimmed);
      const sourceNote =
        result.matched_count > 0
          ? `\n\nMatched ${result.matched_count} approved entr${
              result.matched_count === 1 ? "y" : "ies"
            } (${Math.round(result.confidence * 100)}% confidence).`
          : "";
      const hint = result.student_hint
        ? `\n\nHint while you wait: ${result.student_hint}`
        : "";
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: `${result.answer}${sourceNote}${hint}`,
        },
      ]);
    } catch (askError) {
      setError(askError.message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: "I could not reach the knowledge agent. Try again in a moment, or submit a help request instead.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass-panel w-full max-w-3xl animate-fade-in-up p-6 sm:p-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="glass-chip mb-3">
            Course knowledge agent
          </p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">
            Ask approved answers
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Built from past office-hours questions the professor has curated.
            Nothing pending review is shown here.
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="btn-ghost px-4 py-2 text-sm"
        >
          Back
        </button>
      </div>

      <div className="mb-4 max-h-[22rem] space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-4">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`rounded-2xl px-4 py-3 text-sm leading-6 whitespace-pre-wrap ${
              message.role === "user"
                ? "ml-8 bg-aui-forest text-white"
                : "mr-8 bg-white text-slate-800 ring-1 ring-slate-200"
            }`}
          >
            {message.text}
          </div>
        ))}
      </div>

      {error ? (
        <p className="mb-3 text-sm font-medium text-red-600">{error}</p>
      ) : null}

      <form onSubmit={handleAsk} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="e.g. How do I think about recursion base cases?"
          className="field-glass flex-1 px-4 py-3 text-base font-medium text-slate-900"
        />
        <button
          type="submit"
          disabled={busy || question.trim().length < 3}
          className="btn-primary px-6 py-3 text-base disabled:opacity-60"
        >
          {busy ? "Thinking..." : "Ask"}
        </button>
      </form>
    </section>
  );
}
