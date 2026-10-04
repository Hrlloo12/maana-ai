# MA'NA evaluation: full (gemini:gemini-3.5-flash-lite)

Generated: 2026-10-03T12:20:17+00:00

| Metric | Value |
|---|---|
| Intended Concept Extraction (recall of expected meanings) | 100.0% |
| Background leakage into intended meaning (lower is better) | 0.0% |
| Meaning Gap Detection Accuracy (status) | 36.0% |
| Gap Type Accuracy | 80.0% |
| RAG topic gate accuracy | 100.0% |
| RAG Relevance (precision of kept evidence) | 100.0% |
| Irrelevant retrieval rejected (out-of-scope content) | n/a |
| Citation Correctness | 100.0% |
| Unsupported Claim Rate (lower is better) | 0.0% |
| Abstention Accuracy | 100.0% |
| Abstention precision | n/a |
| Abstention recall | n/a |
| Refinement: strategy fits the cause | 100.0% |
| Refinement Relevance (explanation covers the gap) | 100.0% |
| Before/After: misunderstanding resolved or partially resolved | 100.0% |
| Mean alignment before | 0.375 |
| Mean alignment after | 1.0 |
| Mean improvement (points) | 62.5 |
| Agent outputs valid on first attempt | 97.6% |
| Agent outputs valid after correction | 100.0% |
| n cases | 25 |
| n errors | 15 |
| n retested | 4 |
| n citations | 45 |
| n claims | 27 |
| guard rejections | 0 |

| Category | Cases | Status accuracy |
|---|---|---|
| ambiguous_content | 3 | 0.0% |
| before_after_no_improvement | 1 | 0.0% |
| concept_confusion | 2 | 0.0% |
| correct_abstention | 2 | 0.0% |
| correct_understanding | 4 | 100.0% |
| english_source_content | 1 | 0.0% |
| insufficient_evidence | 1 | 0.0% |
| irrelevant_rag_retrieval | 2 | 0.0% |
| omits_background_knowledge | 1 | 100.0% |
| partial_understanding | 3 | 100.0% |
| unsupported_claim_guard | 1 | 0.0% |
| wrong_understanding | 4 | 25.0% |

## Cases that missed the expected status

- fasting-correct-en: major_gap (expected ['understood'])
- fasting-sunnah-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- hajj-umrah-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- sadaqah-zakat-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- hajj-umrah-still-confused-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- zakat-charity-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- zakat-sadaqa-word-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- allah-word-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- hajj-tourism-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- hajj-unverifiable-extra-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- evasive-answer-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- prayer-irrelevant: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- pillars-prayer-irrelevant-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- music-abstain-ar: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- inheritance-abstain-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
- halal-food-abstain-en: LLMError: The LLM provider's rate limit or quota was reached (GenerateRequestsPerDayPerProjectPerModel-FreeTier). Wait a minute and try again, or use a key with a higher quota. (expected None)
