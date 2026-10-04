"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { StarMark } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function Nav() {
  const path = usePathname() ?? "/";
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  const links = [
    { href: "/", label: t.nav.home, match: (p: string) => p === "/" },
    { href: "/analyze/", label: t.nav.test, match: (p: string) => ["/analyze", "/test", "/result"].some((x) => p.startsWith(x)) },
    { href: "/dashboard/", label: t.nav.dashboard, match: (p: string) => p.startsWith("/dashboard") },
    { href: "/evaluation/", label: t.nav.evaluation, match: (p: string) => p.startsWith("/evaluation") },
    { href: "/about/", label: t.nav.about, match: (p: string) => ["/about", "/technology", "/sources"].some((x) => p.startsWith(x)) },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-sand-200/80 bg-sand-50/85 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-gold-300">
            <StarMark size={24} />
          </span>
          <span className="font-display text-2xl font-bold leading-none text-navy-900">{t.brand}</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-full px-4 py-2 text-[15px] transition ${
                l.match(path) ? "bg-navy-900 text-sand-50" : "text-navy-600 hover:bg-sand-100 hover:text-navy-900"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2 md:hidden">
          <button
            className="rounded-full border border-sand-300 bg-white p-2 text-navy-800"
            aria-label={t.menu}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden>
              <path d={open ? "M5 5l10 10M15 5L5 15" : "M3 6h14M3 10h14M3 14h14"} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <nav className="border-t border-sand-200 bg-sand-50 px-4 py-3 md:hidden">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`block rounded-xl px-4 py-3 ${l.match(path) ? "bg-navy-900 text-sand-50" : "text-navy-700"}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
