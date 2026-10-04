from __future__ import annotations

import re
import unicodedata

_AR_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = _AR_MARKS.sub("", t)
    t = re.sub("[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    t = _PUNCT.sub(" ", t.lower())
    return _SPACES.sub(" ", t).strip()


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def _stem(word: str) -> str:
    for prefix in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            return word[len(prefix):]
    return word


def _stems(text: str) -> list[str]:
    return [_stem(w) for w in tokens(text)]


def token_share(part: str, whole: str) -> float:
    p = _stems(part)
    if not p:
        return 0.0
    w = set(_stems(whole))
    return sum(1 for x in p if x in w) / len(p)


def grounded_in(quote: str, source: str, min_share: float = 0.75) -> bool:
    q, s = normalize(quote), normalize(source)
    if not q:
        return False
    if q in s:
        return True
    return len(q.split()) >= 2 and token_share(quote, source) >= min_share


def quote_supported(quote: str, chunk_text: str) -> bool:
    q = normalize(quote)
    if len(q.split()) < 3:
        return False
    if q in normalize(chunk_text):
        return True
    return len(q.split()) >= 5 and token_share(quote, chunk_text) >= 0.85


def jaccard(a: str, b: str) -> float:
    x, y = set(_stems(a)), set(_stems(b))
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def mentions_any(text: str, terms: list[str]) -> bool:
    body = f" {normalize(text)} "
    stems = set(_stems(text))
    for term in terms:
        t = normalize(term)
        if not t:
            continue
        if f" {t} " in body or (" " not in t and _stem(t) in stems):
            return True
    return False


RESTRICTIVE = ("فقط", "مجرد", "يقتصر", "تقتصر", "يقتصرون", "اقتصار", "حصر", "يحصر", "تنحصر", "لا غير", "ليس الا",
               "only", "merely", "just", "solely", "nothing but", "nothing more")


def adds_restriction(claim: str, said: str) -> bool:
    c, s = f" {normalize(claim)} ", f" {normalize(said)} "
    marks = [normalize(m) for m in RESTRICTIVE]
    return any(f" {m} " in c or (" " not in m and m in c) for m in marks) and not any(f" {m} " in s for m in marks)


YES_NO_STARTS = ("is ", "are ", "does ", "do ", "did ", "can ", "should ", "was ", "هل ", "أليس ", "اليس ")


def is_yes_no_question(question: str) -> bool:
    q = (question or "").strip().lower()
    return q.startswith(YES_NO_STARTS)
