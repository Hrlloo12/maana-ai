"use client";

import { SessionView } from "@/lib/api";

const PIPELINE = [
  { key: "rag", node: "retrieve_knowledge", title: "استرجاع المعرفة", sub: "RAG · بوابة موضوع · حد صلة · تقييم صلة كل مقطع", kind: "rag" },
  { key: "meaning", node: "meaning_agent", title: "وكيل المعنى", sub: "معانٍ مقصودة من النص فقط · سياق خلفي · صياغات ملتبسة", kind: "agent" },
  { key: "wait1", node: "interrupt", title: "انتظار إجابة القارئ", sub: "توقف المسار حتى يجيب القارئ", kind: "wait" },
  { key: "understanding", node: "understanding_agent", title: "وكيل الفهم", sub: "وصف ما فهمه القارئ دون الاطلاع على المصادر", kind: "agent" },
  { key: "verification", node: "verification_agent", title: "وكيل التحقق", sub: "نوع الفجوة لكل معنى · عبارة داعمة من المصدر", kind: "agent" },
  { key: "refinement", node: "refinement_agent", title: "وكيل الشرح التكيّفي", sub: "سبب الالتباس · اختيار طريقة الشرح · شرح جديد", kind: "agent" },
  { key: "retest", node: "retest_*", title: "إعادة الاختبار", sub: "الفهم ثم التحقق بالسؤال نفسه والمعاني نفسها", kind: "agent" },
  { key: "finalize", node: "finalize", title: "قياس التحسن", sub: "الدرجة قبل وبعد · حالة كل سوء فهم", kind: "io" },
] as const;

function doneFromSession(s: SessionView | null): Set<string> {
  const done = new Set<string>();
  if (!s) return done;
  if (s.rag_context || s.rag_decisions) done.add("rag");
  if (s.meaning_analysis) done.add("meaning");
  if (s.user_response) done.add("wait1");
  if (s.user_interpretation) done.add("understanding");
  if (s.verification || s.abstention) done.add("verification");
  if (s.refinement) done.add("refinement");
  if (s.second_verification) done.add("retest");
  if (s.final_result) done.add("finalize");
  return done;
}

const KIND_TAG: Record<string, { label: string; cls: string }> = {
  agent: { label: "وكيل", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  rag: { label: "RAG", cls: "border-gold-100 bg-gold-50 text-gold-700" },
  wait: { label: "توقف", cls: "border-sand-300 bg-sand-100 text-navy-600" },
  io: { label: "حساب برمجي", cls: "border-sand-300 bg-sand-100 text-navy-600" },
};

export default function AgentPipeline({ session }: { session: SessionView | null }) {
  const done = doneFromSession(session);
  const skipped = new Set<string>();
  if (session?.final_result && !session.refinement) ["refinement", "retest"].forEach((k) => skipped.add(k));

  return (
    <ol className="space-y-1">
      {PIPELINE.map((p, i) => {
        const st = skipped.has(p.key) ? "skipped" : done.has(p.key) ? "done" : session ? "pending" : "idle";
        const tag = KIND_TAG[p.kind];
        return (
          <li key={p.key} className="relative flex gap-3">
            {i < PIPELINE.length - 1 && (
              <span className={`absolute start-[13px] top-8 h-[calc(100%-14px)] w-px ${st === "done" ? "bg-emerald-300" : "bg-sand-300"}`} />
            )}
            <span
              className={`relative z-10 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-latin text-[11px] font-bold ${
                st === "done"
                  ? "border-emerald-500 bg-emerald-600 text-white"
                  : st === "skipped"
                    ? "border-sand-300 bg-sand-50 text-navy-300"
                    : "border-sand-300 bg-white text-navy-500"
              }`}
            >
              {st === "done" ? "✓" : st === "skipped" ? "–" : i + 1}
            </span>
            <div className={`pb-4 ${st === "pending" || st === "skipped" ? "opacity-55" : ""}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-navy-900">{p.title}</span>
                <span className={`chip px-2 py-0 text-[10px] ${tag.cls}`}>{tag.label}</span>
                <code className="font-latin text-[11px] text-navy-400" dir="ltr">
                  {p.node}
                </code>
              </div>
              <p className="text-xs text-navy-500">{p.sub}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
