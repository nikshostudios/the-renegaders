# The Renegaders

The Renegaders is a deterministic shopping Agent for Track 4 of TechJam 2026. It keeps useful terms across a conversation, asks structured clarification questions, and ranks the frozen 50,000-product catalog with SQLite FTS5.

The Agent runs locally with Python's standard library. It makes no model or network calls during evaluation, reports zero model tokens, and has zero API cost.

## Verified public-set result

A fresh run on the released 200-session public set produced:

| Metric | Result |
| --- | ---: |
| Exact targets found | 187 of 200 |
| Hit Rate@10 | 0.935000 |
| MRR | 0.600468 |
| MTTC | 2.945000 |
| Technical score | 0.808740 |

The untouched starter found 25 of 200 targets. These are public development results only. The Agent has not been tested on the organizer's 800 private sessions.

## Quick start

Python 3.10 or later is required. No package installation is needed.

1. Clone this repository.
2. Obtain `catalog.jsonl.gz` from the authorized organizer release.
3. Verify it against the organizer's published `SHA256SUMS` file.
4. Decompress it into the ignored local data path:

```bash
gzip -dc /path/to/catalog.jsonl.gz > data/catalog.jsonl
```

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the released public-set evaluation:

```bash
python3 -m evaluator.local_evaluator --output results.json
```

`results.json` is ignored so local runs do not create accidental Git changes. The checked evidence is in [`results/final-verification.json`](results/final-verification.json).

Run the three-scenario headless demo:

```bash
python3 demo.py
```

Measure index construction and response latency separately:

```bash
python3 -m evaluator.performance_probe --output performance.json
```

## Repository guide

```text
starter/agent.py                  Agent entry point
evaluator/local_evaluator.py      Released local evaluator
tests/                            Agent and evaluator unit tests
data/public_set.jsonl             Released 200-session development set
docs/overnight_agent_report.md    Method, evidence, cost, and limitations
docs/agent_api_contract.json      Required Agent response contract
results/                          Checked baseline and final public evidence
```

The downloaded catalog is deliberately excluded because it is about 60 MB and remains subject to the source dataset's terms. See [`DATA_ATTRIBUTION.md`](DATA_ATTRIBUTION.md).

## How the Agent works

The current implementation adds four bounded changes to the weak starter:

1. It remembers product terms across turns so a later constraint does not erase the original category.
2. It asks the allowed `other` clarification during the first four turns so the deterministic customer policy can reveal concrete requirements.
3. It filters fixed conversation boilerplate before retrieval so simulator language does not outrank product evidence.
4. It retrieves 50 lexical candidates internally and deterministically reranks them by query-term coverage across title, feature, detail, category, store, and description fields before returning the requested top results.

The reranker can be disabled with `Agent(catalog_path, rerank=False)`. A full-run equivalence check compared all 645 response objects with the fixed-point Agent and found zero differences; the checked receipt is in [`results/fallback-equivalence.json`](results/fallback-equivalence.json).

The required class is `starter.agent.Agent`. Its public methods are `reset(...)` and `respond(...)`, as defined in [`docs/agent_api_contract.json`](docs/agent_api_contract.json).

## Collaborating

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before changing the Agent. Keep changes small, add or update tests, and never commit catalogs, credentials, private evaluator material, generated caches, or local machine paths.

GitHub Actions runs the catalog-free unit suite on every push and pull request. Full scoring remains a local check because the catalog is intentionally not stored in GitHub.

## Known limitations

- The broad `other` clarification is effective in the released simulator but less natural than asking field-specific questions.
- The Agent is lexical, so products with generic category and material descriptions remain difficult to distinguish.
- Intent updates add new evidence but do not fully delete every earlier preference. The public Intent Override result is 0.900000, but the demo and report do not claim complete natural-language negation handling.
- The selected reranking weight was chosen from a bounded experiment on the released public set. The organizer's private set may respond differently.
- One local 200-session timing probe recorded a 1.485-second index build, 22.68 ms p50 response latency, and 49.35 ms p95 response latency. Timing varies by host.
- No private sessions, user interface, multimodal behavior, real transactions, or live model behavior has been tested.
