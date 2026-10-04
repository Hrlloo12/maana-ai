"use client";

import Link from "next/link";
import { Ornament, PageHeader, StarMark } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function AboutPage() {
  const { t } = useI18n();
  const a = t.about;
  const h = t.home;

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader title={a.title} subtitle={a.lead} />

      <section className="card">
        <h2 className="text-xl font-bold text-navy-900">{a.problemTitle}</h2>
        <p className="mt-3 text-lg leading-relaxed text-navy-600">{a.problem}</p>
      </section>

      <section className="pattern-gold rounded-[2rem] bg-navy-900 px-6 py-10 text-center text-sand-50 shadow-lift sm:px-10">
        <p className="text-2xl font-bold">{h.principleTitle}</p>
        <p className="mt-2 text-navy-300">{h.principle}</p>
      </section>

      <section className="card">
        <h2 className="mb-5 text-xl font-bold text-navy-900">{a.approachTitle}</h2>
        <ul className="space-y-4">
          {a.approach.map((x) => (
            <li key={x} className="flex gap-3 text-navy-700">
              <StarMark size={16} className="mt-1.5 shrink-0 text-gold-500" />
              <span className="leading-relaxed">{x}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="card border-emerald-200">
          <p className="eyebrow mb-3 text-emerald-700">{h.isTitle}</p>
          <p className="text-lg leading-relaxed text-navy-800">{h.isText}</p>
        </div>
        <div className="card">
          <p className="eyebrow mb-3">{h.isNotTitle}</p>
          <ul className="space-y-1.5 text-navy-600">
            {h.isNot.map((x) => (
              <li key={x}>✕ {x}</li>
            ))}
          </ul>
        </div>
      </section>

      <Ornament className="mx-auto max-w-md" />
      <div className="flex flex-wrap justify-center gap-3">
        <Link href="/technology/" className="btn-primary">
          {a.techCta}
        </Link>
        <Link href="/sources/" className="btn-ghost">
          {a.sourcesCta}
        </Link>
      </div>
    </div>
  );
}
