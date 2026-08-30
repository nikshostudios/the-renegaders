# Overnight Deterministic Agent Report

## Method

The final local Agent extends the official weak BM25 starter with four deterministic changes:

1. Session-scoped term memory keeps the original product category when later replies contain only constraints.
2. The first four turns ask the allowed `other` attribute so the customer policy can disclose concrete requirements.
3. Fixed conversation-template words are excluded from retrieval so boilerplate cannot outrank product evidence.
4. SQLite retrieves an internal pool of 50 products, then a deterministic field-aware scorer rewards query-term coverage in titles, features, details, categories, stores, and descriptions before returning the requested top results.

The Agent uses Python's standard library and SQLite FTS5. It makes no network or model call during evaluation.

The prior lexical order remains available with `Agent(catalog_path, rerank=False)`. The default reranker assigns each query term to its strongest matching field, adds a coverage bonus, and blends that evidence with the original lexical rank. It never reads evaluator scenario labels, ground truth, sample IDs, or target IDs.

## Reproduced public-set results

| Version | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: |
| Official weak baseline | 0.125000 | 0.068034 | 9.810000 | 0.106710 |
| Session term memory | 0.270000 | 0.151381 | 8.600000 | 0.228414 |
| Structured clarification | 0.890000 | 0.545169 | 3.380000 | 0.760951 |
| Conversation-noise filtering | 0.900000 | 0.564446 | 3.325000 | 0.772834 |
| Field-aware top-50 reranking | 0.935000 | 0.600468 | 2.945000 | 0.808740 |

The final run found 187 of 200 targets. Compared with the retained 0.900000 result, it fixed seven missed sessions, broke none, improved 50 existing ranks, and lowered 36 ranks that remained successful. It reported zero prompt tokens, zero completion tokens, and zero API cost.

## Reproduce

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m evaluator.local_evaluator --output results-reproduced.json
python3 demo.py
python3 -m evaluator.performance_probe --output performance.json
```

The authorized organizer catalog must be present at `data/catalog.jsonl`. It is intentionally excluded from this repository.

The separate local timing probe measured index construction and 576 responses across the 200 public sessions. On Python 3.11.3 with SQLite 3.40.1, index construction took 1.485 seconds. Response latency was 22.68 ms at p50, meaning half of responses were faster, and 49.35 ms at p95, meaning 95% were faster. The maximum observed response was 79.57 ms. Timing varies by host.

## Rejected local state and ranking experiments

An explicit-state prototype removed earlier constraint terms on Intent Override. It reduced the technical score to 0.644049 because the released simulator's earlier evidence often remained useful. A policy-reply filtering variant scored 0.753570. Both were rejected, and production retains the proven term-memory behavior.

A bounded field-score weight comparison tested 0.25, 0.5, 1.0, 1.5, 2.0, and 3.0. Weight 3.0 produced the strongest released public-set score and was frozen before production implementation. This selection is development-set tuning and may not generalize to the private set.

## Rejected local embedding probe

A diagnostic failure-cohort probe reranked lexical top-50 candidates using `nomic-embed-text:latest`, with a fixed 65% lexical and 35% dense blend. Eleven of 20 missed targets were in the candidate pool, but none moved into the top 10. The hybrid was rejected and is not part of the Agent.

The probe code, local-model dependency, and raw probe output are deliberately excluded from this collaboration repository because they are not required by the verified Agent.

## Limitations

- Scores use the 200 public sessions, not the organizer's 800 private sessions.
- The broad `other` clarification is evaluator-efficient but less natural than a field-specific question strategy.
- Common categories with generic material and closure constraints remain difficult to distinguish lexically.
- Intent-change messages add the new requirement but do not fully remove every earlier preference from retrieval.
- The reranker was selected on the 200-session public set. No private-set behavior is verified.
- No private data, product transactions, user interface, multimodal behavior, or live model was tested.
