"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { StarMark } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

const VIDEO_URL = process.env.NEXT_PUBLIC_INTRO_VIDEO_URL || "";
const SEEN_KEY = "maana-intro-seen";

export const INTRO_CUES = [
  "السلام عليكم ورحمة الله وبركاته.",
  "قد يصل المحتوى الإسلامي إلى ملايين الأشخاص حول العالم...",
  "لكن هل تصل كلماته فقط، أم يصل معناها كما قُصد له أن يصل؟",
  "بين اختلاف اللغات والثقافات والخلفيات المعرفية،",
  "قد يكون المحتوى صحيحًا، وقد تكون ترجمته سليمة،",
  "ومع ذلك يُفهم بطريقة مختلفة عن المقصود.",
  "لهذا وُجد «مَعنى».",
  "منصة ذكية لا تكتفي بعرض المحتوى، بل تقيس ما فهمه المتلقي فعلًا،",
  "وتكشف فجوات الفهم، وتتحقق من المفاهيم بالرجوع إلى مصادر موثوقة،",
  "ثم تحسّن طريقة الشرح وتقيس أثر هذا التحسين.",
  "«مَعنى» ينقلنا من سؤال: هل ترجمنا المحتوى بشكل صحيح؟",
  "إلى سؤال أهم: هل وصل المعنى بأمانة؟",
  "لأن الكلمة قد تصل...",
  "لكن الأثر الحقيقي يبدأ عندما يصل المعنى.",
];

const cueMs = (text: string) => Math.max(1400, text.length * 40 + 250);
const CUE_WEIGHTS = INTRO_CUES.map(cueMs);
const TOTAL_WEIGHT = CUE_WEIGHTS.reduce((a, b) => a + b, 0);

const PREFERRED_VOICES = ["Hamed", "Naayf", "Maged", "Tarik", "Shakir"];

function pickArabicVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  const arabic = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("ar"));
  if (!arabic.length) return null;
  for (const name of PREFERRED_VOICES) {
    const v = arabic.find((x) => x.name.includes(name));
    if (v) return v;
  }
  return arabic.find((v) => v.lang.toLowerCase() === "ar-sa") ?? arabic[0];
}

type Phase = "ready" | "playing" | "ended";

