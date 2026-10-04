"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import JourneySteps from "@/components/JourneySteps";
import { ErrorBox, PageHeader } from "@/components/ui";
import { api, DemoScenario, Health, newSessionId } from "@/lib/api";
import { useAgentRun } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";

const LANGUAGES = ["Arabic", "English", "French", "Urdu", "Indonesian", "Turkish", "Spanish", "German"];

export default function AnalyzePage() {
  const router = useRouter();
  const { t } = useI18n();
  const [content, setContent] = useState("");
  const [contentLang, setContentLang] = useState("Arabic");
  const [targetLang, setTargetLang] = useState("Arabic");
  const [demo, setDemo] = useState<DemoScenario[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const { run, running, progress, error } = useAgentRun();

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api
      .demo()
      .then((d) => setDemo(d.scenarios))
      .catch(() => setDemo([]));
  }, []);

  async function analyze() {
    const sid = newSessionId();
    const res = await run(sid, () =>
      api.analyzeContent({ session_id: sid, content, content_language: contentLang, target_language: targetLang }),
    );
    if (!res) return;
    router.push(res.stage === "abstained" ? `/result/?id=${sid}` : `/test/?id=${sid}`);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader eyebrow={t.nav.test} title={t.analyze.title} subtitle={t.analyze.subtitle} />

      {health && !health.llm_configured && (
        <div className="mb-5">
          <ErrorBox message={t.common.noKey} />
        </div>
      )}

      <div className="card space-y-6">
        <div>
          <label className="label mb-2 block" htmlFor="content">
            {t.analyze.content}
          </label>
          <textarea
            id="content"
            dir="auto"
            className="input min-h-[170px] text-lg leading-relaxed"
            placeholder={t.analyze.placeholder}
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <p className="mt-2 text-sm text-navy-400">{t.analyze.hint}</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <LangSelect id="clang" label={t.analyze.contentLang} value={contentLang} onChange={setContentLang} />
          <LangSelect id="tlang" label={t.analyze.targetLang} value={targetLang} onChange={setTargetLang} />
        </div>

        {demo.length > 0 && (
          <div>
            <p className="mb-2 text-sm text-navy-500">{t.analyze.examples}</p>
            <div className="flex flex-wrap gap-2">
              {demo.map((d) => (
                <button
                  key={d.id}
                  className="chip border-sand-300 bg-sand-50 px-3 py-1.5 text-sm text-navy-700 hover:border-emerald-500 hover:text-emerald-700"
                  onClick={() => {
                    setContent(d.content);
                    setContentLang(d.content_language);
                    setTargetLang(d.target_language);
                  }}
                  dir="auto"
                >
                  {d.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <ErrorBox message={error} />
        {content.trim().length > 0 && content.trim().length < 5 && <p className="text-sm text-amber-700">{t.analyze.tooShort}</p>}
        <button className="btn-primary w-full py-4 text-base" disabled={running || content.trim().length < 5} onClick={analyze}>
          {running ? t.analyze.running : t.analyze.cta}
        </button>
      </div>

      <div className="mt-6">
        <JourneySteps progress={progress} running={running} />
      </div>
    </div>
  );
}

function LangSelect({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (v: string) => void }) {
  const { t } = useI18n();
  return (
    <div>
      <label className="label mb-2 block" htmlFor={id}>
        {label}
      </label>
      <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {LANGUAGES.map((l) => (
          <option key={l} value={l}>
            {t.langs[l] ?? l}
          </option>
        ))}
      </select>
    </div>
  );
}
