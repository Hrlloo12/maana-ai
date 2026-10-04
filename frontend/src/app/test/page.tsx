"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import JourneySteps from "@/components/JourneySteps";
import { ErrorBox, Loading, MissingSession, PageHeader, StarMark } from "@/components/ui";
import { api } from "@/lib/api";
import { useAgentRun, useSession } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";

function TestView() {
  const id = useSearchParams().get("id");
  const router = useRouter();
  const { t } = useI18n();
  const { session, error } = useSession(id);
  const { run, running, progress, error: runError } = useAgentRun();
  const [answer, setAnswer] = useState("");

  useEffect(() => {
    if (!session) return;
    if (session.stage !== "awaiting_response") router.replace(`/result/?id=${id}`);
  }, [session, id, router]);

  if (!id) return <MissingSession />;
  if (error) return <ErrorBox message={error} />;
  if (!session || session.stage !== "awaiting_response") return <Loading />;

  async function submit() {
    const res = await run(id!, () => api.analyzeUnderstanding(id!, answer));
    if (res) router.push(`/result/?id=${id}`);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={t.test.title} subtitle={t.test.description} />

      <div className="card mb-6 border-gold-100">
        <div className="flex items-start gap-4">
          <StarMark size={22} className="mt-2 shrink-0 text-gold-500" />
          <p className="text-2xl leading-relaxed text-navy-900" dir="auto">
            {session.original_content}
          </p>
        </div>
      </div>

      <div className="card space-y-5">
        <div>
          <p className="eyebrow mb-2">{t.test.question}</p>
          <p className="text-xl font-semibold text-navy-900" dir="auto">
            {session.understanding_question}
          </p>
          <p className="mt-2 text-sm text-navy-500">{t.test.reassure}</p>
        </div>
        <textarea
          dir="auto"
          className="input min-h-[150px] text-lg"
          placeholder={t.test.placeholder}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          aria-label={t.test.question}
        />
        <ErrorBox message={runError} />
        <button className="btn-primary w-full py-4 text-base" disabled={running || answer.trim().length < 2} onClick={submit}>
          {running ? t.test.running : t.test.cta}
        </button>
      </div>

      <div className="mt-6">
        <JourneySteps progress={progress} running={running} />
      </div>
    </div>
  );
}

export default function TestPage() {
  return (
    <Suspense fallback={<Loading />}>
      <TestView />
    </Suspense>
  );
}
