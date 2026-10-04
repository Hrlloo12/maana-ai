"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBox, Loading, PageHeader, StatusPill } from "@/components/ui";
import { api, pct, RecentSession } from "@/lib/api";
import { topicName, useI18n } from "@/lib/i18n";

export default function ResultsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<RecentSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboard()
      .then((d) => setRows(d.recent_sessions ?? []))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!rows) return <Loading />;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={t.results.title} subtitle={t.results.subtitle} />
      {rows.length === 0 ? (
        <div className="card text-center">
          <p className="text-navy-500">{t.results.empty}</p>
          <Link href="/analyze/" className="btn-primary mt-5">
            {t.nav.test}
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {rows.map((r) => {
            const inProgress = r.stage === "awaiting_response";
            const status = r.status_after ?? r.status_before;
            const href = inProgress ? `/test/?id=${r.session_id}` : `/result/?id=${r.session_id}`;
            return (
              <li key={r.session_id}>
                <Link href={href} className="card flex flex-col gap-4 !p-5 transition hover:shadow-lift sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-lg text-navy-900" dir="auto">
                      {r.content}
                    </p>
                    <p className="mt-1 text-xs text-navy-400">
                      {new Date(r.created_at).toLocaleDateString("ar", { dateStyle: "medium" })}
                      {r.topic ? ` · ${topicName(r.topic)}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {r.stage === "abstained" ? (
                      <StatusPill status="insufficient_evidence" />
                    ) : inProgress || !status ? (
                      <span className="chip border-sand-300 bg-sand-100 text-navy-600">{t.results.inProgress}</span>
                    ) : (
                      <StatusPill status={status} />
                    )}
                    {r.before != null && (
                      <span className="font-latin text-sm text-navy-500" dir="ltr">
                        {pct(r.before)}
                        {r.after != null && r.after !== r.before && <span className="text-emerald-700"> → {pct(r.after)}</span>}
                      </span>
                    )}
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