export default function IntroAvatar({
  open,
  autoStart,
  onClose,
}: {
  open: boolean;
  autoStart: boolean;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const it = t.intro;

  const [phase, setPhase] = useState<Phase>("ready");
  const [cue, setCue] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [videoOk, setVideoOk] = useState(Boolean(VIDEO_URL));
  const [videoProgress, setVideoProgress] = useState(0);

  const runRef = useRef(0);
  const mutedRef = useRef(false);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const playBtnRef = useRef<HTMLButtonElement | null>(null);
  const ctaRef = useRef<HTMLAnchorElement | null>(null);

  const useVideo = Boolean(VIDEO_URL) && videoOk;

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const load = () => setVoice(pickArabicVoice());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, []);

  const stopAll = useCallback(() => {
    runRef.current++;
    setSpeaking(false);
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    videoRef.current?.pause();
  }, []);

  const runCue = useCallback(
    (text: string, run: number) =>
      new Promise<void>((resolve) => {
        const silentMs = cueMs(text);
        const canSpeak = !mutedRef.current && voice && "speechSynthesis" in window;
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          if (runRef.current === run) setSpeaking(false);
          resolve();
        };
        const timer = setTimeout(finish, canSpeak ? silentMs * 2.5 + 2000 : silentMs);
        setSpeaking(true);
        if (canSpeak) {
          const u = new SpeechSynthesisUtterance(text);
          u.voice = voice;
          u.lang = voice.lang;
          u.rate = 1.08;
          u.pitch = 0.95;
          u.onend = finish;
          u.onerror = finish;
          utterRef.current = u;
          window.speechSynthesis.speak(u);
        }
      }),
    [voice],
  );

  const play = useCallback(async () => {
    stopAll();
    const run = runRef.current;
    setCue(0);
    setPhase("playing");

    if (useVideo && videoRef.current) {
      const v = videoRef.current;
      v.currentTime = 0;
      v.muted = mutedRef.current;
      try {
        await v.play();
      } catch {
        v.muted = true;
        mutedRef.current = true;
        setMuted(true);
        v.play().catch(() => setVideoOk(false));
      }
      return;
    }

    for (let i = 0; i < INTRO_CUES.length; i++) {
      if (runRef.current !== run) return;
      setCue(i);
      await runCue(INTRO_CUES[i], run);
    }
    if (runRef.current === run) setPhase("ended");
  }, [runCue, stopAll, useVideo]);
  const playRef = useRef(play);
  playRef.current = play;

  const toggleMute = () => {
    const next = !muted;
    mutedRef.current = next;
    setMuted(next);
    if (useVideo && videoRef.current) videoRef.current.muted = next;
    else if (next && "speechSynthesis" in window) window.speechSynthesis.cancel();
  };

  const close = useCallback(() => {
    stopAll();
    try {
      sessionStorage.setItem(SEEN_KEY, "1");
    } catch {}
    onClose();
  }, [onClose, stopAll]);

  useEffect(() => {
    if (!open) return;
    setPhase("ready");
    setCue(0);
    setVideoProgress(0);
    if (autoStart) playRef.current();
    else requestAnimationFrame(() => playBtnRef.current?.focus());
  }, [open, autoStart]);

  useEffect(() => {
    if (phase === "ended") ctaRef.current?.focus();
  }, [phase]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, close]);

  useEffect(() => stopAll, [stopAll]);

  const onVideoTime = () => {
    const v = videoRef.current;
    if (!v || !v.duration) return;
    const p = v.currentTime / v.duration;
    setVideoProgress(p);
    let acc = 0;
    for (let i = 0; i < CUE_WEIGHTS.length; i++) {
      acc += CUE_WEIGHTS[i] / TOTAL_WEIGHT;
      if (p < acc) {
        setCue(i);
        return;
      }
    }
    setCue(INTRO_CUES.length - 1);
  };

  if (!open) return null;

  const progress = phase === "ended" ? 1 : phase === "ready" ? 0 : useVideo ? videoProgress : (cue + 1) / INTRO_CUES.length;
  const silentOnly = !useVideo && !voice;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-navy-950/95 p-3 backdrop-blur-sm sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={it.dialog}
      dir="rtl"
    >
      <div className="w-full max-w-4xl animate-fadeUp">
        <div className="mb-3 flex items-center justify-between gap-3 text-sand-50">
          <div className="flex items-center gap-2">
            <StarMark size={22} className="text-gold-300" />
            <span className="font-display text-2xl font-bold leading-none">مَعنى</span>
          </div>
          <button type="button" onClick={close} className="btn px-4 py-2 text-sm text-sand-50/90 ring-1 ring-sand-50/25 hover:bg-sand-50/10 focus-visible:ring-gold-300/60">
            {phase === "ended" ? it.close : it.skip}
            <span aria-hidden>←</span>
          </button>
        </div>

        <div className="intro-stage relative aspect-[4/5] w-full overflow-hidden rounded-[1.75rem] bg-navy-900 shadow-lift ring-1 ring-gold-300/20 sm:aspect-video">
          {useVideo ? (
            <video
              ref={videoRef}
              src={VIDEO_URL}
              className="absolute inset-0 h-full w-full object-cover"
              playsInline
              preload="auto"
              onTimeUpdate={onVideoTime}
              onEnded={() => setPhase("ended")}
              onError={() => setVideoOk(false)}
            />
          ) : (
            <>
              <IntroScene />
              <div className="absolute inset-x-0 bottom-0 flex h-[86%] justify-center sm:h-[92%]">
                <GuideAvatar speaking={speaking && phase === "playing"} />
              </div>
            </>
          )}

          <span className="absolute start-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-navy-950/60 px-3 py-1 text-xs font-medium text-sand-100 ring-1 ring-emerald-500/40 backdrop-blur">
            <span className={`h-1.5 w-1.5 rounded-full bg-emerald-500 ${speaking ? "animate-pulse" : ""}`} />
            {it.guide}
          </span>

          {phase === "playing" && (
            <div className="absolute inset-x-3 bottom-4 flex justify-center sm:inset-x-10 sm:bottom-6" aria-live="polite">
              <p key={cue} lang="ar" dir="rtl" className="max-w-2xl animate-fadeUp rounded-2xl bg-navy-950/75 px-5 py-3 text-center text-base font-medium text-sand-50 shadow-lift backdrop-blur sm:text-xl">
                <Subtitle text={INTRO_CUES[cue]} />
              </p>
            </div>
          )}

          {phase === "ready" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-t from-navy-950/85 via-navy-950/30 to-transparent px-6 text-center">
              <button
                ref={playBtnRef}
                type="button"
                onClick={play}
                aria-label={it.play}
                className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-600 text-white shadow-lift ring-4 ring-emerald-500/30 transition hover:scale-105 hover:bg-emerald-700 focus:outline-none focus-visible:ring-gold-300 motion-safe:animate-breathe"
              >
                <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden>
                  <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
                </svg>
              </button>
              <div>
                <p className="text-lg font-semibold text-sand-50">{it.play}</p>
                <p className="mt-1 text-sm text-sand-200/80">{it.duration}</p>
                {silentOnly && <p className="mt-2 max-w-sm text-xs text-gold-300">{it.noVoice}</p>}
              </div>
            </div>
          )}

          {phase === "ended" && (
            <div className="pattern-gold absolute inset-0 flex animate-fadeUp flex-col items-center justify-center bg-navy-950/90 px-6 text-center backdrop-blur-md">
              <StarMark size={34} className="text-gold-300" />
              <p className="mt-4 font-display text-6xl font-bold leading-none text-sand-50 sm:text-7xl">مَعنى</p>
              <p className="mt-4 max-w-md text-base text-sand-200 sm:text-lg">{it.endLine}</p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link ref={ctaRef} href="/analyze/" onClick={close} className="btn-accent px-10 py-3.5 text-base">
                  {it.cta}
                </Link>
                <button type="button" onClick={play} className="btn px-5 text-sm text-sand-100 ring-1 ring-sand-50/25 hover:bg-sand-50/10 focus-visible:ring-gold-300/60">
                  ↻ {it.replay}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center gap-3">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-sand-50/15" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
            <div className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-gold-300 transition-[width] duration-700 ease-out" style={{ width: `${progress * 100}%` }} />
          </div>
          {!silentOnly && (
            <button
              type="button"
              onClick={toggleMute}
              aria-pressed={muted}
              aria-label={muted ? it.unmute : it.mute}
              title={muted ? it.unmute : it.mute}
              className="flex h-9 w-9 items-center justify-center rounded-full text-sand-100 ring-1 ring-sand-50/25 transition hover:bg-sand-50/10 focus:outline-none focus-visible:ring-gold-300/60"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" fill="currentColor" stroke="none" />
                {muted ? <path d="M16 9.5l5 5M21 9.5l-5 5" /> : <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />}
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Subtitle({ text }: { text: string }) {
  const parts = text.split("«مَعنى»");
  return (
    <>
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 && <span className="font-display font-bold text-gold-300">«مَعنى»</span>}
          {p}
        </span>
      ))}
    </>
  );
}

