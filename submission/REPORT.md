# The Renegaders technical report

Track 4, TechJam Conversational E-Commerce Search Challenge.

Project name: The Renegaders

## Summary

A deterministic conversational retrieval agent that finds the hidden target
product using lexical search plus a field-aware reranker, with no language model
in the loop. It runs offline, needs no credential, costs nothing to run, and
responds in tens of milliseconds.

## Architecture

The agent is a single Python module built on the Python standard library and
SQLite FTS5. There are four components.

1. **Catalog index.** On construction the agent streams the JSON Lines catalog
   once and inserts every product into an in-memory SQLite FTS5 virtual table
   with six searchable columns: `title`, `categories`, `features`, `details`,
   `store`, `description`. `parent_asin` is stored unindexed. Nested list and
   dictionary metadata is flattened to text.

2. **Session term memory.** `reset` creates an empty term list for the
   `session_id`. Every `respond` call tokenizes the incoming customer message,
   drops a fixed stopword set, and appends the surviving terms to that session's
   list. The retrieval query is the deduplicated last 40 terms joined with `OR`.
   This is the mechanism that keeps the original product category alive when a
   later customer reply contains only a constraint such as "cotton". Without it,
   a follow-up message would search for the constraint alone.

3. **Conversation noise filtering.** The stopword set deliberately includes the
   simulator's own conversational template words, for example `exploring`,
   `preference`, `requirement`, `matters`, `additional`, `ignore`, `earlier`,
   `other`. Filtering these before retrieval stops boilerplate phrasing from
   outranking real product evidence.

4. **Field-aware reranking.** Retrieval pulls an internal pool of 50 candidates
   ordered by a column-weighted BM25 score. Each candidate is then rescored by
   assigning every query term to its strongest matching field: title 4.0,
   features or details 2.5, categories 2.0, store or description 1.0. A coverage
   bonus of `4.0 * matched / total` rewards candidates that satisfy more of the
   accumulated conversation. The evidence score is multiplied by 3.0 and blended
   against the original lexical position, so a strong lexical hit is only
   displaced by materially better field evidence. Ties resolve to the original
   lexical order, which keeps the ranking stable.

## Clarification strategy

The agent sets `ask_attribute` to `other` on turns 1 through 4 and to `null`
afterwards. The broad question was selected because it is measurably the most
productive against the released simulator, which discloses any undisclosed
constraint when asked broadly. This is an evaluator-efficient choice rather than
the most natural conversational one, and it is listed as a limitation below.

## Model choice and cost

- **Models used at scoring time: none.** No language model, no embedding model,
  no external service, no network call.
- **Token usage: 0 prompt tokens and 0 completion tokens** across all 200 public
  sessions and 576 agent responses. The agent reports
  `{"prompt_tokens": 0, "completion_tokens": 0}` on every turn.
- **Estimated model cost: 0.00 USD**, at scoring time and during development,
  for the submitted runtime.
- **Credentials required: none.** No environment variable is read.
- **Network requirement: none.** The agent is unaffected if the organizer
  disables network access. There is no fallback path to describe, because
  offline is the only mode.

A local embedding model was evaluated during development and rejected. See
"Rejected approaches" below. It is not part of this submission and none of its
code is in this bundle.

## Latency and resource use

Measured locally on Python 3.11.3 with SQLite 3.40.1, across the 200 released
public sessions and 576 responses per run:

| Measure | Earlier run | Later verification run |
| --- | ---: | ---: |
| Index construction, 50,000 products | 1.485 s | 2.654 s |
| Response latency p50 | 22.68 ms | 46.49 ms |
| Response latency p95 | 49.35 ms | 179.66 ms |
| Response latency maximum | 79.57 ms | 1,082.22 ms |

The index is held in memory and nothing is written to disk. Timing varies by
host load. Both runs preserved the 0.808740 technical score, so treat the timing
as order-of-magnitude feasibility evidence rather than a guarantee.

## Results on the released public set

All figures below come from the released 200-session public development set,
scored with the released local evaluator. They are development results. See
"Limitations" for what they do not establish.

| Version | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: |
| Official weak baseline | 0.125000 | 0.068034 | 9.810000 | 0.106710 |
| Session term memory | 0.270000 | 0.151381 | 8.600000 | 0.228414 |
| Structured clarification | 0.890000 | 0.545169 | 3.380000 | 0.760951 |
| Conversation noise filtering | 0.900000 | 0.564446 | 3.325000 | 0.772834 |
| Field-aware top-50 reranking (submitted) | 0.935000 | 0.600468 | 2.945000 | 0.808740 |

