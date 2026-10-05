import { strings } from "./i18n";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export type GapStatus = "understood" | "partial_gap" | "major_gap" | "insufficient_evidence";
export type Stage = "awaiting_response" | "gap_detected" | "awaiting_retest" | "completed" | "abstained" | "processing";
export type GapType =
  | "correct_understanding"
  | "missing_intended_meaning"
  | "distorted_meaning"
  | "concept_confusion"
  | "ambiguity_triggered";
export type Resolution = "resolved" | "partially_resolved" | "remains";
export type Strategy = "simplification" | "comparison" | "example" | "visual" | "step_by_step";

export interface RetrievedChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  text_ar: string;
  evidence_id: string;
  relevance_score: number;
  metadata: {
    source_name: string;
    source_name_ar: string;
    topic: string;
    reference: string;
    reference_ar: string;
    language: string;
    review_status: string;
  };
}

export interface IntendedConcept {
  id: string;
  concept: string;
  evidence_from_original_content: string;
  weight: number;
  evidence_ids: string[];
  source_reference: string;
}

export interface BackgroundKnowledge {
  concept: string;
  evidence_ids: string[];
  evidence_quote: string;
  source_reference: string;
}

export interface Ambiguity {
  phrase: string;
  risk: string;
  possible_misunderstanding: string;
  evidence_ids: string[];
  evidence_quote: string;
  source_reference: string;
}

export interface MeaningAnalysis {
  topic: string;
  intended_concepts: IntendedConcept[];
  background_knowledge: BackgroundKnowledge[];
  potential_ambiguities: Ambiguity[];
  understanding_question: string;
}

export interface Interpretation {
  user_interpretation: string[];
  concepts_expressed: string[];
  unclear_points: string[];
  possible_misinterpretations: string[];
  confidence: number;
}

export interface Evidence {
  evidence_id: string;
  source_name: string;
  source_name_ar?: string;
  reference: string;
  reference_ar?: string;
  topic: string;
  supporting_text: string;
  supporting_text_ar?: string;
  relevance_score: number;
  verified_quote?: string;
}

export interface ConceptResult {
  concept_id: string;
  concept: string;
  weight: number;
  gap_type: GapType;
  user_understanding: string;
  explanation: string;
  evidence_ids: string[];
}

export interface Misunderstanding {
  user_understood: string;
  gap_type: "distorted_meaning" | "concept_confusion" | "ambiguity_triggered";
  accurate_meaning: string;
  why_it_happened: string;
  related_concept_id: string;
  confused_with: string;
  evidence_ids: string[];
  evidence_quote: string;
  source_reference: string;
}

export interface Verification {
  status: GapStatus;
  alignment_score: number;
  primary_gap_type: GapType | "insufficient_evidence";
  concept_results: ConceptResult[];
  what_arrived: string[];
  missing: string[];
  misunderstandings: Misunderstanding[];
  unverified_concepts: string[];
  rejected_claims: { claim: string; reason: string }[];
  evidence: Evidence[];
  gap_explanation: string;
  previous_resolution: { user_understood: string; status: Resolution; note: string }[];
  confidence: number;
}

export interface Refinement {
  root_cause: string;
  diagnosis: string;
  strategy: Strategy;
  strategy_reason: string;
  strategy_adjusted: boolean;
  improved_content: string;
  comparison_left_label: string;
  comparison_right_label: string;
  comparison_rows: { aspect: string; left: string; right: string }[];
  steps: string[];
  example: string;
  visual_nodes: { label: string; detail: string }[];
  changes: { original_issue: string; improvement: string; reason: string }[];
  evidence_ids: string[];
  evidence_quotes: string[];
  explanation_text: string;
}

export interface RetrievalDecision {
  doc_id: string;
  topic: string;
  reference: string;
  reference_ar?: string;
  score: number;
  decision: string;
  note: string;
}

export interface ValidationEntry {
  agent: string;
  stage?: string;
  attempts: number;
  issues_first: string[];
  issues_final: string[];
  corrections: string[];
}

