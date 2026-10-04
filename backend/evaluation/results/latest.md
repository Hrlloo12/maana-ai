# MA'NA evaluation: full (openai:gpt-4.1)

Generated: 2026-10-04T17:01:01+00:00

| Metric | Value |
|---|---|
| Intended Concept Extraction (recall of expected meanings) | 100.0% |
| Background leakage into intended meaning (lower is better) | 0.0% |
| Meaning Gap Detection Accuracy (status) | 100.0% |
| Gap Type Accuracy | 95.5% |
| RAG scope gate accuracy (in scope vs. out of scope) | 100.0% |
| RAG Relevance (precision of kept evidence) | 100.0% |
| Irrelevant retrieval rejected (out-of-scope content) | 100.0% |
| Citation Correctness | 100.0% |
| Unsupported Claim Rate (lower is better) | 0.0% |
| Abstention Accuracy | 100.0% |
| Abstention precision | 100.0% |
| Abstention recall | 100.0% |
| Refinement: strategy fits the cause | 100.0% |
| Refinement Relevance (explanation covers the gap) | 100.0% |
| Before/After: misunderstanding resolved or partially resolved | 100.0% |
| Mean alignment before | 0.083 |
| Mean alignment after | 0.917 |
| Mean improvement (points) | 83.3 |
| Agent outputs valid on first attempt | 96.1% |
| Agent outputs valid after correction | 99.0% |
| n cases | 26 |
| n errors | 0 |
| n retested | 12 |
| n citations | 96 |
| n claims | 74 |
| guard rejections | 1 |

| Category | Cases | Status accuracy |
|---|---|---|
| ambiguous_content | 3 | 100.0% |
| before_after_no_improvement | 1 | 100.0% |
| broader_coverage | 2 | 100.0% |
| concept_confusion | 2 | 100.0% |
| correct_abstention | 2 | 100.0% |
| correct_understanding | 4 | 100.0% |
| english_source_content | 1 | 100.0% |
| irrelevant_rag_retrieval | 2 | 100.0% |
| omits_background_knowledge | 1 | 100.0% |
| partial_understanding | 3 | 100.0% |
| unsupported_claim_guard | 1 | 100.0% |
| wrong_understanding | 4 | 100.0% |
