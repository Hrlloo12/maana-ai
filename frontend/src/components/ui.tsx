"use client";

import Link from "next/link";
import { Evidence, GapStatus, pct, Resolution } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export function PageHeader({ eyebrow, title, subtitle }: { eyebrow?: string; title: string; subtitle?: string }) {
  return (
    <div className="mb-10 animate-fadeUp">
      {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
      <h1 className="text-3xl font-bold leading-tight text-navy-900 sm:text-4xl">{title}</h1>
      {subtitle && <p className="mt-3 max-w-2xl text-lg text-navy-500">{subtitle}</p>}
    </div>
  );
}

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-2xl border border-clay-100 bg-clay-50 px-4 py-3 text-sm text-clay-700" role="alert" dir="auto">
      {message}
    </div>
  );
}

export function Loading({ text }: { text?: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-3 py-10 text-navy-500">
      <StarMark size={22} className="animate-spin text-gold-500 [animation-duration:3s]" />
      <span>{text ?? t.common.loading}</span>
    </div>
  );
}

export function MissingSession() {
  const { t } = useI18n();
  return (
    <div className="card mx-auto max-w-lg text-center">
      <p className="text-navy-600">{t.common.noSession}</p>
      <Link href="/analyze/" className="btn-primary mt-5">
        {t.common.startNew}
      </Link>
    </div>
  );
}

export function StarMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round">
        <rect x="8" y="8" width="16" height="16" />
        <rect x="8" y="8" width="16" height="16" transform="rotate(45 16 16)" />
      </g>
      <circle cx="16" cy="16" r="2.4" fill="currentColor" />
    </svg>
  );
}

export function Ornament({ className = "" }: { className?: string }) {
  return (
    <div className={`ornament ${className}`} aria-hidden>
      <StarMark size={18} />
    </div>
  );
}

const STATUS_TONE: Record<GapStatus, string> = {
  understood: "border-emerald-200 bg-emerald-50 text-emerald-700",
  partial_gap: "border-amber-100 bg-amber-50 text-amber-700",
  major_gap: "border-clay-100 bg-clay-50 text-clay-700",
  insufficient_evidence: "border-sand-300 bg-sand-100 text-navy-600",
};

export function StatusPill({ status }: { status: GapStatus }) {
  const { t } = useI18n();
  return <span className={`chip px-3.5 py-1.5 text-sm ${STATUS_TONE[status]}`}>{t.status[status]}</span>;
}

const GAP_TONE: Record<string, string> = {
  correct_understanding: "border-emerald-200 bg-emerald-50 text-emerald-700",
  missing_intended_meaning: "border-amber-100 bg-amber-50 text-amber-700",
  distorted_meaning: "border-clay-100 bg-clay-50 text-clay-700",
  concept_confusion: "border-clay-100 bg-clay-50 text-clay-700",
  ambiguity_triggered: "border-gold-100 bg-gold-50 text-gold-700",
  insufficient_evidence: "border-sand-300 bg-sand-100 text-navy-600",
};

export function GapTypePill({ type }: { type: string }) {
  const { t } = useI18n();
  return <span className={`chip ${GAP_TONE[type] ?? GAP_TONE.insufficient_evidence}`}>{t.gapType[type] ?? type}</span>;
}

const RESOLUTION_TONE: Record<Resolution, { tone: string; icon: string }> = {
  resolved: { tone: "border-emerald-200 bg-emerald-50 text-emerald-700", icon: "✓" },
  partially_resolved: { tone: "border-amber-100 bg-amber-50 text-amber-700", icon: "◐" },
  remains: { tone: "border-clay-100 bg-clay-50 text-clay-700", icon: "!" },
};

export function ResolutionPill({ status, large = false }: { status: Resolution; large?: boolean }) {
  const { t } = useI18n();
  const r = RESOLUTION_TONE[status];
  return (
    <span className={`chip ${large ? "px-4 py-2 text-base" : ""} ${r.tone}`}>
      <span aria-hidden>{r.icon}</span>
      {t.resolution[status]}
    </span>
  );
}

