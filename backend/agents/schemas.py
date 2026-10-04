from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GapStatus = Literal["understood", "partial_gap", "major_gap", "insufficient_evidence"]
GapType = Literal[
    "correct_understanding",
    "missing_intended_meaning",
    "distorted_meaning",
    "concept_confusion",
    "ambiguity_triggered",
]
EVIDENCE_REQUIRED: set[str] = {"concept_confusion", "ambiguity_triggered"}
MISUNDERSTANDING_TYPES: set[str] = {"distorted_meaning", "concept_confusion", "ambiguity_triggered"}
Resolution = Literal["resolved", "partially_resolved", "remains"]

RootCause = Literal[
    "concept_confusion",
    "ambiguous_wording",
    "abstract_concept",
    "missing_context",
    "complex_process",
    "overgeneralization",
]
Strategy = Literal["simplification", "comparison", "example", "visual", "step_by_step"]

STRATEGY_FIT: dict[str, list[str]] = {
    "concept_confusion": ["comparison"],
    "ambiguous_wording": ["simplification", "comparison", "example"],
    "abstract_concept": ["example", "visual", "simplification"],
    "missing_context": ["simplification", "example", "step_by_step"],
    "complex_process": ["step_by_step", "visual"],
    "overgeneralization": ["example", "comparison", "simplification"],
}


class QueryPlan(BaseModel):
    primary_topic: str = Field(default="", description="ONE topic from the available list, or empty")
    related_topics: list[str] = Field(default_factory=list, description="At most one closely confused topic")
    key_terms: list[str] = Field(default_factory=list, description="Names of the concept (English, transliteration, Arabic)")
    search_queries: list[str] = Field(default_factory=list, description="2-3 short English queries")


class IntendedConcept(BaseModel):
    id: str = Field(default="", description="C1, C2, ...")
    concept: str
    evidence_from_original_content: str = Field(description="Exact words of the original content that carry it")
    weight: float = Field(default=0.0, ge=0.0)
    evidence_ids: list[str] = Field(default_factory=list)
    source_reference: str = ""


class BackgroundKnowledge(BaseModel):
    concept: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str = Field(default="", description="Verbatim sentence copied from the cited evidence")
    source_reference: str = ""


class Ambiguity(BaseModel):
    phrase: str
    risk: str
    possible_misunderstanding: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str = Field(default="", description="Verbatim sentence copied from the cited evidence")
    source_reference: str = ""


class MeaningAnalysis(BaseModel):
    topic: str
    intended_concepts: list[IntendedConcept]
    background_knowledge: list[BackgroundKnowledge] = Field(default_factory=list)
    potential_ambiguities: list[Ambiguity] = Field(default_factory=list)
    understanding_question: str


class UserInterpretation(BaseModel):
    user_interpretation: list[str] = Field(default_factory=list)
    concepts_expressed: list[str] = Field(default_factory=list)
    unclear_points: list[str] = Field(default_factory=list)
    possible_misinterpretations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ConceptJudgement(BaseModel):
    concept_id: str
    gap_type: GapType
    user_understanding: str = ""
    explanation: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str = Field(default="", description="Verbatim sentence from the cited evidence")


class MisunderstandingLLM(BaseModel):
    user_understood: str
    reader_quote: str = Field(default="", description="The reader's own words that express this reading")
    gap_type: Literal["distorted_meaning", "concept_confusion", "ambiguity_triggered"]
    accurate_meaning: str
    why_it_happened: str = ""
    related_concept_id: str = ""
    confused_with: str = Field(default="", description="The other concept the reader equated it with, if any")
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str = Field(default="", description="Verbatim sentence from the cited evidence")


class ResolutionLLM(BaseModel):
    index: int
    status: Resolution
    note: str = ""


class VerificationLLMOutput(BaseModel):
    judgements: list[ConceptJudgement]
    misunderstandings: list[MisunderstandingLLM] = Field(default_factory=list)
    gap_explanation: str = ""
    previous_resolution: list[ResolutionLLM] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    evidence_id: str
    source_name: str
    source_name_ar: str = ""
    reference: str
    reference_ar: str = ""
    topic: str
    supporting_text: str
    relevance_score: float
    verified_quote: str = ""


class ConceptResult(BaseModel):
    concept_id: str
    concept: str
    weight: float
    gap_type: GapType
    user_understanding: str = ""
    explanation: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class Misunderstanding(BaseModel):
    user_understood: str
    gap_type: Literal["distorted_meaning", "concept_confusion", "ambiguity_triggered"]
    accurate_meaning: str
    why_it_happened: str
    related_concept_id: str = ""
    confused_with: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str = ""
    source_reference: str = ""


class ResolutionItem(BaseModel):
    user_understood: str
    status: Resolution
    note: str = ""


class RejectedClaim(BaseModel):
    claim: str
    reason: str


class Verification(BaseModel):
    status: GapStatus
    alignment_score: float = 0.0
    primary_gap_type: GapType | Literal["insufficient_evidence"] = "correct_understanding"
    concept_results: list[ConceptResult] = Field(default_factory=list)
    what_arrived: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    misunderstandings: list[Misunderstanding] = Field(default_factory=list)
    unverified_concepts: list[str] = Field(default_factory=list)
    rejected_claims: list[RejectedClaim] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    gap_explanation: str = ""
    previous_resolution: list[ResolutionItem] = Field(default_factory=list)
    confidence: float = 0.0


class Change(BaseModel):
    original_issue: str
    improvement: str
    reason: str


class ComparisonRow(BaseModel):
    aspect: str
    left: str
    right: str


class VisualNode(BaseModel):
    label: str
    detail: str = ""


class RefinementLLMOutput(BaseModel):
    root_cause: RootCause
    diagnosis: str = Field(description="Why the reader misunderstood, in the report language")
    strategy: Strategy
    strategy_reason: str = Field(description="Why this strategy fits this cause, in the report language")
    improved_content: str = Field(description="The new explanation the reader will read, in the audience language")
    comparison_left_label: str = ""
    comparison_right_label: str = ""
    comparison_rows: list[ComparisonRow] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    example: str = ""
    visual_nodes: list[VisualNode] = Field(default_factory=list)
    changes: list[Change] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)


class RefinementOutput(RefinementLLMOutput):
    strategy_adjusted: bool = False
    explanation_text: str = ""