export interface FinalResult {
  outcome: "understood_first_time" | "retested" | "abstained";
  status_before?: GapStatus;
  status_after?: GapStatus;
  before_score?: number;
  after_score?: number;
  improvement_points?: number;
  resolution?: Resolution | null;
  gaps_detected?: string[];
  resolved_gaps?: string[];
  partially_resolved_gaps?: string[];
  remaining_gaps?: string[];
  root_cause?: string | null;
  explanation_strategy?: Strategy | null;
  sources_used?: Evidence[];
  message?: string;
  reason?: string;
}

export interface SessionView {
  session_id: string;
  stage: Stage;
  original_content: string;
  content_language: string;
  target_language: string;
  rag_context?: RetrievedChunk[];
  rag_queries?: string[];
  rag_topics?: string[];
  rag_primary_topic?: string;
  rag_key_terms?: string[];
  rag_decisions?: RetrievalDecision[];
  meaning_analysis?: MeaningAnalysis;
  understanding_question?: string;
  user_response?: string;
  user_interpretation?: Interpretation;
  verification?: Verification;
  refinement?: Refinement;
  refined_content?: string;
  explanation_text?: string;
  follow_up_question?: string;
  follow_up_response?: string;
  second_interpretation?: Interpretation;
  second_verification?: Verification;
  before_score?: number;
  after_score?: number;
  final_result?: FinalResult;
  abstention?: { message: string; stage: string; reason: string; reason_code: string };
  validation_log?: ValidationEntry[];
}

export interface Progress {
  active: string | null;
  completed: string[];
  error: string | null;
}

export interface Dashboard {
  content_sessions: number;
  sessions_with_gaps: number;
  meaning_gaps_detected: number;
  meaning_gaps_resolved: number;
  abstentions: number;
  average_before_alignment: number | null;
  average_after_alignment: number | null;
  most_misunderstood_concepts: { concept: string; count: number }[];
  gaps_by_topic: { topic: string; count: number }[];
  explanation_strategies: { strategy: string; count: number }[];
  before_after: { session_id: string; topic: string | null; before: number; after: number; created_at: string }[];
}

export interface EvaluationCase {
  id: string;
  category: string;
  content: string;
  language: string;
  user_response: string;
  expected_status: string[];
  status: string | null;
  status_ok: boolean;
  gap_type: string | null;
  root_cause: string | null;
  strategy: string | null;
  before: number | null;
  after: number | null;
  resolution: Resolution | null;
  error: string | null;
}

export interface Evaluation {
  generated_at: string;
  metrics: Record<string, number | null>;
  categories: Record<string, { n: number; status_accuracy: number | null }>;
  cases: EvaluationCase[];
}

export interface Health {
  status: string;
  llm_configured: boolean;
  vector_index_ready: boolean;
  app_env: string;
  review_filter: string[];
}

export interface SourceCollection {
  id: string;
  name: string;
  name_ar: string;
  license: string;
  attribution: string;
  homepage: string;
  count: number;
}

export interface SourcesResponse {
  collections: SourceCollection[];
  total: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const t = strings;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new Error(t.common.backendDown);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = (await res.json()).detail;
    } catch {}
    throw new Error(typeof detail === "string" && detail ? detail : t.common.unexpected);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/api/health"),
  sources: () => request<SourcesResponse>("/api/sources"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  evaluation: () => request<Evaluation>("/api/evaluation"),
  session: (id: string) => request<SessionView>(`/api/session/${id}`),
  progress: (id: string) => request<Progress>(`/api/session/${id}/progress`),
  analyzeContent: (body: { session_id: string; content: string; content_language: string; target_language: string }) =>
    post<SessionView>("/api/content/analyze", body),
  analyzeUnderstanding: (session_id: string, response: string) =>
    post<SessionView>("/api/understanding/analyze", { session_id, response }),
  refine: (session_id: string) => post<SessionView>("/api/content/refine", { session_id }),
  retest: (session_id: string, response: string) => post<SessionView>("/api/understanding/retest", { session_id, response }),
};

export function newSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID().replace(/-/g, "");
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export const pct = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 100)}%`);

