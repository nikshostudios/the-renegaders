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

The separate local timing probe measured index construction and 576 responses
across the 200 public sessions. On Python 3.11.3 with SQLite 3.40.1, one run
measured a 1.485-second index build, 22.68 ms p50, 49.35 ms p95, and 79.57 ms
maximum. A later verification run measured a 2.654-second index build, 46.49 ms
p50, 179.66 ms p95, and a 1,082.22 ms maximum outlier while preserving the
0.808740 technical score. Timing varies materially with host load, so these are
feasibility measurements rather than guarantees.

## Rejected local state and ranking experiments

An explicit-state prototype removed earlier constraint terms on Intent Override. It reduced the technical score to 0.644049 because the released simulator's earlier evidence often remained useful. A policy-reply filtering variant scored 0.753570. Both were rejected, and production retains the proven term-memory behavior.

A bounded field-score weight comparison tested 0.25, 0.5, 1.0, 1.5, 2.0, and 3.0. Weight 3.0 produced the strongest released public-set score and was frozen before production implementation. This selection is development-set tuning and may not generalize to the private set.

## Rejected local embedding probe

A diagnostic failure-cohort probe reranked lexical top-50 candidates using `nomic-embed-text:latest`, with a fixed 65% lexical and 35% dense blend. Eleven of 20 missed targets were in the candidate pool, but none moved into the top 10. The hybrid was rejected and is not part of the Agent.

The probe code, local-model dependency, and raw probe output are deliberately excluded from this collaboration repository because they are not required by the verified Agent.

## Post-freeze challenge experiments

After the 0.808740 result was selected, the 13 remaining misses were traced through a deeper 500-product pool. Every target remained lexically retrievable. Six reached reranked positions 11 to 50 and seven reached positions 51 to 500.

Four isolated follow-up checks did not beat the frozen Agent:

| Experiment | Technical score | Fixed misses | Broken hits | Decision |
| --- | ---: | ---: | ---: | --- |
| Candidate pool 100 | 0.808740 | 0 | 0 | Reject, no session changed |
| Candidate pool 200 | 0.808740 | 0 | 0 | Reject, no session changed |
| Full-context plus focused query route | 0.803026 | 0 | 1 | Reject |
| Discount very common reranker terms | 0.794407 | 0 | 3 | Reject |
| Open-ended intent route with one extra broad question | 0.808440 | 0 | 0 | Reject, three existing hits arrived one turn later |

The pool-depth wiring was checked directly: the reranker received 50, 100, and 200 rows respectively. The identical pool results were therefore genuine, not a configuration failure.

The Issue 3 intent-routing prototype classified an opener as constraint-bearing
or open-ended using only observable language. It preserved the broad `other`
question but gave open-ended sessions one additional clarification turn. A
feature-off run reproduced the frozen complete result exactly, SHA256
`5386560e643c3d4e2a73281b5bcce6e5ffd4ed05540fa9cc7db6c86657b764a8`.
With routing enabled, Hit Rate@10 and MRR were unchanged, three existing hits
arrived one turn later, MTTC worsened from 2.945 to 2.960, and technical score
fell from 0.808740 to 0.808440. The candidate was rejected and the frozen
question policy was retained.

A final negative-preference penalty was considered but stopped before implementation. The released simulator creates the earlier preference from the target product itself. Across all 30 Intent Override sessions, every earlier preference overlapped the correct target, 29 had all extracted terms in the target, and no override message named the earlier value directly. Penalizing that evidence would attack the correct product without a reliable value to identify.

The runtime was frozen after these checks. A fresh complete run matched the selected 200-session output byte for byte. Twenty catalog-free tests now cover the Agent, evaluator, result comparison, determinism, hidden-metadata isolation, and freeze receipt.

## Limitations

- Scores use the 200 public sessions, not the organizer's 800 private sessions.
- The broad `other` clarification is evaluator-efficient but less natural than a field-specific question strategy.
- Common categories with generic material and closure constraints remain difficult to distinguish lexically.
- Intent-change messages add the new requirement but do not fully remove every earlier preference from retrieval.
- The reranker was selected on the 200-session public set. No private-set behavior is verified.
- Buying-versus-Browsing question routing and profile personalization were not promoted because the remaining failures did not provide evidence that either would improve the protected score, while the broad `other` question was already measurably productive.
- No private data, product transactions, user interface, multimodal behavior, or live model was tested.
