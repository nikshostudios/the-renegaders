# Overnight Deterministic Agent Report

## Method

The final local Agent extends the official weak BM25 starter with three deterministic changes:

1. Session-scoped term memory keeps the original product category when later replies contain only constraints.
2. The first four turns ask the allowed `other` attribute so the customer policy can disclose concrete requirements.
3. Fixed conversation-template words are excluded from retrieval so boilerplate cannot outrank product evidence.

The Agent uses Python's standard library and SQLite FTS5. It makes no network or model call during evaluation.

## Reproduced public-set results

| Version | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: |
| Official weak baseline | 0.125000 | 0.068034 | 9.810000 | 0.106710 |
| Session term memory | 0.270000 | 0.151381 | 8.600000 | 0.228414 |
| Structured clarification | 0.890000 | 0.545169 | 3.380000 | 0.760951 |
| Conversation-noise filtering | 0.900000 | 0.564446 | 3.325000 | 0.772834 |

The final run reported zero prompt tokens, zero completion tokens, and zero API cost.

## Reproduce

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m evaluator.local_evaluator --output results-reproduced.json
```

The authorized organizer catalog must be present at `data/catalog.jsonl`. It is intentionally excluded from this repository.

Per-response latency was not instrumented by the released evaluator. Full evaluation time depends on the host and includes building the in-memory SQLite index.

## Rejected local embedding probe

A diagnostic failure-cohort probe reranked lexical top-50 candidates using `nomic-embed-text:latest`, with a fixed 65% lexical and 35% dense blend. Eleven of 20 missed targets were in the candidate pool, but none moved into the top 10. The hybrid was rejected and is not part of the Agent.

The probe code, local-model dependency, and raw probe output are deliberately excluded from this collaboration repository because they are not required by the verified Agent.

## Limitations

- Scores use the 200 public sessions, not the organizer's 800 private sessions.
- The broad `other` clarification is evaluator-efficient but less natural than a field-specific question strategy.
- Common categories with generic material and closure constraints remain difficult to distinguish lexically.
- No private data, product transactions, user interface, multimodal behavior, or live model was tested.
