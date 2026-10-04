"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import AgentPipeline from "@/components/AgentPipeline";
import { StrategyBadge } from "@/components/Explanation";
import { GapTypePill, Loading, PageHeader, StarMark } from "@/components/ui";
import { SessionView } from "@/lib/api";
import { useSession } from "@/lib/hooks";
import { topicName, useI18n } from "@/lib/i18n";

const GAP_TYPES = [
  "correct_understanding",
  "missing_intended_meaning",
  "distorted_meaning",
  "concept_confusion",
  "ambiguity_triggered",
  "insufficient_evidence",
];

const STRATEGY_CAUSES: Record<string, string[]> = {
  comparison: ["concept_confusion", "ambiguous_wording", "overgeneralization"],
  simplification: ["ambiguous_wording", "abstract_concept", "missing_context", "overgeneralization"],
  example: ["ambiguous_wording", "abstract_concept", "missing_context", "overgeneralization"],
  visual: ["abstract_concept", "complex_process"],
  step_by_step: ["missing_context", "complex_process"],
};

const AGENT_NAMES: Record<string, string> = {
  meaning_agent: "وكيل المعنى",
  understanding_agent: "وكيل الفهم",
  verification_agent: "وكيل التحقق",
  refinement_agent: "وكيل الشرح التكيّفي",
};

