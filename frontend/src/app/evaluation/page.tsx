"use client";

import { useEffect, useState } from "react";
import { StrategyBadge } from "@/components/Explanation";
import { ErrorBox, Loading, PageHeader, StarMark, StatusPill } from "@/components/ui";
import { api, Evaluation, GapStatus, pct } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const KEY = ["meaning_gap_detection_accuracy", "citation_correctness", "unsupported_claim_rate", "abstention_accuracy"];
const OTHERS = [
  "gap_type_accuracy",
  "intended_concept_extraction",
  "background_leakage_rate",
  "topic_gate_accuracy",
  "rag_relevance_precision",
  "irrelevant_retrieval_rejection",
  "refinement_strategy_fit",
  "refinement_relevance",
  "before_after_resolution_rate",
  "agent_first_pass_rate",
  "agent_final_pass_rate",
];
const LOWER_BETTER = new Set(["unsupported_claim_rate", "background_leakage_rate"]);

const percent = (v: number | null | undefined) => (v == null ? "—" : `${Number.isInteger(v) ? v : v.toFixed(1)}%`);

export default function EvaluationPage() {
  const { t } = useI18n();
  const e = t.evaluation;
  const [data, setData] = useState<Evaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .evaluation()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  const m = data.metrics;
  const date = data.generated_at ? new Date(data.generated_at).toLocaleDateString("ar", { dateStyle: "long" }) : "—";

  return (
    <div className="space-y-10">
      <PageHeader title={e.title} subtitle={e.subtitle} />
      <p className="-mt-6 flex flex-wrap gap-x-6 gap-y-1 text-sm text-navy-500">
        <span>
          {e.runInfo}: {date}
        </span>
        <span>
          <bdi className="font-latin">{m.n_cases}</bdi> {e.cases}
        </span>
      </p>

      <section>
        <h2 className="mb-4 text-xl font-bold text-navy-900">{e.key}</h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {KEY.map((k) => (
            <div key={k} className="card !p-6 text-center">
              <p className="font-latin text-4xl font-bold text-emerald-700" dir="ltr">
                {percent(m[k])}
              </p>
              <p className="mt-3 text-sm font-semibold leading-snug text-navy-700">{t.metrics[k]}</p>
              {LOWER_BETTER.has(k) && <p className="mt-1 text-xs text-navy-400">{e.lowerBetter}</p>}
            </div>
          ))}
        </div>
      </section>

      <section className="pattern-gold rounded-[2rem] bg-navy-900 px-6 py-10 text-center text-sand-50 shadow-lift sm:px-12">
        <h2 className="text-2xl font-bold">{e.impact}</h2>
        <p className="mt-2 text-navy-300">{e.impactHelp}</p>
        <div className="mt-8 grid items-center gap-6 sm:grid-cols-[1fr_auto_1fr]">
          <div>
            <p className="font-latin text-6xl font-bold text-navy-300">{pct(m.mean_before_alignment)}</p>
            <p className="mt-2 text-sm text-navy-300">{e.before}</p>
          </div>
          <div>
            <p className="font-latin text-4xl font-bold text-emerald-500" dir="ltr">
              +{m.mean_improvement_points ?? 0}
            </p>
            <p className="text-xs text-navy-300">{e.points}</p>
          </div>
          <div>
            <p className="font-latin text-6xl font-bold text-emerald-500">{pct(m.mean_after_alignment)}</p>
            <p className="mt-2 text-sm text-navy-300">{e.after}</p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold text-navy-900">{e.all}</h2>
        <div className="card !p-0">
          <ul className="divide-y divide-sand-200">
            {OTHERS.map((k) => (
              <li key={k} className="flex items-center justify-between gap-4 px-6 py-3.5">
                <span className="text-navy-700">
                  {t.metrics[k]}
                  {LOWER_BETTER.has(k) && <span className="ms-2 text-xs text-navy-400">({e.lowerBetter})</span>}
                </span>
                <span className="font-latin font-semibold text-navy-900" dir="ltr">
                  {percent(m[k])}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold text-navy-900">{e.categories}</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(data.categories).map(([k, v]) => (
            <div key={k} className="card flex items-center justify-between gap-3 !p-5">
              <div>
                <p className="font-semibold text-navy-800">{t.categories[k] ?? k}</p>
                <p className="text-xs text-navy-400">
                  <bdi className="font-latin">{v.n}</bdi> {e.cases}
                </p>
              </div>
              <span className="font-latin text-xl font-bold text-emerald-700" dir="ltr">
                {percent(v.status_accuracy)}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold text-navy-900">{e.caseList}</h2>
        <ul className="space-y-3">
          {data.cases.map((c) => (
            <li key={c.id} className={`card !p-5 ${c.status_ok ? "" : "border-amber-100 bg-amber-50/40"}`}>
              <div className="flex flex-wrap items-center gap-2">
                <StarMark size={14} className="text-gold-500" />
                <span className="text-sm font-semibold text-navy-700">{t.categories[c.category] ?? c.category}</span>
                <span className={`chip ms-auto ${c.status_ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-100 bg-amber-50 text-amber-700"}`}>
                  {c.status_ok ? `✓ ${e.matched}` : `✕ ${e.missed}`}
                </span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs text-navy-400">{e.content}</p>
                  <p className="text-navy-900" dir="auto">
                    {c.content}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-navy-400">{e.answer}</p>
                  <p className="text-navy-700" dir="auto">
                    {c.user_response}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-navy-500">
                <span>
                  {e.expected}: {c.expected_status.map((s) => t.status[s] ?? s).join(e.or)}
                </span>
                <span className="flex items-center gap-2">
                  {e.actual}: {c.status ? <StatusPill status={c.status as GapStatus} /> : "—"}
                </span>
                {c.strategy && (
                  <span className="flex items-center gap-2">
                    {e.strategy}: <StrategyBadge strategy={c.strategy} />
                  </span>
                )}
                {c.before != null && c.after != null && (
                  <span className="font-latin" dir="ltr">
                    {pct(c.before)} → {pct(c.after)}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