The submitted agent located 187 of 200 targets. Compared with the previous
0.900000 configuration it fixed seven previously missed sessions and broke none.

Per scenario:

| Scenario | Sessions | Hit Rate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: |
| Buying | 80 | 0.937500 | 0.600749 | 2.550000 |
| Browsing | 80 | 0.937500 | 0.549350 | 2.800000 |
| Intent Override | 30 | 0.900000 | 0.711429 | 4.433333 |
| Boundary | 10 | 1.000000 | 0.674286 | 2.800000 |

## Reproducibility

The submitted `agent.py` is byte-identical to the frozen development runtime,
SHA256 `f88498ff1f8291dab53fe90c0404526e2fad1c734407432fbc227a9799074242`.

The complete 200-session result file produced by that runtime hashes to SHA256
`5386560e643c3d4e2a73281b5bcce6e5ffd4ed05540fa9cc7db6c86657b764a8`. A fresh
independent run reproduced that exact hash, so the reported figures are a
byte-for-byte reproduction rather than a transcription.

The agent contains no randomness and no time dependence, so repeated runs over
the same catalog and the same conversation produce identical output.

## Rejected approaches

Each of these was implemented, measured on the released public set, and rejected
because it did not beat the submitted configuration.

| Experiment | Technical score | Decision |
| --- | ---: | --- |
| Explicit state that deletes earlier constraints on intent override | 0.644049 | Reject |
| Policy-reply filtering variant | 0.753570 | Reject |
| Candidate pool 100 | 0.808740 | Reject, no session changed |
| Candidate pool 200 | 0.808740 | Reject, no session changed |
| Full context plus focused query route | 0.803026 | Reject |
| Discount very common reranker terms | 0.794407 | Reject |

A hybrid dense reranker using a local `nomic-embed-text` model over the lexical
top 50 was also rejected. Eleven of 20 then-missed targets were present in the
candidate pool, but the dense blend moved none of them into the top 10.

A negative-preference penalty for intent override was designed and then stopped
before implementation. In the released simulator the earlier preference is
generated from the target product itself: across all 30 Intent Override
sessions every earlier preference overlapped the correct target, and no override
message named the earlier value directly. Penalizing that evidence would have
attacked the correct product.

## Limitations

These are stated plainly because they bound what the results above prove.

- **No private-set result is claimed.** Every number in this report comes from
  the 200 released public sessions. The organizer's 800 private sessions have
  not been run and no private-set behavior is verified or predicted.
- **The reranker weight is development-set tuned.** The value 3.0 was chosen
  from a bounded sweep over 0.25, 0.5, 1.0, 1.5, 2.0, and 3.0 on the released
  public set. That selection may not generalize.
- **The clarification question is broad, not natural.** Asking `other` is
  effective against the released deterministic simulator and less natural than
  field-specific questioning. A simulator that paraphrases differently could
  reward a different strategy.
- **Retrieval is purely lexical.** Products whose distinguishing attributes are
  expressed as generic category and material language remain hard to separate.
  Thirteen of 200 public sessions still miss.
- **Intent override is additive, not subtractive.** A new requirement is added
  to the session evidence, but earlier preference terms are not removed. This is
  a deliberate, measured choice rather than an oversight, and it means the agent
  does not implement true natural-language negation.
- **Buying versus Browsing routing and profile personalization are not
  implemented.** The anonymized `user_profile` is accepted and ignored. Neither
  was promoted because the remaining failures gave no evidence either would
  improve the score.
- **Latency figures are host/load-dependent local measurements**, not a
  multi-machine benchmark or a guarantee.
- **Untested entirely:** private sessions, any user interface, multimodal input,
  real transactions, and live model behavior.

## Team contributions

[SHOHAM DECISION REQUIRED - team contribution wording. Do not fill this in
without confirming each teammate's actual contribution with them directly.]

## Data attribution

The competition catalog derives from Amazon Reviews 2023, published by McAuley
Lab at UCSD (https://amazon-reviews-2023.github.io/), category
`Clothing_Shoes_and_Jewelry`, joined on `parent_asin`. The catalog is not
redistributed in this bundle.
