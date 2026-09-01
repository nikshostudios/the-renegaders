# The Renegaders submission agent

A deterministic multi-turn shopping agent for the TechJam Conversational
E-Commerce Search Challenge.

The agent keeps useful product terms across a conversation, asks a structured
clarification question during the opening turns, and ranks the frozen 50,000
product catalog using SQLite FTS5 followed by a deterministic field-aware
reranker.

## Bundle contents

```text
agent.py           Agent entry point, exports the required `Agent` class
requirements.txt   Dependency manifest, no third-party packages
README.md          Setup, run command, and environment requirements
REPORT.md          Method, model choice, cost, latency, and limitations
```

## Requirements

- Python 3.10 or later. No other Python version requirement applies.
- SQLite built with the FTS5 extension, which is the default in the standard
  CPython distributions.
- No third-party packages. Do not run an install step.

Confirm FTS5 before scoring:

```bash
python3 -c "import sqlite3; sqlite3.connect(':memory:').execute('CREATE VIRTUAL TABLE t USING fts5(x)'); print('fts5 available')"
```

## Network and credential policy

- The agent makes no network call at any point, during construction or during
  any turn.
- The agent requires no API key, no credential, and no environment variable.
- The agent calls no language model, so there is no offline fallback to
  describe. Offline operation is the only mode.
- Reported token usage is `0` prompt tokens and `0` completion tokens on every
  turn, because no model is invoked.

The agent therefore runs unchanged when the organizer disables network access.

## Catalog

The agent reads the frozen official catalog as JSON Lines. Each line must be one
product object containing at least `parent_asin`, and optionally `title`,
`categories`, `features`, `details`, `store`, and `description`.

The catalog is not included in this bundle. Place the organizer catalog at
`data/catalog.jsonl` relative to the working directory, or pass an explicit path
to the constructor.

## Run command

Construct the agent once per scoring run and reuse it across sessions. Index
construction reads the catalog once and takes roughly 1.5 seconds for 50,000
products.

```python
from agent import Agent

agent = Agent("data/catalog.jsonl")       # explicit path, recommended
agent.reset(session_id, user_profile)
response = agent.respond(session_id, user_message, turn, top_k)
```

`Agent()` with no argument defaults to the relative path `data/catalog.jsonl`.

One command that exercises the agent end to end from this directory:

```bash
python3 -c "from agent import Agent; a=Agent('data/catalog.jsonl'); a.reset('s',{}); print(a.respond('s','I am looking for a black leather wallet.',1,10))"
```

## Interface

```python
class Agent:
    def reset(self, session_id: str, user_profile: dict) -> None: ...
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict: ...
```

`respond` returns:

```python
{
    "message": str,                       # customer facing text
    "ask_attribute": str | None,          # one allowed attribute, or None
    "recommendations": [{"parent_asin": str}, ...],   # best to worst, length <= top_k
    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
}
```

`reset` must be called before `respond` for a given `session_id`. Calling
`respond` for an unknown `session_id` raises `RuntimeError`.

Recommendations are ordered best to worst, contain no duplicate `parent_asin`,
and contain only identifiers present in the supplied catalog.

## Determinism

The agent uses no randomness, no clock, no ordering that depends on the host,
and no persistent state outside the current process. Two constructions of the
agent over the same catalog produce identical output for identical
conversations. Session state is keyed by `session_id` and does not leak between
sessions.

`Agent(catalog_path, rerank=False)` disables the field-aware reranker and
restores plain lexical ordering. This flag exists as a documented fallback. The
default `rerank=True` is the submitted configuration.

## Resource behavior

- Index construction took 1.485 seconds in one local run and 2.654 seconds in a
  later rerun, with one full read of the catalog file.
- The FTS5 index is held in an in-memory SQLite database. Nothing is written to
  disk at any point.
- Per-turn latency across the 200 released public sessions on Python 3.11.3
  with SQLite 3.40.1 was 22.68 ms at p50 and 49.35 ms at p95 in one local run.
  A later rerun measured 46.49 ms at p50 and 179.66 ms at p95. The technical
  score remained 0.808740. Timing varies materially with host load and these
  measurements are not guarantees.

See `REPORT.md` for method, evidence, and limitations.
