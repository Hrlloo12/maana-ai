"use client";

import { useEffect, useMemo, useState } from "react";
import { ErrorBox, Loading, PageHeader } from "@/components/ui";
import { api, SourceDoc } from "@/lib/api";
import { topicName, useI18n } from "@/lib/i18n";

export default function SourcesPage() {
  const { t } = useI18n();
  const [docs, setDocs] = useState<SourceDoc[] | null>(null);
  const [filter, setFilter] = useState<string[]>([]);
  const [topic, setTopic] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .sources()
      .then((r) => {
        setDocs(r.documents);
        setFilter(r.production_filter);
      })
      .catch((e) => setError(e.message));
  }, []);

  const topics = useMemo(() => ["all", ...Array.from(new Set((docs ?? []).map((d) => d.topic)))], [docs]);
  if (error) return <ErrorBox message={error} />;
  if (!docs) return <Loading />;
  const shown = docs.filter((d) => topic === "all" || d.topic === topic);

  return (
    <div className="space-y-6">
      <PageHeader title={t.sources.title} subtitle={t.sources.subtitle} />
      <p className="flex flex-wrap items-center gap-2 text-sm text-navy-500">
        {t.sources.filter}:
        {filter.map((f) => (
          <span key={f} className="chip border-sand-300 bg-white text-navy-600">
            {t.review[f] ?? f}
          </span>
        ))}
      </p>
      <div className="flex flex-wrap gap-2">
        {topics.map((x) => (
          <button
            key={x}
            onClick={() => setTopic(x)}
            className={`chip px-4 py-1.5 text-sm ${x === topic ? "border-navy-900 bg-navy-900 text-sand-50" : "border-sand-300 bg-white text-navy-600"}`}
          >
            {x === "all" ? t.sources.all : topicName(x)}
          </button>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {shown.map((d) => (
          <article key={d.id} className="card !p-6">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              <span className="chip border-sand-300 text-navy-600">{topicName(d.topic)}</span>
              <span
                className={`chip ${d.review_status === "reviewed" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-100 bg-amber-50 text-amber-700"}`}
              >
                {t.review[d.review_status] ?? d.review_status}
              </span>
            </div>
            <p className="font-semibold text-navy-900">{d.source_name_ar || d.source_name}</p>
            <p className="mb-3 text-sm text-gold-700">{d.reference_ar || d.reference}</p>
            {d.language !== "ar" && <p className="mb-1 text-xs text-navy-400">{t.common.sourceTextNote}</p>}
            <p className="text-sm leading-relaxed text-navy-600" dir="auto">
              {d.text}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
