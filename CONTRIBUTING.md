# Contributing to The Renegaders

## Local setup

Use Python 3.10 or later. The unit suite needs no downloaded catalog:

```bash
python3 -m unittest discover -s tests -v
```

For a full public-set run, place the authorized organizer catalog at `data/catalog.jsonl`, then run:

```bash
python3 -m evaluator.local_evaluator --output results.json
```

## Change workflow

1. Create a short-lived branch from `main`.
2. Keep each change focused on one behavior or experiment.
3. Add or update tests that show the intended consequence.
4. Run the unit suite before opening a pull request.
5. Run the full public-set evaluator when retrieval or conversation behavior changes.
6. Record the before and after public metrics in the pull request description.

## Data and security rules

Never commit:

- `data/catalog.jsonl` or compressed catalog archives
- private evaluation data or organizer-only files
- API keys, credentials, `.env` files, or access tokens
- local absolute paths, generated caches, or raw local run output

Keep the source attribution in `DATA_ATTRIBUTION.md`. Do not report or imply results on the organizer's private sessions unless the organizer supplies verified evidence.

## Pull request checklist

- The unit suite passes.
- Full public metrics are included when Agent behavior changed.
- New behavior has a focused test.
- No catalog, secret, private data, cache, or machine-local path is included.
- Documentation matches what was actually verified.