export function ScoreRing({
  value,
  label,
  size = 150,
  tone = "emerald",
}: {
  value: number;
  label?: string;
  size?: number;
  tone?: "emerald" | "navy" | "gold" | "muted";
}) {
  const stroke = 10;
  const r = (size - stroke - 4) / 2;
  const c = 2 * Math.PI * r;
  const color = { emerald: "#147563", navy: "#13254d", gold: "#b48f45", muted: "#a3aec7" }[tone];
  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="#ebe3d3" strokeWidth={stroke} fill="none" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={stroke}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - Math.max(0, Math.min(1, value)))}
            style={{ transition: "stroke-dashoffset 1.1s ease" }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-latin text-3xl font-bold text-navy-900" dir="ltr">
          {pct(value)}
        </span>
      </div>
      {label && <span className="mt-3 text-sm font-medium text-navy-500">{label}</span>}
    </div>
  );
}

export function Section({
  n,
  title,
  help,
  children,
  tone = "default",
}: {
  n?: number;
  title: string;
  help?: string;
  children: React.ReactNode;
  tone?: "default" | "highlight";
}) {
  return (
    <section className={`card animate-fadeUp ${tone === "highlight" ? "border-emerald-200 bg-gradient-to-b from-emerald-50/70 to-white" : ""}`}>
      <div className="mb-5 flex items-start gap-3">
        {n != null && (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gold-300 bg-gold-50 font-latin text-sm font-semibold text-gold-700">
            {n}
          </span>
        )}
        <div>
          <h2 className="text-xl font-bold text-navy-900">{title}</h2>
          {help && <p className="mt-1 text-sm text-navy-500">{help}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export function EvidenceList({ items }: { items: Evidence[] }) {
  const { t } = useI18n();
  if (!items.length) return null;
  return (
    <div className="space-y-3">
      {items.map((e) => (
        <details key={e.evidence_id + e.reference} className="group rounded-2xl border border-sand-200 bg-sand-50/70 px-4 py-3">
          <summary className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <StarMark size={14} className="text-gold-500" />
            <span className="font-semibold text-navy-800">{e.reference_ar || e.reference}</span>
            <span className="text-sm text-navy-500">{e.source_name_ar || e.source_name}</span>
            <span className="ms-auto text-xs text-emerald-700 group-open:hidden">{t.common.viewSource}</span>
          </summary>
          {e.verified_quote && (
            <div className="mt-3 rounded-xl bg-emerald-50/80 px-4 py-3">
              <p className="text-xs font-semibold text-emerald-700">{t.common.verifiedQuote}</p>
              <p className="mt-1 text-sm leading-relaxed text-navy-800" dir="auto">
                «{e.verified_quote}»
              </p>
            </div>
          )}
          <SourceText arabic={e.supporting_text_ar} text={e.supporting_text} />
        </details>
      ))}
    </div>
  );
}

export function SourceText({ arabic, text }: { arabic?: string; text: string }) {
  const { t } = useI18n();
  const translated = Boolean(arabic) && arabic !== text;
  return (
    <div className="mt-3 space-y-3">
      {arabic && (
        <blockquote className="max-h-72 overflow-y-auto border-s-2 border-gold-300 ps-4 font-display text-lg leading-loose text-navy-900" dir="rtl" lang="ar">
          {arabic}
        </blockquote>
      )}
      {(translated || !arabic) && (
        <div>
          <p className="text-xs text-navy-400">{t.common.sourceTextNote}</p>
          <blockquote className="mt-1 max-h-48 overflow-y-auto border-s-2 border-sand-300 ps-4 text-sm leading-relaxed text-navy-600" dir="ltr" lang="en">
            {text}
          </blockquote>
        </div>
      )}
    </div>
  );
}

export function Quote({ children, label }: { children: React.ReactNode; label?: string }) {
  return (
    <figure className="card-quiet">
      {label && <figcaption className="mb-2 text-xs font-semibold text-navy-500">{label}</figcaption>}
      <blockquote className="text-lg leading-relaxed text-navy-900" dir="auto">
        {children}
      </blockquote>
    </figure>
  );
}
