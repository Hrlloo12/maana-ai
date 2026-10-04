"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBox, Loading, PageHeader } from "@/components/ui";
import { api, Dashboard, pct } from "@/lib/api";
import { topicName, useI18n } from "@/lib/i18n";

export default function DashboardPage() {
  const { t } = useI18n();
  const d = t.dashboard;
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  const stats = [
    { label: d.tested, value: String(data.content_sessions) },
    { label: d.gaps, value: String(data.meaning_gaps_detected) },
    { label: d.improved, value: String(data.meaning_gaps_resolved) },
    { label: d.avgBefore, value: pct(data.average_before_alignment), tone: "text-gold-600" },
    { label: d.avgAfter, value: pct(data.average_after_alignment), tone: "text-emerald-700" },
  ];
  const topics = data.gaps_by_topic ?? [];
  const maxTopic = Math.max(1, ...topics.map((x) => x.count));
  const strategies = data.explanation_strategies ?? [];
  const maxStrategy = Math.max(1, ...strategies.map((x) => x.count));

  return (
    <div className="space-y-8">
      <PageHeader title={d.title} subtitle={d.subtitle} />

      {data.content_sessions === 0 && (
        <div className="card text-center">
          <p className="text-navy-500">{d.none}</p>
          <Link href="/analyze/" className="btn-primary mt-5">
            {d.first}
          </Link>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label} className="card !p-5">
            <p className="font-latin text-3xl font-bold text-navy-900" dir="ltr">
              <span className={s.tone}>{s.value}</span>
            </p>
            <p className="mt-2 text-sm leading-snug text-navy-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <p className="label">{d.beforeAfter}</p>
          <div className="mb-5 mt-2 flex gap-4 text-xs text-navy-500">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-gold-300" /> {t.result.before}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" /> {t.result.after}
            </span>
          </div>
          {data.before_after.length ? (
            <div className="space-y-5">
              {data.before_after.map((s) => (
                <div key={s.session_id}>
                  <p className="mb-2 text-sm text-navy-600">{topicName(s.topic)}</p>
                  <Bar value={s.before} cls="bg-gold-300" />
                  <Bar value={s.after} cls="bg-emerald-600" />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-navy-400">{d.none}</p>
          )}
        </div>

        <div className="space-y-6">
          <div className="card">
            <p className="label mb-5">{d.byTopic}</p>
            {topics.length ? (
              <div className="space-y-3">
                {topics.map((c) => (
                  <div key={c.topic}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="text-navy-700">{topicName(c.topic)}</span>
                      <span className="font-latin text-navy-400">{c.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-sand-100">
                      <div className="h-2 rounded-full bg-gold-500" style={{ width: `${(c.count / maxTopic) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-navy-400">{d.none}</p>
            )}
          </div>

          <div className="card">
            <p className="label mb-5">{d.strategies}</p>
            {strategies.length ? (
              <div className="space-y-3">
                {strategies.map((c) => (
                  <div key={c.strategy}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="text-navy-700">{t.strategies[c.strategy]?.name ?? c.strategy}</span>
                      <span className="font-latin text-navy-400">{c.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-sand-100">
                      <div className="h-2 rounded-full bg-emerald-600" style={{ width: `${(c.count / maxStrategy) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-navy-400">{d.none}</p>
            )}
          </div>

          <div className="card">
            <p className="label mb-4">{d.common}</p>
            {data.most_misunderstood_concepts.length ? (
              <ul className="space-y-2">
                {data.most_misunderstood_concepts.map((c) => (
                  <li key={c.concept} className="flex items-start justify-between gap-3 text-sm" dir="auto">
                    <span className="text-navy-700">{c.concept}</span>
                    <span className="chip shrink-0 border-sand-300 font-latin text-navy-500">{c.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-navy-400">{d.none}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Bar({ value, cls }: { value: number; cls: string }) {
  return (
    <div className="mb-1.5 flex items-center gap-3">
      <div className="h-3 flex-1 rounded-full bg-sand-100">
        <div className={`h-3 rounded-full ${cls}`} style={{ width: `${Math.max(2, value * 100)}%` }} />
      </div>
      <span className="w-12 font-latin text-xs text-navy-500" dir="ltr">
        {pct(value)}
      </span>
    </div>
  );
}
