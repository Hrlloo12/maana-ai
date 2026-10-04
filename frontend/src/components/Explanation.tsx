"use client";

import { Refinement } from "@/lib/api";
import { wordDiff } from "@/lib/diff";
import { useI18n } from "@/lib/i18n";

const STRATEGY_ICON: Record<string, string> = {
  simplification: "✦",
  comparison: "⇄",
  example: "◆",
  visual: "◎",
  step_by_step: "☰",
};

export function StrategyBadge({ strategy }: { strategy: string }) {
  const { t } = useI18n();
  const s = t.strategies[strategy];
  if (!s) return null;
  return (
    <span className="chip border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700">
      <span aria-hidden>{STRATEGY_ICON[strategy]}</span>
      {s.name}
    </span>
  );
}

export default function ExplanationView({ refinement, original }: { refinement: Refinement; original: string }) {
  const { t } = useI18n();
  const r = refinement;
  const diff = wordDiff(original, r.improved_content);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-clay-100 bg-clay-50/50 p-5">
          <p className="text-xs font-semibold text-clay-600">{t.result.cause}</p>
          <p className="mt-1 font-semibold text-navy-900">{t.causes[r.root_cause] ?? r.root_cause}</p>
          <p className="mt-2 leading-relaxed text-navy-700" dir="auto">
            {r.diagnosis}
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5">
          <p className="text-xs font-semibold text-emerald-700">{t.result.strategy}</p>
          <div className="mt-2">
            <StrategyBadge strategy={r.strategy} />
          </div>
          <p className="mt-2 leading-relaxed text-navy-700" dir="auto">
            {r.strategy_reason}
          </p>
          {r.strategy_adjusted && <p className="mt-2 text-xs text-amber-700">{t.result.strategyAdjusted}</p>}
        </div>
      </div>

      <figure className="rounded-2xl border-2 border-emerald-200 bg-white p-5 sm:p-6">
        <figcaption className="mb-3 text-xs font-semibold text-emerald-700">{t.result.newExplanation}</figcaption>
        <blockquote className="text-xl leading-relaxed text-navy-900" dir="auto">
          {diff
            .filter((p) => p.type !== "removed")
            .map((p, i) =>
              p.type === "added" ? (
                <mark key={i} className="rounded bg-emerald-100 px-0.5 text-emerald-800">
                  {p.text}
                </mark>
              ) : (
                <span key={i}>{p.text}</span>
              ),
            )}
        </blockquote>
        <div className="mt-5">
          <StrategyBody refinement={r} />
        </div>
      </figure>

      <div className="grid gap-4 md:grid-cols-2">
        <figure className="card-quiet">
          <figcaption className="mb-2 text-xs font-semibold text-navy-500">{t.result.original}</figcaption>
          <blockquote className="text-navy-500" dir="auto">
            {original}
          </blockquote>
        </figure>
        {r.changes.length > 0 && (
          <div className="card-quiet">
            <p className="mb-2 text-xs font-semibold text-navy-500">{t.result.whatChanged}</p>
            <ul className="space-y-2 text-sm">
              {r.changes.map((c, i) => (
                <li key={i} dir="auto">
                  <span className="text-clay-600 line-through decoration-clay-300">{c.original_issue}</span>
                  <span className="mx-2 text-navy-300">←</span>
                  <span className="font-semibold text-emerald-700">{c.improvement}</span>
                  <p className="mt-0.5 text-navy-500">{c.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function StrategyBody({ refinement: r }: { refinement: Refinement }) {
  if (r.strategy === "comparison" && r.comparison_rows.length) {
    return (
      <div className="overflow-hidden rounded-2xl border border-sand-200" dir="auto">
        <div className="grid grid-cols-[1fr_1.2fr_1.2fr] bg-navy-900 text-sm font-semibold text-sand-50">
          <span className="px-3 py-2.5" />
          <span className="px-3 py-2.5">{r.comparison_left_label}</span>
          <span className="px-3 py-2.5">{r.comparison_right_label}</span>
        </div>
        {r.comparison_rows.map((row, i) => (
          <div key={i} className={`grid grid-cols-[1fr_1.2fr_1.2fr] text-sm ${i % 2 ? "bg-sand-50" : "bg-white"}`}>
            <span className="px-3 py-2.5 font-semibold text-navy-700">{row.aspect}</span>
            <span className="px-3 py-2.5 text-navy-800">{row.left}</span>
            <span className="px-3 py-2.5 text-navy-800">{row.right}</span>
          </div>
        ))}
      </div>
    );
  }
  if (r.strategy === "step_by_step" && r.steps.length) {
    return (
      <ol className="space-y-2" dir="auto">
        {r.steps.map((s, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-600 font-latin text-sm font-semibold text-white">
              {i + 1}
            </span>
            <span className="leading-relaxed text-navy-800">{s}</span>
          </li>
        ))}
      </ol>
    );
  }
  if (r.strategy === "example" && r.example) {
    return (
      <div className="flex gap-3 rounded-2xl bg-gold-50 p-4">
        <span className="text-xl text-gold-600" aria-hidden>
          ◆
        </span>
        <p className="leading-relaxed text-navy-800" dir="auto">
          {r.example}
        </p>
      </div>
    );
  }
  if (r.strategy === "visual" && r.visual_nodes.length) {
    return (
      <ol className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center" dir="auto">
        {r.visual_nodes.map((n, i) => (
          <li key={i} className="flex items-center gap-2 sm:flex-1">
            <div className="flex-1 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-center">
              <p className="font-semibold text-navy-900">{n.label}</p>
              {n.detail && <p className="mt-1 text-xs text-navy-500">{n.detail}</p>}
            </div>
            {i < r.visual_nodes.length - 1 && (
              <span className="hidden text-xl text-emerald-600 sm:inline" aria-hidden>
                ←
              </span>
            )}
          </li>
        ))}
      </ol>
    );
  }
  return null;
}
