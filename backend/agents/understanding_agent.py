from __future__ import annotations

from agents.base import call_validated, report_rule
from agents.schemas import UserInterpretation
from agents.text import normalize

JUDGEMENT_WORDS = ("correct", "incorrect", "wrong", "mistake", "inaccurate", "صحيح", "خاطئ", "خطا", "غلط", "مخطئ")

SYSTEM_PROMPT = """You are the UNDERSTANDING AGENT of MA'NA.

Your ONLY job: describe faithfully what the reader understood, based solely on their answer.

Rules:
- Do NOT judge whether the reader is religiously correct. Never use words such as correct, wrong, mistake
  (or their Arabic equivalents). You are a neutral listener.
- user_interpretation: the meanings the reader expressed, as short statements.
- concepts_expressed: the key ideas or terms the reader explicitly mentioned.
- unclear_points: parts of the answer that are vague or ambiguous.
- possible_misinterpretations: readings the reader appears to infer beyond what they read, or signs they
  equate the term with a different concept (e.g. "the reader describes the giving as a personal choice",
  "the reader appears to equate Hajj with Umrah"). Describe them neutrally.
- Only describe what the reader said. Do not list facts the reader did not mention.
- confidence: how clearly the answer reveals the reader's understanding (0.0-1.0). Very short or evasive
  answers deserve low confidence."""


def validate_understanding(out: UserInterpretation, response: str) -> list[str]:
    issues: list[str] = []
    if len(response.split()) >= 3 and not out.user_interpretation:
        issues.append("user_interpretation is empty although the reader gave an answer.")
    text = normalize(" ".join(out.user_interpretation + out.possible_misinterpretations + out.unclear_points))
    used = [w for w in JUDGEMENT_WORDS if f" {normalize(w)} " in f" {text} "]
    if used:
        issues.append(f"Judgement words used {used}; describe the reader neutrally without judging.")
    return issues


def run_understanding_agent(
    content_read: str, question: str, response: str, language: str
) -> tuple[UserInterpretation, dict]:
    user = f"""CONTENT THE READER READ:
\"\"\"{content_read}\"\"\"

QUESTION ASKED: {question}

READER'S ANSWER ({language}):
\"\"\"{response}\"\"\"

{report_rule()}
Return the interpretation JSON."""
    return call_validated(
        "understanding_agent", SYSTEM_PROMPT, user, UserInterpretation,
        lambda o: validate_understanding(o, response),
    )
