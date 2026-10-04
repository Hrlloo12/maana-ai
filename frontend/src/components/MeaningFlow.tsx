"use client";

import { SessionView } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type StepState = "done" | "current" | "skipped" | "pending" | "stopped";

function flowStates(s: SessionView): StepState[] {
  const v = s.verification;
  const understood = v?.status === "understood";
  const abstained = s.stage === "abstained";
  const done = [
    true,
    Boolean(s.meaning_analysis),
    Boolean(s.user_response),
    Boolean(v),
    Boolean(v),
    Boolean(s.refinement),
    Boolean(s.refinement),
    Boolean(s.refinement),
    Boolean(s.second_verification),
    Boolean(s.second_verification && s.final_result),
  ];
  const skipped = done.map((_, i) => understood && i >= 5);
  const firstOpen = done.findIndex((d, i) => !d && !skipped[i]);
  return done.map((d, i) => {
    if (d) return "done";
    if (skipped[i]) return "skipped";
    if (abstained) return "stopped";
    return i === firstOpen ? "current" : "pending";
  });
}

const DOT: Record<StepState, string> = {
  done: "border-emerald-500 bg-emerald-600 text-white",
  current: "border-emerald-500 bg-white text-emerald-700 animate-breathe",
  skipped: "border-sand-300 bg-sand-50 text-navy-300",
  pending: "border-sand-300 bg-white text-navy-400",
  stopped: "border-clay-100 bg-clay-50 text-clay-500",
};

export default function MeaningFlow({ session }: { session: SessionView }) {
  const { t } = useI18n();
  const states = flowStates(session);
  return (
    <section className="card !p-5 sm:!p-6" aria-label={t.flow.title}>
      <p className="label mb-4">{t.flow.title}</p>
      <ol className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-5">
        {t.flow.steps.map((label, i) => {
          const st = states[i];
          return (
            <li key={label} className="flex items-center gap-2" title={st === "skipped" ? t.flow.skipped : undefined}>
              <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-latin text-xs font-semibold ${DOT[st]}`}>
                {st === "done" ? "✓" : st === "skipped" ? "–" : i + 1}
              </span>
              <span className={`text-sm leading-snug ${st === "done" || st === "current" ? "font-semibold text-navy-800" : "text-navy-400"}`}>
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
