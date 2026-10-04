"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import IntroAvatar, { shouldAutoOpenIntro } from "@/components/IntroAvatar";
import { Ornament, StarMark } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function Landing() {
  const { t } = useI18n();
  const h = t.home;
  const [intro, setIntro] = useState<{ open: boolean; autoStart: boolean }>({ open: false, autoStart: false });
  useEffect(() => {
    if (shouldAutoOpenIntro()) setIntro({ open: true, autoStart: false });
  }, []);

  return (
    <div className="space-y-24">
      <IntroAvatar open={intro.open} autoStart={intro.autoStart} onClose={() => setIntro({ open: false, autoStart: false })} />

      <section className="grid items-center gap-12 pt-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="animate-fadeUp">
          <p className="eyebrow">{h.eyebrow}</p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.25] text-navy-900 sm:text-5xl lg:text-[3.4rem]">{h.headline}</h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-navy-600">{h.description}</p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/analyze/" className="btn-primary px-8">
              {h.cta}
            </Link>
            <a href="#how" className="btn-ghost">
              {h.how}
            </a>
            <button type="button" onClick={() => setIntro({ open: true, autoStart: true })} className="btn-ghost">
              <span className="text-emerald-600" aria-hidden>
                ▶
              </span>
              {h.watchIntro}
            </button>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-sm animate-fadeUp [animation-delay:120ms]">
          <div className="arch pattern-gold relative overflow-hidden bg-navy-900 px-8 pb-12 pt-20 text-center shadow-lift">
            <div className="arch pointer-events-none absolute inset-3 border border-gold-300/30" />
            <StarMark size={40} className="mx-auto text-gold-300" />
            <p className="mt-6 font-display text-7xl font-bold leading-none text-sand-50">مَعنى</p>
            <div className="mx-auto mt-8 h-px w-24 bg-gradient-to-r from-transparent via-gold-300/70 to-transparent" />
            <p className="mt-6 text-sm leading-relaxed text-navy-300">{h.archLine}</p>
          </div>
        </div>
      </section>

      <section className="card">
        <p className="eyebrow mb-6 text-center">{h.exampleTitle}</p>
        <div className="grid gap-6 md:grid-cols-[1fr_auto_1fr] md:items-center">
          <div className="card-quiet">
            <p className="label mb-2">{h.contentSays}</p>
            <p className="text-lg text-navy-900">{h.exampleContent}</p>
          </div>
          <div className="text-center font-latin text-3xl text-gold-500" aria-hidden>
            ≠
          </div>
          <div className="card-quiet">
            <p className="label mb-2">{h.readerUnderstood}</p>
            <p className="text-lg text-navy-900">{h.exampleReader}</p>
          </div>
        </div>
        <p className="mt-6 text-center text-gold-700">⚠ {h.exampleGap}</p>
      </section>

      <section id="how" className="scroll-mt-24">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold text-navy-900">{h.howTitle}</h2>
          <p className="mt-2 text-navy-500">{h.howSubtitle}</p>
        </div>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {h.steps.map((s, i) => (
            <li key={s.t} className="card relative overflow-hidden">
              <span className="font-display text-5xl font-bold text-gold-300">{"١٢٣٤"[i]}</span>
              <h3 className="mt-3 text-lg font-bold text-navy-900">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-navy-500">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pattern-gold rounded-[2rem] bg-navy-900 px-6 py-14 text-center text-sand-50 shadow-lift sm:px-12">
        <StarMark size={30} className="mx-auto text-gold-300" />
        <h2 className="mt-5 text-2xl font-bold sm:text-3xl">{h.principleTitle}</h2>
        <p className="mx-auto mt-3 max-w-2xl text-lg text-navy-300">{h.principle}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="card border-emerald-200">
          <p className="eyebrow mb-3 text-emerald-700">{h.isTitle}</p>
          <p className="text-lg leading-relaxed text-navy-800">{h.isText}</p>
        </div>
        <div className="card">
          <p className="eyebrow mb-3">{h.isNotTitle}</p>
          <ul className="flex flex-wrap gap-2">
            {h.isNot.map((x) => (
              <li key={x} className="chip border-sand-300 bg-sand-50 px-3 py-1.5 text-sm text-navy-600">
                <span className="text-clay-500" aria-hidden>
                  ✕
                </span>
                {x}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="text-center">
        <h2 className="text-2xl font-bold text-navy-900">{h.forTitle}</h2>
        <ul className="mx-auto mt-6 flex max-w-3xl flex-wrap justify-center gap-3">
          {h.audiences.map((a) => (
            <li key={a} className="chip border-gold-100 bg-white px-4 py-2 text-sm text-navy-700 shadow-soft">
              <StarMark size={12} className="text-gold-500" />
              {a}
            </li>
          ))}
        </ul>
        <Ornament className="mx-auto my-12 max-w-md" />
        <p className="text-xl font-semibold text-navy-800">{h.ctaBand}</p>
        <Link href="/analyze/" className="btn-accent mt-6 px-8">
          {h.cta}
        </Link>
      </section>
    </div>
  );
}
