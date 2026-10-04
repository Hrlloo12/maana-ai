"use client";

import { Progress } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const NODE_STEP: Record<string, number> = {
  retrieve_knowledge: 0,
  meaning_agent: 0,
  understanding_agent: 1,
  retest_understanding: 1,
  verification_agent: 2,
  retest_verification: 2,
  safe_abstention: 2,
  finalize: 2,
  refinement_agent: 3,
};

export default function JourneySteps({ progress, running }: { progress: Progress | null; running: boolean }) {
  const { t } = useI18n();
  if (!running) return null;
  const done = new Set((progress?.completed ?? []).map((n) => NODE_STEP[n]).filter((x) => x != null));
  const active = progress?.active != null ? NODE_STEP[progress.active] : undefined;

  return (
    <div className="card animate-fadeUp" aria-live="polite">
      <p className="label mb-5">{t.journey.title}</p>
      <ol className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
        {t.journey.steps.map((label, i) => {
          const state = i === active ? "active" : done.has(i) ? "done" : "pending";
          return (
            <li key={label} className="flex items-center gap-2 sm:flex-1">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border font-latin text-sm font-semibold ${
                  state === "active"
                    ? "animate-breathe border-emerald-500 bg-emerald-600 text-white"
                    : state === "done"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border-sand-300 bg-white text-navy-400"
                }`}
              >
                {state === "done" ? "✓" : i + 1}
              </span>
              <span className={`text-sm ${state === "pending" ? "text-navy-400" : "font-semibold text-navy-800"}`}>{label}</span>
              {i < t.journey.steps.length - 1 && <span className="mx-1 hidden h-px flex-1 bg-sand-300 sm:block" aria-hidden />}
            </li>
          );
        })}
      </ol>
      {active != null && <p className="mt-5 text-sm text-emerald-700">{t.journey.active[active]}</p>}
      {progress?.error && <p className="mt-3 text-sm text-clay-600">{t.journey.failed}</p>}
    </div>
  );
}
