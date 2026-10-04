from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="maana-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.memory import InMemorySaver

from db.database import init_db
from graph.maana_graph import MaanaWorkflow
from llm.client import LLMClient, set_llm
from services.session_service import set_workflow

OUT_OF_SCOPE = ("music", "football", "الموسيقى")
GOOD_ANSWER_MARKERS = ("not optional", "obligatory", "required", "فريضة", "يذهبون إلى مكة", "form of giving",
                       "عبادة")


def _is_hajj(text: str) -> bool:
    return "الحج" in text or "hajj" in text.lower()


def evidence_quotes(prompt: str) -> dict[str, str]:
    quotes = {}
    for eid, text in re.findall(r"\[(E\d+)\] source:[^\n]*\n([^\n]+)", prompt):
        quotes[eid] = re.split(r"(?<=[.!?؟])\s+", text.strip())[0]
    return quotes


class FakeBackend:
    def __init__(self, invent_citation: bool = False, unsourced_confusion: bool = False,
                 ungrounded_concept: bool = False, bad_strategy: bool = False, irrelevant_grades: bool = False,
                 empty_payload: bool = False):
        self.calls: list[str] = []
        self.invent_citation = invent_citation
        self.unsourced_confusion = unsourced_confusion
        self.ungrounded_concept = ungrounded_concept
        self.bad_strategy = bad_strategy
        self.irrelevant_grades = irrelevant_grades
        self.empty_payload = empty_payload

    def chat(self, system: str, user: str, json_mode: bool) -> str:
        quotes = evidence_quotes(user)
        evidence = list(quotes)
        if "retrieval planner" in system:
            self.calls.append("planner")
            content = user.split("CONTENT:", 1)[1]
            if any(w in content.lower() for w in OUT_OF_SCOPE):
                return json.dumps({"primary_topic": "", "related_topics": [], "key_terms": [], "search_queries": []})
            if _is_hajj(content):
                return json.dumps({"primary_topic": "hajj", "related_topics": [], "key_terms": ["hajj", "الحج"],
                                   "search_queries": ["hajj pilgrimage makkah", "hajj umrah difference", "الحج"]})
            return json.dumps({"primary_topic": "zakat", "related_topics": ["sadaqah"],
                               "key_terms": ["zakat", "zakah", "الزكاة"],
                               "search_queries": ["zakat obligation pillar", "zakat charity", "الزكاة"]})
        if "relevance grader" in system:
            self.calls.append("grader")
            n = len(re.findall(r"^\[(\d+)\] ", user, re.MULTILINE))
            return json.dumps({"grades": [{"passage": i, "relevant": not self.irrelevant_grades, "reason": "test"}
                                          for i in range(1, n + 1)]})
        if "MEANING AGENT" in system:
            self.calls.append("meaning")
            content = user.split('"""', 2)[1]
            first = evidence[:1]
            quote = quotes[first[0]] if first else ""
            if _is_hajj(content):
                intended = [{"concept": "الحج رحلة المسلمين إلى مكة",
                             "evidence_from_original_content": "رحلة يقوم بها المسلمون إلى مكة", "weight": 1.0,
                             "evidence_ids": first}]
                background = [{"concept": "الحج فريضة على المستطيع", "evidence_ids": first, "evidence_quote": quote}]
                amb = [{"phrase": "رحلة", "risk": "قد تُفهم رحلة عادية", "possible_misunderstanding": "العمرة",
                        "evidence_ids": first, "evidence_quote": quote}]
            else:
                ids = first + (["E99"] if self.invent_citation else [])
                intended = [
                    {"concept": "الزكاة نوع من العطاء", "evidence_from_original_content": "a form of charity",
                     "weight": 3, "evidence_ids": ids},
                    {"concept": "الزكاة جزء من الإسلام", "evidence_from_original_content": "in Islam",
                     "weight": 1, "evidence_ids": []},
                ]
                if self.ungrounded_concept:
                    intended.append({"concept": "الزكاة فريضة لها نصاب",
                                     "evidence_from_original_content": "obligatory once nisab is reached",
                                     "weight": 1, "evidence_ids": first})
                background = [{"concept": "الزكاة فريضة بشروط", "evidence_ids": ids, "evidence_quote": quote}]
                if self.invent_citation:
                    background.append({"concept": "ادعاء بلا مصدر", "evidence_ids": ["E99"],
                                       "evidence_quote": "this sentence is not in any source"})
                amb = [{"phrase": "charity", "risk": "توحي بالتطوع", "possible_misunderstanding": "اختيارية",
                        "evidence_ids": first, "evidence_quote": quote}]
            return json.dumps({"topic": "الحج" if _is_hajj(content) else "الزكاة", "intended_concepts": intended,
                               "background_knowledge": background, "potential_ambiguities": amb,
                               "understanding_question": "بكلماتك الخاصة، ماذا فهمت من هذا المحتوى؟"})
        if "UNDERSTANDING AGENT" in system:
            self.calls.append("understanding")
            return json.dumps({"user_interpretation": ["إعطاء المال"], "concepts_expressed": ["تبرع"],
                               "unclear_points": [], "possible_misinterpretations": [], "confidence": 0.8})
        if "VERIFICATION AGENT" in system:
            self.calls.append("verification")
            answer = user.split("READER'S ANSWER", 1)[1].split("READER'S INTERPRETATION", 1)[0]
            concept_ids = re.findall(r"^- (C\d+) \(weight", user, re.MULTILINE)
            first = evidence[:1]
            quote = "" if self.unsourced_confusion else (quotes[first[0]] if first else "")
            judgements, misunderstandings = [], []
            confused = "العمرة" in answer and "ليس" not in answer
            optional = any(w in answer.lower() for w in ("optional", "choose", "اختيار")) and "not optional" not in answer.lower()
            good = any(m in answer.lower() for m in GOOD_ANSWER_MARKERS) and not confused and not optional
            for cid in concept_ids:
                if confused:
                    gap, ids = "concept_confusion", first
                elif optional and cid == "C1":
                    gap, ids = "ambiguity_triggered", first
                elif good or cid != "C1":
                    gap, ids = "correct_understanding", []
                else:
                    gap, ids = "missing_intended_meaning", []
                judgements.append({"concept_id": cid, "gap_type": gap, "user_understanding": answer.strip()[:40],
                                   "explanation": "اختبار", "evidence_ids": ids,
                                   "evidence_quote": quote if ids else ""})
            if confused:
                misunderstandings.append({"user_understood": "الحج هو العمرة", "gap_type": "concept_confusion",
                                          "reader_quote": answer.strip().strip('"').strip()[:60],
                                          "accurate_meaning": "الحج والعمرة عبادتان مختلفتان",
                                          "why_it_happened": "كلمة رحلة لا تميز بينهما",
                                          "related_concept_id": "C1", "confused_with": "العمرة",
                                          "evidence_ids": first, "evidence_quote": quote})
            if optional:
                misunderstandings.append({"user_understood": "الزكاة اختيارية", "gap_type": "ambiguity_triggered",
                                          "reader_quote": answer.strip().strip('"').strip()[:60],
                                          "accurate_meaning": "الزكاة فريضة",
                                          "why_it_happened": "كلمة charity توحي بالتطوع",
                                          "related_concept_id": "C1", "evidence_ids": first, "evidence_quote": quote})
            previous = []
            if "PREVIOUS MISUNDERSTANDINGS" in user:
                previous = re.findall(r"^(\d+)\. ", user.split("PREVIOUS MISUNDERSTANDINGS", 1)[1], re.MULTILINE)
            resolution = [{"index": int(i), "status": "resolved" if good else "remains"} for i in previous]
            return json.dumps({"judgements": judgements, "misunderstandings": misunderstandings,
                               "gap_explanation": "ملخص اختبار", "previous_resolution": resolution, "confidence": 0.9})
        if "complete one part of an explanation" in system:
            self.calls.append("payload")
            return json.dumps({"comparison_left_label": "الحج", "comparison_right_label": "العمرة",
                               "comparison_rows": [{"aspect": "الوقت", "left": "أشهر معلومات", "right": "طوال العام"},
                                                   {"aspect": "الحكم", "left": "ركن", "right": "عبادة مستقلة"}]})
        if "REFINEMENT AGENT" in system:
            self.calls.append("refinement")
            quote = quotes[evidence[0]] if evidence else ""
            confusion = "concept_confusion" in user.split("ALLOWED ROOT CAUSES", 1)[1].split("\n", 1)[0]
            if self.bad_strategy:
                body = {"root_cause": "concept_confusion" if confusion else "ambiguous_wording",
                        "strategy": "example", "example": ""}
            elif confusion and self.empty_payload:
                body = {"root_cause": "concept_confusion", "strategy": "comparison"}
            elif confusion:
                body = {"root_cause": "concept_confusion", "strategy": "comparison",
                        "comparison_left_label": "الحج", "comparison_right_label": "العمرة",
                        "comparison_rows": [{"aspect": "الوقت", "left": "أشهر معلومات", "right": "طوال العام"},
                                            {"aspect": "الحكم", "left": "ركن", "right": "عبادة مستقلة"}]}
            else:
                body = {"root_cause": "ambiguous_wording", "strategy": "simplification"}
            return json.dumps({
                **body,
                "diagnosis": "تشخيص اختبار", "strategy_reason": "سبب اختبار",
                "improved_content": "الحج عبادة يقصد فيها المسلمون مكة في وقت محدد." if confusion
                else "Zakat is an obligatory form of giving in Islam.",
                "changes": [{"original_issue": "charity", "improvement": "obligatory", "reason": "evidence"}],
                "evidence_ids": evidence[:1], "evidence_quotes": [quote] if quote else [],
            })
        raise AssertionError(f"Unexpected prompt: {system[:80]}")


@pytest.fixture()
def fake_llm():
    backend = FakeBackend()
    set_llm(LLMClient(backend))
    return backend


@pytest.fixture()
def workflow(fake_llm):
    init_db()
    wf = MaanaWorkflow(checkpointer=InMemorySaver())
    set_workflow(wf)
    return wf
