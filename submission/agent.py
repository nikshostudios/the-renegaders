from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import NamedTuple


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
RERANK_POOL_SIZE = 50
RERANK_EVIDENCE_WEIGHT = 3.0
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
    "actually", "additional", "ask", "attribute", "don", "earlier", "exploring",
    "have", "ignore", "key", "matters", "need", "one", "options", "other",
    "preference", "quite", "requirement", "right", "specific", "still", "those",
    "use", "what", "yet", "your",
}


class CandidateRow(NamedTuple):
    parent_asin: str
    title: str
    categories: str
    features: str
    details: str
    store: str
    description: str
    lexical_score: float


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _terms(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


class Agent:
    """Deterministic conversational BM25 Agent with no model dependency."""

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
        rerank: bool = True,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.rerank = rerank
        self.connection = sqlite3.connect(":memory:")
        self._sessions: set[str] = set()
        self._session_terms: dict[str, list[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                batch.append(
                    (
                        str(product["parent_asin"]),
                        _text(product.get("title")),
                        _text(product.get("categories")),
                        _text(product.get("features")),
                        _text(product.get("details")),
                        _text(product.get("store")),
                        _text(product.get("description")),
                    )
                )
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

    def _evidence_score(self, row: CandidateRow, query_terms: list[str]) -> float:
        title_terms = set(_terms(row.title))
        category_terms = set(_terms(row.categories))
        detail_terms = set(_terms(f"{row.features} {row.details}"))
        other_terms = set(_terms(f"{row.store} {row.description}"))
        matched = 0
        score = 0.0
        for term in query_terms:
            if term in title_terms:
                score += 4.0
                matched += 1
            elif term in detail_terms:
                score += 2.5
                matched += 1
            elif term in category_terms:
                score += 2.0
                matched += 1
            elif term in other_terms:
                score += 1.0
                matched += 1
        if query_terms:
            score += 4.0 * matched / len(query_terms)
        return score

    def reset(self, session_id: str, user_profile: dict) -> None:
        # The profile is anonymized and may be used for personalization.
        self._sessions.add(session_id)
        self._session_terms[session_id] = []

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        if session_id not in self._sessions:
            raise RuntimeError("reset must be called before respond")
        history = self._session_terms[session_id]
        history.extend(_terms(user_message))
        unique_terms = list(dict.fromkeys(history))[-40:]
        expression = " OR ".join(f'"{term}"' for term in unique_terms)
        if not expression:
            recommendations: list[dict] = []
        elif not self.rerank:
            rows = self.connection.execute(
                "SELECT parent_asin FROM products WHERE products MATCH ? "
                "ORDER BY bm25(products, 0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0) LIMIT ?",
                (expression, top_k),
            ).fetchall()
            recommendations = [{"parent_asin": str(row[0])} for row in rows]
        else:
            rows = [
                CandidateRow(*row)
                for row in self.connection.execute(
                    "SELECT parent_asin, title, categories, features, details, store, description, "
                    "bm25(products, 0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0) AS lexical_score "
                    "FROM products WHERE products MATCH ? ORDER BY lexical_score LIMIT ?",
                    (expression, max(top_k, RERANK_POOL_SIZE)),
                ).fetchall()
            ]
            scored = [
                (
                    RERANK_EVIDENCE_WEIGHT * self._evidence_score(row, unique_terms) - index,
                    index,
                    row,
                )
                for index, row in enumerate(rows)
            ]
            scored.sort(key=lambda item: (-item[0], item[1]))
            recommendations = [
                {"parent_asin": str(row.parent_asin)}
                for _, _, row in scored[:top_k]
            ]
        return {
            "message": "Here are the closest matches. What specific requirement matters most?",
            "ask_attribute": "other" if turn <= 4 else None,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