function IntroScene() {
  const arch = (cx: number, w: number, spring: number, apex: number, bottom: number) =>
    `M${cx - w} ${bottom}V${spring}C${cx - w} ${spring - (spring - apex) * 0.55} ${cx - w * 0.3} ${apex + 18} ${cx} ${apex}` +
    `C${cx + w * 0.3} ${apex + 18} ${cx + w} ${spring - (spring - apex) * 0.55} ${cx + w} ${spring}V${bottom}Z`;

  return (
    <svg className="intro-anim absolute inset-0 h-full w-full" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <defs>
        <linearGradient id="in-wall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0c1a3a" />
          <stop offset="1" stopColor="#13254d" />
        </linearGradient>
        <linearGradient id="in-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0b2f3a" />
          <stop offset="0.6" stopColor="#0f5e50" />
          <stop offset="1" stopColor="#dcc18a" />
        </linearGradient>
        <linearGradient id="in-floor" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ebe3d3" />
          <stop offset="1" stopColor="#c9bca3" />
        </linearGradient>
        <radialGradient id="in-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#f3e6c6" stopOpacity="0.9" />
          <stop offset="1" stopColor="#f3e6c6" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="in-halo" cx="0.5" cy="0.45" r="0.55">
          <stop offset="0" stopColor="#1b8a74" stopOpacity="0.28" />
          <stop offset="1" stopColor="#1b8a74" stopOpacity="0" />
        </radialGradient>
        <pattern id="in-lattice" width="44" height="44" patternUnits="userSpaceOnUse">
          <g fill="none" stroke="#dcc18a" strokeOpacity="0.35" strokeWidth="1.4">
            <rect x="12" y="12" width="20" height="20" />
            <rect x="12" y="12" width="20" height="20" transform="rotate(45 22 22)" />
            <path d="M0 0L8 8M44 0L36 8M0 44L8 36M44 44L36 36" />
          </g>
        </pattern>
        <pattern id="in-tiles" width="60" height="60" patternUnits="userSpaceOnUse">
          <g fill="none" stroke="#977535" strokeOpacity="0.18" strokeWidth="1">
            <rect x="15" y="15" width="30" height="30" transform="rotate(45 30 30)" />
            <circle cx="30" cy="30" r="4" />
          </g>
        </pattern>
      </defs>

      <rect width="1600" height="900" fill="url(#in-wall)" />
      <rect width="1600" height="900" fill="url(#in-tiles)" opacity="0.5" />

      <path d={arch(800, 250, 330, 70, 760)} fill="url(#in-sky)" />
      <g fill="#081126" opacity="0.85">
        <path d="M640 760V600h320v160z" />
        <path d="M680 600c0-90 55-150 120-165 65 15 120 75 120 165z" />
        <rect x="796" y="405" width="8" height="34" />
        <circle cx="800" cy="400" r="7" />
        <rect x="1000" y="470" width="26" height="290" />
        <path d="M994 470h38l-19-46z" />
        <rect x="992" y="540" width="42" height="10" />
      </g>
      <circle cx="905" cy="190" r="26" fill="#f3e6c6" opacity="0.9" />
      <circle cx="917" cy="182" r="24" fill="#0b3a40" />
      <path d={arch(800, 250, 330, 70, 760)} fill="none" stroke="#dcc18a" strokeOpacity="0.55" strokeWidth="6" />
      <path d={arch(800, 272, 330, 46, 760)} fill="none" stroke="#dcc18a" strokeOpacity="0.2" strokeWidth="2" />

      {[260, 1340].map((cx) => (
        <g key={cx}>
          <path d={arch(cx, 150, 360, 170, 760)} fill="#081126" opacity="0.7" />
          <path d={arch(cx, 150, 360, 170, 760)} fill="url(#in-lattice)" />
          <path d={arch(cx, 150, 360, 170, 760)} fill="none" stroke="#dcc18a" strokeOpacity="0.4" strokeWidth="4" />
        </g>
      ))}

      {[470, 1130].map((x) => (
        <g key={x}>
          <rect x={x - 22} y="250" width="44" height="510" fill="#1d3363" />
          <rect x={x - 32} y="240" width="64" height="18" rx="4" fill="#2c4479" />
          <rect x={x - 32} y="742" width="64" height="18" rx="4" fill="#2c4479" />
        </g>
      ))}

      <rect y="760" width="1600" height="140" fill="url(#in-floor)" />
      <rect y="760" width="1600" height="140" fill="url(#in-tiles)" />
      <rect y="756" width="1600" height="6" fill="#b48f45" opacity="0.6" />

      <ellipse cx="800" cy="520" rx="420" ry="360" fill="url(#in-halo)" />

      {[
        { x: 470, len: 120, s: 1 },
        { x: 1130, len: 150, s: 0.9 },
        { x: 140, len: 90, s: 0.75 },
        { x: 1460, len: 80, s: 0.75 },
      ].map(({ x, len, s }, i) => (
        <g key={x} className="intro-sway" style={{ transformOrigin: `${x}px 0px`, animationDelay: `${i * -1.3}s` }}>
          <line x1={x} y1="0" x2={x} y2={len} stroke="#b48f45" strokeWidth="2" />
          <g transform={`translate(${x} ${len}) scale(${s})`}>
            <circle cx="0" cy="46" r="70" fill="url(#in-glow)" className="intro-glow" />
            <path d="M-8 0h16l6 14h-28z" fill="#b48f45" />
            <path d="M-22 14h44l8 30-8 34h-44l-8-34z" fill="#f3e6c6" opacity="0.9" />
            <path d="M-22 14h44l8 30-8 34h-44l-8-34z" fill="none" stroke="#977535" strokeWidth="2.5" />
            <path d="M0 14v64M-30 44h60" stroke="#977535" strokeWidth="1.5" />
            <path d="M-14 78h28l-6 12h-16z" fill="#b48f45" />
          </g>
        </g>
      ))}
    </svg>
  );
}

