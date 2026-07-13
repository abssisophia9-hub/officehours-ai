import { useEffect, useMemo, useState } from "react";
import {
  fetchRecommendationDecisions,
  getCalendarExportUrl,
  saveRecommendationDecision,
} from "../api/actions.js";
import {
  buildRecommendationCards,
  formatDateTime,
} from "../utils/requests.js";

const CARD_STYLES = {
  group_session: {
    emoji: "🎓",
    title: "Group review session",
    gradient: "from-[var(--aui-forest)] via-[#147a52] to-[#0a4f34]",
    chip: "bg-emerald-50 text-[var(--aui-forest-deep)] ring-emerald-200",
    button: "bg-[var(--aui-forest)] hover:brightness-110",
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
  const [actionPlans, setActionPlans] = useState({});
  const [decisionIds, setDecisionIds] = useState({});
  const [savingCardId, setSavingCardId] = useState("");
  const [errorByCardId, setErrorByCardId] = useState({});
  const cards = useMemo(() => buildRecommendationCards(requests), [requests]);
  const visibleCards =
    selectedKind === "all"
      ? cards
      : cards.filter((card) => card.kind === selectedKind);
  const filters = buildFilters(cards);

  useEffect(() => {
    let cancelled = false;

    fetchRecommendationDecisions()
      .then((decisions) => {
        if (cancelled || !Array.isArray(decisions)) {
          return;
        }

        // Prefer the latest decision per card_id.
        const latestByCard = new Map();
        for (const decision of decisions) {
          latestByCard.set(decision.card_id, decision);
        }

        const nextStatuses = {};
        const nextPlans = {};
        const nextIds = {};
        for (const [cardId, decision] of latestByCard.entries()) {
          nextStatuses[cardId] = decision.status;
          nextPlans[cardId] = decision.action_plan;
          nextIds[cardId] = decision.id;
        }
        setCardStatuses(nextStatuses);
        setActionPlans(nextPlans);
        setDecisionIds(nextIds);
      })
      .catch(() => {
        // Keep local empty state if the backend is unreachable.
      });

    return () => {
      cancelled = true;
    };
  }, [requests]);

  async function updateStatus(card, status) {
    setSavingCardId(card.id);
    setErrorByCardId((current) => ({ ...current, [card.id]: "" }));

    try {
      const decision = await saveRecommendationDecision({ card, status });
      setCardStatuses((current) => ({ ...current, [card.id]: status }));
      setActionPlans((current) => ({
        ...current,
        [card.id]: decision.action_plan,
      }));
      setDecisionIds((current) => ({
        ...current,
        [card.id]: decision.id,
      }));
    } catch (error) {
      setErrorByCardId((current) => ({
        ...current,
        [card.id]:
          "Could not save this decision. Keep discussing it, then try again.",
      }));
    } finally {
      setSavingCardId("");
    }
  }

  return (
    <section className="glass-panel overflow-hidden">
      <div className="relative overflow-hidden bg-slate-950 p-6 text-white">
        <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-emerald-500/25 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 h-48 w-48 rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-100">
              Recommendation cockpit
            </p>
            <h2 className="mt-2 text-3xl font-black tracking-tight">
              Pick the next move
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
              AI groups requests into playful action cards. Approve, edit, or
              dismiss cards to generate agenda, status, and notification plans.
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
              actionPlan={actionPlans[card.id]}
              decisionId={decisionIds[card.id]}
              error={errorByCardId[card.id]}
              saving={savingCardId === card.id}
              onStatusChange={(status) => updateStatus(card, status)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function RecommendationCard({
  card,
  status,
  actionPlan,
  decisionId,
  error,
  saving,
  onStatusChange,
}) {
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
            {saving ? "Saving..." : STATUS_LABELS[status]}
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
            disabled={saving}
            onClick={() => onStatusChange("approved")}
          >
            Approve
          </ActionButton>
          <ActionButton
            className="bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            disabled={saving}
            onClick={() => onStatusChange("editing")}
          >
            Edit
          </ActionButton>
          <ActionButton
            className="bg-white text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50"
            disabled={saving}
            onClick={() => onStatusChange("dismissed")}
          >
            Dismiss
          </ActionButton>
        </div>

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-700">
            {error}
          </div>
        ) : null}

        {actionPlan ? (
          <ActionPlanPreview actionPlan={actionPlan} decisionId={decisionId} />
        ) : null}

        {status === "editing" ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4">
            <label className="text-xs font-black uppercase tracking-wide text-slate-500">
              Draft professor note
            </label>
            <textarea
              rows={3}
              defaultValue={card.action}
              className="field-glass mt-2 w-full resize-none p-3 text-sm"
            />
          </div>
        ) : null}
      </div>
    </article>
  );
}

function ActionPlanPreview({ actionPlan, decisionId }) {
  const calendarReady = actionPlan.calendar?.ics_ready && decisionId;

  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <p className="text-xs font-black uppercase tracking-wide text-emerald-700">
        Next step generated
      </p>
      <p className="mt-1 font-black text-emerald-950">{actionPlan.title}</p>
      <p className="mt-2 text-sm leading-6 text-emerald-800">
        {actionPlan.student_update}
      </p>
      {actionPlan.agenda_item ? (
        <p className="mt-2 rounded-xl bg-white/70 p-3 text-sm font-bold text-emerald-900">
          Agenda: {actionPlan.agenda_item.suggested_window} ·{" "}
          {actionPlan.agenda_item.format}
        </p>
      ) : null}
      {calendarReady ? (
        <a
          href={getCalendarExportUrl(decisionId)}
          className="mt-3 inline-flex rounded-xl bg-emerald-700 px-4 py-2 text-sm font-black text-white hover:bg-emerald-800"
        >
          Download calendar (.ics)
        </a>
      ) : null}
    </div>
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

function ActionButton({ children, className, disabled = false, onClick }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-xl px-4 py-3 text-sm font-black transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