function TechnologyView() {
  const id = useSearchParams().get("id");
  const { t } = useI18n();
  const x = t.tech;
  const { session } = useSession(id);

  return (
    <div className="space-y-10">
      <PageHeader title={x.title} subtitle={x.subtitle} />

      <section className="grid gap-4 md:grid-cols-2">
        {x.pillars.map((p) => (
          <div key={p.tag} className="card">
            <span className="chip border-gold-100 bg-gold-50 font-latin text-gold-700">{p.tag}</span>
            <h2 className="mt-4 text-lg font-bold text-navy-900">{p.t}</h2>
            <p className="mt-2 leading-relaxed text-navy-600">{p.d}</p>
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-5 text-2xl font-bold text-navy-900">{x.agentsTitle}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {x.agents.map((a) => (
            <div key={a.n} className="card !p-6">
              <StarMark size={22} className="text-emerald-600" />
              <h3 className="mt-3 text-lg font-bold text-navy-900">{a.t}</h3>
              <p className="font-latin text-xs text-emerald-700" dir="ltr">
                {a.n}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-navy-500">{a.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <div className="card">
          <h2 className="mb-5 text-xl font-bold text-navy-900">{id ? x.sessionTrace : x.workflowTitle}</h2>
          {id && !session ? <Loading /> : <AgentPipeline session={session} />}
        </div>
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-navy-900">{x.scoreTitle}</h2>
            <p className="mt-3 leading-relaxed text-navy-600">{x.scoreText}</p>
          </div>
          <div className="card">
            <h2 className="mb-4 text-xl font-bold text-navy-900">{x.gapTypesTitle}</h2>
            <div className="flex flex-wrap gap-2">
              {GAP_TYPES.map((g) => (
                <GapTypePill key={g} type={g} />
              ))}
            </div>
          </div>
          <div className="card">
            <h2 className="mb-4 text-xl font-bold text-navy-900">{x.strategiesTitle}</h2>
            <ul className="space-y-3">
              {Object.entries(STRATEGY_CAUSES).map(([s, causes]) => (
                <li key={s} className="flex flex-col gap-1">
                  <StrategyBadge strategy={s} />
                  <span className="text-sm text-navy-500">{causes.map((c) => t.causes[c]).join("، ")}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {session && <SessionDetails session={session} />}

      <section className="card">
        <h2 className="mb-4 text-xl font-bold text-navy-900">{x.reliabilityTitle}</h2>
        <ul className="space-y-3">
          {x.reliability.map((r) => (
            <li key={r} className="flex gap-3 text-navy-700">
              <StarMark size={14} className="mt-1.5 shrink-0 text-gold-500" />
              {r}
            </li>
          ))}
        </ul>
        <Link href="/sources/" className="btn-ghost mt-6">
          {t.about.sourcesCta}
        </Link>
      </section>
    </div>
  );
}

function SessionDetails({ session }: { session: SessionView }) {
  const { t } = useI18n();
  const x = t.tech;
  const m = session.meaning_analysis;
  const decisions = session.rag_decisions ?? [];
  const log = session.validation_log ?? [];
  return (
    <section className="card space-y-8">
      <div>
        <p className="label mb-2">{x.retrieval}</p>
        <p className="text-sm text-navy-600">
          <span className="font-semibold">{x.primaryTopic}:</span> {topicName(session.rag_primary_topic)}
        </p>
        <p className="mt-2 text-sm font-semibold text-navy-600">{x.queries}:</p>
        <ul className="ms-5 list-disc text-sm text-navy-500">
          {(session.rag_queries ?? []).map((q) => (
            <li key={q} dir="auto">
              {q}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p className="label mb-2">{x.decisions}</p>
        {decisions.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-start text-sm">
              <thead>
                <tr className="text-xs text-navy-400">
                  <th className="py-2 pe-3 text-start font-medium">المصدر</th>
                  <th className="py-2 pe-3 text-start font-medium">الموضوع</th>
                  <th className="py-2 pe-3 text-start font-medium">{x.score}</th>
                  <th className="py-2 text-start font-medium">{x.decision}</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d.doc_id + d.score} className="border-t border-sand-200 align-top">
                    <td className="py-2 pe-3 font-latin text-navy-700" dir="ltr">
                      {d.reference}
                    </td>
                    <td className="py-2 pe-3 text-navy-500">{topicName(d.topic)}</td>
                    <td className="py-2 pe-3 font-latin text-navy-500">{d.score.toFixed(3)}</td>
                    <td className={`py-2 ${d.decision === "kept" ? "font-semibold text-emerald-700" : "text-navy-500"}`}>
                      {t.decisions[d.decision] ?? d.decision}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-navy-400">{x.none}</p>
        )}
      </div>

      {m && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card-quiet">
            <p className="mb-2 text-sm font-semibold text-emerald-700">{x.intendedScored}</p>
            <ul className="space-y-1 text-sm text-navy-700">
              {m.intended_concepts.map((c) => (
                <li key={c.id}>
                  <span className="font-latin">{c.id}</span> · {c.concept} ·{" "}
                  <span className="font-latin">{Math.round(c.weight * 100)}%</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card-quiet">
            <p className="mb-2 text-sm font-semibold text-navy-500">{x.backgroundNotScored}</p>
            <ul className="space-y-1 text-sm text-navy-500">
              {m.background_knowledge.length ? m.background_knowledge.map((b, i) => <li key={i}>{b.concept}</li>) : <li>{x.none}</li>}
            </ul>
          </div>
        </div>
      )}

      {session.verification?.concept_results && session.verification.concept_results.length > 0 && (
        <div>
          <p className="label mb-2">{x.verdicts}</p>
          <ul className="space-y-2 text-sm text-navy-700">
            {session.verification.concept_results.map((c) => (
              <li key={c.concept_id} className="flex flex-wrap items-center gap-2">
                <span className="font-latin">{c.concept_id}</span>
                <GapTypePill type={c.gap_type} />
                <span>{c.concept}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {log.length > 0 && (
        <div>
          <p className="label mb-2">{x.validation}</p>
          <ul className="space-y-2">
            {log.map((e, i) => (
              <li key={i} className="rounded-2xl border border-sand-200 bg-sand-50/60 px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-navy-800">{AGENT_NAMES[e.agent] ?? e.agent}</span>
                  {e.stage === "retest" && <span className="chip border-sand-300 text-navy-500">{t.result.retest}</span>}
                  <span className="text-navy-500">
                    {x.attempts}: <span className="font-latin">{e.attempts}</span>
                  </span>
                  <span className={`chip ${e.issues_first.length ? "border-amber-100 bg-amber-50 text-amber-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
                    {e.issues_first.length ? x.corrected : x.firstPass}
                  </span>
                </div>
                {[...e.issues_first, ...e.corrections].length > 0 && (
                  <ul className="mt-2 space-y-1 font-latin text-xs text-navy-500" dir="ltr">
                    {[...e.issues_first, ...e.corrections].map((issue, j) => (
                      <li key={j}>• {issue}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export default function TechnologyPage() {
  return (
    <Suspense fallback={<Loading />}>
      <TechnologyView />
    </Suspense>
  );
}
