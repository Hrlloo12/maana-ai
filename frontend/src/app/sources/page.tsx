"use client";

import { useEffect, useState } from "react";
import { ErrorBox, Loading, PageHeader, SourceText, StarMark } from "@/components/ui";
import { api, SourcesResponse } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function SourcesPage() {
  const { t } = useI18n();
  const s = t.sources;
  const [data, setData] = useState<SourcesResponse | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .sources()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setData(await api.sources(query.trim()));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  return (
    <div className="space-y-8">
      <PageHeader title={s.title} subtitle={s.subtitle} />

      <div className="grid gap-4 md:grid-cols-3">
        {data.collections.map((c) => (
          <article key={c.id} className="card !p-6">
            <StarMark size={20} className="text-gold-500" />
            <h2 className="mt-3 text-xl font-bold text-navy-900">{c.name_ar}</h2>
            <p className="mt-1 text-3xl font-bold text-emerald-700">
              <bdi className="font-latin">{c.count.toLocaleString("en")}</bdi> <span className="text-base font-medium text-navy-500">{s.texts}</span>
            </p>
            <p className="mt-3 text-xs leading-relaxed text-navy-400">
              {s.source}:{" "}
              <a href={c.homepage} target="_blank" rel="noreferrer" className="font-latin text-emerald-700 underline-offset-2 hover:underline" dir="ltr">
                {c.attribution}
              </a>
            </p>
          </article>
        ))}
      </div>
      <p className="text-sm text-navy-500">
        {s.total}: <bdi className="font-latin font-semibold">{data.total.toLocaleString("en")}</bdi> · {s.numberingNote}
      </p>

      <div className="card space-y-4">
        <label htmlFor="q" className="label block">
          {s.searchLabel}
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="q"
            className="input"
            dir="auto"
            placeholder={s.searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button className="btn-primary shrink-0 px-8" disabled={busy || !query.trim()} onClick={search}>
            {busy ? s.searching : s.search}
          </button>
        </div>
        <ErrorBox message={error} />
      </div>

      {data.query && (
        <div className="space-y-4">
          {data.results.length === 0 && <p className="text-navy-500">{s.noResults}</p>}
          {data.results.map((r) => (
            <article key={r.id} className="card !p-6">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <StarMark size={14} className="text-gold-500" />
                <span className="font-semibold text-navy-900">{r.reference_ar}</span>
                <span className="text-sm text-navy-500">{r.source_name_ar}</span>
              </div>
              <SourceText arabic={r.text_ar} text={r.text} />
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
