"use client";

import Link from "next/link";
import { Ornament } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function Footer() {
  const { t } = useI18n();
  return (
    <footer className="mx-auto max-w-6xl px-4 pb-12 sm:px-6">
      <Ornament className="mb-6" />
      <div className="flex flex-col gap-4 text-sm text-navy-500 sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-2xl leading-relaxed">{t.footer.note}</p>
        <div className="flex shrink-0 gap-5">
          <Link href="/technology/" className="hover:text-navy-900">
            {t.footer.tech}
          </Link>
          <Link href="/sources/" className="hover:text-navy-900">
            {t.footer.sources}
          </Link>
        </div>
      </div>
    </footer>
  );
}