function GuideAvatar({ speaking }: { speaking: boolean }) {
  return (
    <svg className={`intro-anim h-full w-auto max-w-full ${speaking ? "is-speaking" : ""}`} viewBox="0 0 400 520" aria-hidden>
      <defs>
        <linearGradient id="av-cloth" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#e6dfd1" />
        </linearGradient>
        <linearGradient id="av-thobe" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fbf8f2" />
          <stop offset="1" stopColor="#e2dac9" />
        </linearGradient>
        <linearGradient id="av-skin" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e2b893" />
          <stop offset="1" stopColor="#cf9f7a" />
        </linearGradient>
      </defs>

      <g className="intro-breathe">
        <path d="M30 520C30 440 80 392 160 372h80c80 20 130 68 130 148z" fill="url(#av-thobe)" />
        <path d="M120 400c-10 40-14 80-14 120M280 400c10 40 14 80 14 120" stroke="#d8cfbd" strokeWidth="2" fill="none" />

        <path d="M150 230h100l8 150H142z" fill="#d9d0be" />
        <path d="M172 290h56v80c-10 10-46 10-56 0z" fill="#c9966f" />
        <path d="M172 290h56v26c-18 10-38 10-56 0z" fill="#b8835e" />
        <path d="M146 342h108l12 40H134z" fill="url(#av-thobe)" />
        <path d="M166 336q34 22 68 0v12q-34 22-68 0z" fill="#fbf8f2" stroke="#d8cfbd" strokeWidth="1.5" />
        <path d="M200 358v130" stroke="#d8cfbd" strokeWidth="2" />
        <circle cx="200" cy="380" r="3" fill="#cfc4ae" />
        <circle cx="200" cy="404" r="3" fill="#cfc4ae" />

        <g className="intro-head">
          <path
            d="M200 58C126 58 106 122 104 196c-2 66-12 130-44 222 30 18 76 24 104 18-6-70-10-130-10-186h92c0 56-4 116-10 186 28 6 74 0 104-18-32-92-42-156-44-222C294 122 274 58 200 58z"
            fill="url(#av-cloth)"
          />
          <path d="M112 250c-6 60-18 110-36 160M128 260c-2 56-8 110-18 168M288 250c6 60 18 110 36 160M272 260c2 56 8 110 18 168" stroke="#ddd5c4" strokeWidth="2" fill="none" />

          <ellipse cx="200" cy="216" rx="58" ry="76" fill="url(#av-skin)" />

          <path d="M146 226c4 40 26 66 54 66s50-26 54-66c-6 16-14 26-24 32-10-4-20-6-30-6s-20 2-30 6c-10-6-18-16-24-32z" fill="#3a2a1f" opacity="0.62" />

          <path d="M160 180q16-9 30-2M210 178q14-7 30 2" stroke="#2b1d14" strokeWidth="4.5" strokeLinecap="round" fill="none" />

          <g className="intro-blink">
            <path d="M162 198q13-10 26 0q-13 8-26 0z" fill="#fbf8f2" />
            <path d="M212 198q13-10 26 0q-13 8-26 0z" fill="#fbf8f2" />
            <circle cx="175" cy="198" r="5" fill="#3a2618" />
            <circle cx="225" cy="198" r="5" fill="#3a2618" />
            <circle cx="176.5" cy="196.5" r="1.4" fill="#fff" />
            <circle cx="226.5" cy="196.5" r="1.4" fill="#fff" />
          </g>

          <path d="M200 204c-2 14-6 24-10 30 6 4 14 4 20 0" stroke="#a87553" strokeWidth="2.2" strokeLinecap="round" fill="none" />

          <path d="M186 254q14 6 28 0" stroke="#6b3a2c" strokeWidth="2.6" strokeLinecap="round" fill="none" />
          <ellipse className="intro-mouth" cx="200" cy="256" rx="11" ry="6" fill="#5a2a22" />

          <path d="M178 246c8-6 16-6 22-2 6-4 14-4 22 2-6 4-14 6-22 4-8 2-16 0-22-4z" fill="#2b1d14" />

          <path d="M126 178c6-30 36-46 74-48 38 2 68 18 74 48v-58c-12-44-136-44-148 0z" fill="url(#av-cloth)" />
          <path d="M126 172c2 60 10 104 22 150l-24 6c-12-50-16-100-14-154zM274 172c-2 60-10 104-22 150l24 6c12-50 16-100 14-154z" fill="url(#av-cloth)" />
          <path d="M132 176c10-26 38-38 68-40 30 2 58 14 68 40" stroke="#d8cfbd" strokeWidth="2" fill="none" />

          <path d="M126 112q74-26 148 0" fill="none" stroke="#1f1f1f" strokeWidth="5" />
          <path d="M120 120q80 30 160 0" fill="none" stroke="#141414" strokeWidth="8" strokeLinecap="round" />
          <path d="M124 108q76 28 152 0" fill="none" stroke="#141414" strokeWidth="7" strokeLinecap="round" />
        </g>
      </g>
    </svg>
  );
}

export function shouldAutoOpenIntro(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) !== "1";
  } catch {
    return false;
  }
}
