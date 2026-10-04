"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import ExplanationView from "@/components/Explanation";
import JourneySteps from "@/components/JourneySteps";
import MeaningFlow from "@/components/MeaningFlow";
import {
  ErrorBox,
  EvidenceList,
  GapTypePill,
  Loading,
  MissingSession,
  PageHeader,
  Quote,
  ResolutionPill,
  ScoreRing,
  Section,
  StarMark,
  StatusPill,
} from "@/components/ui";
import { api, ConceptResult, DemoScenario, Resolution, SessionView } from "@/lib/api";
import { useAgentRun, useSession } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";

function ResultView() {
  const id = useSearchParams().get("id");
  const router = useRouter();
  const { t } = useI18n();
  const { session, setSession, error } = useSession(id);
  const { run, running, progress, error: runError } = useAgentRun();
  const [answer, setAnswer] = useState("");
  const [sample, setSample] = useState<DemoScenario | null>(null);

  useEffect(() => {
    if (session?.stage === "awaiting_response") router.replace(`/test/?id=${id}`);
    if (!session) return;
    api
      .demo()
      .then((d) => setSample(d.scenarios.find((s) => s.content === session.original_content) ?? null))
      .catch(() => setSample(null));
  }, [session, id, router]);

  if (!id) return <MissingSession />;
  if (error) return <ErrorBox message={error} />;
  if (!session || session.stage === "awaiting_response") return <Loading />;
  if (session.stage === "abstained") return <Abstained session={session} />;

  const v = session.verification;
  const m = session.meaning_analysis;
  if (!v || !m) return <ErrorBox message={t.common.noSession} />;

  const misunderstandings = v.misunderstandings ?? [];
  const missing = v.missing ?? [];
  const hasGap = v.status !== "understood";
  const byId = new Map<string, ConceptResult>((v.concept_results ?? []).map((c) => [c.concept_id, c]));
  const supported = misunderstandings.filter((x) => x.source_reference);

  async function refine() {
    const res = await run(id!, () => api.refine(id!));
    if (res) setSession(res);
  }
  async function retest() {
    const res = await run(id!, () => api.retest(id!, answer));
    if (res) setSession(res);
  }

  let n = 0;
  const next = () => ++n;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader eyebrow={t.result.title} title={t.status[session.second_verification?.status ?? v.status]} />
      <MeaningFlow session={session} />

      <Section n={next()} title={t.result.overall}>
        <div className="grid items-center gap-8 md:grid-cols-[auto_1fr]">
          <ScoreRing value={v.alignment_score} label={t.result.clarity} tone={hasGap ? "gold" : "emerald"} />
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <StatusPill status={v.status} />
              {hasGap && v.primary_gap_type !== "correct_understanding" && <GapTypePill type={v.primary_gap_type} />}
            </div>
            {hasGap && <p className="font-semibold text-navy-800">{t.result.gapDetected}</p>}
            {v.gap_explanation && <p className="text-lg leading-relaxed text-navy-700">{v.gap_explanation}</p>}
            <p className="text-xs leading-relaxed text-navy-400">{t.result.clarityHelp}</p>
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Quote label={t.common.yourContent}>{session.original_content}</Quote>
          <Quote label={t.common.readerAnswer}>{session.user_response}</Quote>
        </div>

        <div className="mt-8">
          <p className="label">{t.result.intended}</p>
          <p className="mb-3 text-sm text-navy-400">{t.result.intendedHelp}</p>
          <ul className="space-y-2">
            {m.intended_concepts.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl border border-sand-200 bg-white px-4 py-3">
                <ConceptIcon gap={byId.get(c.id)?.gap_type} />
                <span className="font-semibold text-navy-900">{c.concept}</span>
                <span className="text-sm text-navy-400">
                  {t.result.fromContent}: «<bdi>{c.evidence_from_original_content}</bdi>»
                </span>
                <span className="ms-auto text-xs text-navy-400">
                  {t.result.weight} <bdi className="font-latin">{Math.round(c.weight * 100)}%</bdi>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section n={next()} title={t.result.arrived} tone={hasGap ? "default" : "highlight"}>
        {v.what_arrived?.length ? (
          <ul className="space-y-2">
            {v.what_arrived.map((x) => (
              <li key={x} className="flex gap-3 text-lg text-navy-800">
                <span className="text-emerald-600" aria-hidden>
                  ✓
                </span>
                {x}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-navy-500">{t.result.arrivedNone}</p>
        )}
        {!hasGap && <p className="mt-5 text-emerald-700">{t.result.understoodFirst}</p>}
      </Section>

      {hasGap && (
        <Section n={next()} title={t.result.gapWhere}>
          <div className="space-y-3">
            {misunderstandings.map((x, i) => (
              <div key={i} className="rounded-2xl border border-clay-100 bg-clay-50/50 p-5">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="text-clay-600" aria-hidden>
                    ⚠
                  </span>
                  <GapTypePill type={x.gap_type} />
                  {x.confused_with && (
                    <span className="text-sm text-navy-500">
                      {t.result.confusedWith}: <strong className="text-navy-800">{x.confused_with}</strong>
                    </span>
                  )}
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold text-clay-600">{t.result.readerUnderstood}</p>
                    <p className="mt-1 text-navy-800">{x.user_understood}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-emerald-700">{t.result.accurate}</p>
                    <p className="mt-1 text-navy-800">{x.accurate_meaning}</p>
                  </div>
                </div>
              </div>
            ))}
            {missing.map((c) => (
              <div key={c} className="flex items-start gap-3 rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
                <span className="text-amber-600" aria-hidden>
                  ○
                </span>
                <div>
                  <p className="text-xs font-semibold text-amber-700">{t.result.notArrived}</p>
                  <p className="text-navy-800">{c}</p>
                </div>
              </div>
            ))}
            {!misunderstandings.length && !missing.length && <p className="text-navy-500">{t.result.gapNone}</p>}
          </div>
        </Section>
      )}

      {hasGap && (misunderstandings.length > 0 || m.potential_ambiguities.length > 0) && (
        <Section n={next()} title={t.result.why}>
          <div className="space-y-3">
            {misunderstandings.map((x, i) => (
              <p key={i} className="text-lg leading-relaxed text-navy-700">
                {x.why_it_happened}
              </p>
            ))}
            {m.potential_ambiguities.length > 0 && (
              <div className="card-quiet mt-4">
                <p className="mb-3 text-sm font-semibold text-gold-700">{t.result.wordingRisk}</p>
                <ul className="space-y-2">
                  {m.potential_ambiguities.map((a, i) => (
                    <li key={i} className="text-navy-700">
                      <span className="font-semibold text-navy-900">
                        «<bdi>{a.phrase}</bdi>»
                      </span>{" "}
                      {t.result.mayLead} {a.possible_misunderstanding}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Section>
      )}

      <Section n={next()} title={t.result.verify} help={t.result.verifyHelp}>
        {supported.length > 0 && (
          <ul className="mb-5 space-y-2">
            {supported.map((x, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-2 text-navy-700">
                <StarMark size={12} className="text-gold-500" />
                <span>{x.accurate_meaning}</span>
              </li>
            ))}
          </ul>
        )}
        {(v.evidence ?? []).length ? <EvidenceList items={v.evidence} /> : <p className="text-sm text-navy-400">{t.result.noEvidenceCited}</p>}
        {(v.rejected_claims ?? []).length > 0 && (
          <div className="mt-5 rounded-2xl border border-dashed border-amber-100 bg-amber-50/40 p-4">
            <p className="text-sm font-semibold text-amber-700">{t.result.rejected}</p>
            <ul className="mt-2 space-y-1 text-sm text-navy-600">
              {v.rejected_claims.map((c, i) => (
                <li key={i}>• {c.claim}</li>
              ))}
            </ul>
          </div>
        )}
        {m.background_knowledge.length > 0 && (
          <details className="mt-5 rounded-2xl border border-dashed border-sand-300 p-4">
            <summary className="flex items-center justify-between gap-3">
              <span className="font-semibold text-navy-700">{t.result.background}</span>
              <span className="text-xs text-navy-400">{m.background_knowledge.length}</span>
            </summary>
            <p className="mt-2 text-sm text-navy-400">{t.result.backgroundHelp}</p>
            <ul className="mt-3 space-y-2">
              {m.background_knowledge.map((b, i) => (
                <li key={i} className="text-sm text-navy-600">
                  • {b.concept}
                </li>
              ))}
            </ul>
          </details>
        )}
      </Section>

      {hasGap && (
        <Section n={next()} title={t.result.explain} help={t.result.explainHelp} tone={session.refinement ? "highlight" : "default"}>
          {session.refinement ? (
            <ExplanationView refinement={session.refinement} original={session.original_content} />
          ) : (
            <>
              <ErrorBox message={runError} />
              <button className="btn-accent mt-2 w-full py-4" disabled={running} onClick={refine}>
                {running ? t.result.explaining : t.result.explainCta}
              </button>
              <div className="mt-4">
                <JourneySteps progress={progress} running={running} />
              </div>
            </>
          )}
        </Section>
      )}

      {hasGap && session.refinement && (
        <Section n={next()} title={session.stage === "awaiting_retest" ? t.result.retest : t.result.improvement}>
          {session.stage === "awaiting_retest" ? (
            <div className="space-y-4">
              <p className="text-sm text-navy-500">{t.result.retestHelp}</p>
              <p className="text-xl font-semibold text-navy-900" dir="auto">
                {session.follow_up_question}
              </p>
              <textarea
                dir="auto"
                className="input min-h-[140px] text-lg"
                placeholder={t.test.placeholder}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                aria-label={t.result.retest}
              />
              {sample?.retest_response && (
                <button className="btn-link" onClick={() => setAnswer(sample.retest_response)}>
                  {t.result.sampleRetest}
                </button>
              )}
              <ErrorBox message={runError} />
              <button className="btn-primary w-full py-4" disabled={running || answer.trim().length < 2} onClick={retest}>
                {running ? t.result.retesting : t.result.retestCta}
              </button>
              <JourneySteps progress={progress} running={running} />
            </div>
          ) : (
            <Comparison session={session} />
          )}
        </Section>
      )}

      <div className="flex flex-wrap items-center gap-3 pt-4">
        <Link href="/analyze/" className="btn-primary">
          {t.result.newTest}
        </Link>
        <Link href={`/technology/?id=${id}`} className="btn-link ms-auto">
          {t.result.techTrace}
        </Link>
      </div>
    </div>
  );
}

function ConceptIcon({ gap }: { gap?: string }) {
  if (gap === "correct_understanding") return <span className="text-emerald-600">✓</span>;
  if (gap === "missing_intended_meaning") return <span className="text-amber-600">○</span>;
  if (gap) return <span className="text-clay-600">⚠</span>;
  return <span className="text-navy-300">·</span>;
}

function Comparison({ session }: { session: SessionView }) {
  const { t } = useI18n();
  const f = session.final_result;
  if (!f) return null;
  const before = f.before_score ?? 0;
  const after = f.after_score ?? before;
  const delta = f.improvement_points ?? 0;
  const items: { text: string; status: Resolution }[] = [
    ...(f.resolved_gaps ?? []).map((text) => ({ text, status: "resolved" as const })),
    ...(f.partially_resolved_gaps ?? []).map((text) => ({ text, status: "partially_resolved" as const })),
    ...(f.remaining_gaps ?? []).map((text) => ({ text, status: "remains" as const })),
  ];

  return (
    <div className="space-y-6">
      {f.resolution && (
        <div className="text-center">
          <ResolutionPill status={f.resolution} large />
        </div>
      )}
      <div className="grid items-center gap-6 sm:grid-cols-[1fr_auto_1fr]">
        <div className="flex flex-col items-center gap-2">
          <ScoreRing value={before} label={t.result.before} tone="muted" size={140} />
        </div>
        <div className="text-center">
          <p className={`font-latin text-4xl font-bold ${delta > 0 ? "text-emerald-600" : "text-navy-400"}`} dir="ltr">
            {delta > 0 ? "+" : ""}
            {delta}
          </p>
          <p className="text-xs text-navy-400">{t.result.points}</p>
        </div>
        <div className="flex flex-col items-center gap-2">
          <ScoreRing value={after} label={t.result.after} tone="emerald" size={140} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Quote label={t.result.beforeUnderstanding}>{session.user_response}</Quote>
        <Quote label={t.result.afterUnderstanding}>{session.follow_up_response}</Quote>
      </div>

      {items.length > 0 && (
        <ul className="space-y-2">
          {items.map((x, i) => (
            <li key={i} className="flex flex-wrap items-center gap-3 rounded-2xl border border-sand-200 bg-white px-4 py-3">
              <ResolutionPill status={x.status} />
              <span className="text-navy-700">{x.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Abstained({ session }: { session: SessionView }) {
  const { t } = useI18n();
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader eyebrow={t.result.title} title={t.result.abstainTitle} />
      <MeaningFlow session={session} />
      <div className="card">
        <StatusPill status="insufficient_evidence" />
        <div className="mt-5">
          <Quote label={t.common.yourContent}>{session.original_content}</Quote>
        </div>
        <p className="mt-6 text-lg font-semibold text-navy-800">{session.abstention?.message}</p>
        {session.abstention?.reason && <p className="mt-2 leading-relaxed text-navy-600">{session.abstention.reason}</p>}
        <p className="mt-4 leading-relaxed text-navy-600">{t.result.abstainText}</p>
        <p className="mt-3 text-sm text-navy-400">{t.result.abstainHint}</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/analyze/" className="btn-primary">
          {t.result.newTest}
        </Link>
        <Link href={`/technology/?id=${session.session_id}`} className="btn-link ms-auto">
          {t.result.techTrace}
        </Link>
      </div>
    </div>
  );
}

export default function ResultPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ResultView />
    </Suspense>
  );
}
