import { useMemo, useState } from "react";
import {
  buildRecommendationCards,
  formatDateTime,
} from "../utils/requests.js";

const CARD_STYLES = {
  group_session: {
    emoji: "🎓",
    title: "Group review session",
    gradient: "from-indigo-600 via-violet-600 to-fuchsia-500",
    chip: "bg-indigo-50 text-indigo-700 ring-indigo-200",
    button: "bg-indigo-600 hover:bg-indigo-700",
  },
  faq: {
    emoji: "📌",
    title: "FAQ response",
    gradient: "from-sky-600 via-cyan-500 to-emerald-400",
    chip: "bg-cyan-50 text-cyan-700 ring-cyan-200",
    button: "bg-cyan-600 hover:bg-cyan-700",
  },
  one_to_one: {
    emoji: "💬",
    title: "Priority 1:1",
    gradient: "from-rose-600 via-pink-500 to-orange-400",
    chip: "bg-rose-50 text-rose-700 ring-rose-200",
    button: "bg-rose-600 hover:bg-rose-700",
  },
  ta_support: {
    emoji: "🛠",
    title: "TA support block",
    gradient: "from-amber-500 via-orange-500 to-red-500",
    chip: "bg-amber-50 text-amber-800 ring-amber-200",
    button: "bg-amber-600 hover:bg-amber-700",
  },
  admin_route: {
    emoji: "🧭",
    title: "Admin route",
    gradient: "from-slate-700 via-slate-800 to-slate-950",
    chip: "bg-slate-100 text-slate-700 ring-slate-200",
    button: "bg-slate-900 hover:bg-slate-800",
  },
  manual_review: {
    emoji: "✨",
    title: "Manual review",
    gradient: "from-emerald-600 via-teal-500 to-lime-400",
    chip: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    button: "bg-emerald-600 hover:bg-emerald-700",
  },
};

const STATUS_LABELS = {
  draft: "Ready",
  approved: "Approved",
  editing: "Editing",
  dismissed: "Dismissed",
};

export default function RecommendationBoard({
  requests,
  selectedKind,
  onSelectedKindChange,
}) {
  const [cardStatuses, setCardStatuses] = useState({});
  const cards = useMemo(() => buildRecommendationCards(requests), [requests]);
  const visibleCards =
    selectedKind === "all"
      ? cards
      : cards.filter((card) => card.kind === selectedKind);
  const filters = buildFilters(cards);

  function updateStatus(cardId, status) {
    setCardStatuses((current) => ({ ...current, [cardId]: status }));
  }

  return (
    <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
      <div className="relative overflow-hidden bg-slate-950 p-6 text-white">
        <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-indigo-500/30 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 h-48 w-48 rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-indigo-200">
              Recommendation cockpit
            </p>
            <h2 className="mt-2 text-3xl font-black tracking-tight">
              Pick the next move
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
              AI groups requests into playful action cards. Approve, edit, or
              dismiss cards locally while you decide what should happen next.
            </p>
          </div>
          <div className="rounded-2xl bg-white/10 px-5 py-4 text-center">
            <p className="text-3xl font-black">{cards.length}</p>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-300">
              action cards
            </p>
          </div>
        </div>
      </div>

      <div className="border-b border-slate-200 bg-slate-50 p-4">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {filters.map((filter) => {
            const selected = selectedKind === filter.kind;
            return (
              <button
                key={filter.kind}
                type="button"
                onClick={() => onSelectedKindChange(filter.kind)}
                className={[
                  "whitespace-nowrap rounded-full px-4 py-2 text-sm font-black transition",
                  selected
                    ? "bg-slate-950 text-white shadow-sm"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100",
                ].join(" ")}
              >
                {filter.label}{" "}
                <span className={selected ? "text-white/70" : "text-slate-400"}>
                  {filter.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {visibleCards.length === 0 ? (
        <div className="p-10 text-center">
          <p className="text-lg font-bold text-slate-700">
            No recommendation cards in this lane yet.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Try another filter or submit more kiosk requests.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 p-5 xl:grid-cols-2">
          {visibleCards.map((card) => (
            <RecommendationCard
              key={card.id}
              card={card}
              status={cardStatuses[card.id] || "draft"}
              onStatusChange={(status) => updateStatus(card.id, status)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function RecommendationCard({ card, status, onStatusChange }) {
  const style = CARD_STYLES[card.kind] || CARD_STYLES.manual_review;
  const previewRequests = card.requests.slice(0, 3);

  return (
    <article className="group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-xl">
      <div className={`bg-gradient-to-br ${style.gradient} p-5 text-white`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-4xl" aria-hidden="true">
                {style.emoji}
              </span>
              <div>
                <p className="text-sm font-bold uppercase tracking-wide text-white/75">
                  {card.clusterLabel}
                </p>
                <h3 className="text-2xl font-black">{style.title}</h3>
              </div>
            </div>
            <p className="mt-4 text-sm font-medium leading-6 text-white/90">
              {card.action}
            </p>
          </div>
          <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-black text-white backdrop-blur">
            {STATUS_LABELS[status]}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="flex flex-wrap gap-2">
          <Badge className={style.chip}>{card.category}</Badge>
          <Badge className={style.chip}>
            {card.requests.length} request{card.requests.length === 1 ? "" : "s"}
          </Badge>
          <Badge className={style.chip}>
            newest {formatDateTime(card.requests[0]?.created_at)}
          </Badge>
        </div>

        <div className="space-y-3">
          {previewRequests.map((request) => (
            <div key={request.id} className="rounded-2xl bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-black uppercase text-slate-400">
                  Request #{request.id}
                </p>
                <p className="text-xs font-bold text-slate-400">
                  {request.anonymous
                    ? "Anonymous"
                    : request.student_id || "Identified"}
                </p>
              </div>
              <p className="mt-2 line-clamp-2 text-sm font-medium leading-6 text-slate-700">
                {request.text}
              </p>
            </div>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-3">
          <ActionButton
            className={`${style.button} text-white`}
            onClick={() => onStatusChange("approved")}
          >
            Approve
          </ActionButton>
          <ActionButton
            className="bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            onClick={() => onStatusChange("editing")}
          >
            Edit
          </ActionButton>
          <ActionButton
            className="bg-white text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50"
            onClick={() => onStatusChange("dismissed")}
          >
            Dismiss
          </ActionButton>
        </div>

        {status === "editing" ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4">
            <label className="text-xs font-black uppercase tracking-wide text-slate-500">
              Draft professor note
            </label>
            <textarea
              rows={3}
              defaultValue={card.action}
              className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:border-indigo-400"
            />
          </div>
        ) : null}
      </div>
    </article>
  );
}

function buildFilters(cards) {
  const counts = cards.reduce(
    (current, card) => ({
      ...current,
      [card.kind]: (current[card.kind] || 0) + 1,
    }),
    {},
  );

  return [
    { kind: "all", label: "All", count: cards.length },
    ...Object.entries(CARD_STYLES).map(([kind, style]) => ({
      kind,
      label: style.title,
      count: counts[kind] || 0,
    })),
  ];
}

function Badge({ children, className }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-black ring-1 ${className}`}>
      {children}
    </span>
  );
}

function ActionButton({ children, className, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl px-4 py-3 text-sm font-black transition active:scale-[0.98] ${className}`}
    >
      {children}
    </button>
  );
}
