from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agent.paths import DATA_DIR
from agent.tokens import count_tokens


@dataclass
class Chunk:
    chunk_id: str
    source: str
    section: str
    text: str
    tokens: int


def _split_faq(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    chunks: list[Chunk] = []
    pairs = re.split(r"\n(?=Q: )", text)
    for index, block in enumerate(pairs):
        block = block.strip()
        if not block.startswith("Q:"):
            continue
        heading = block.split("\n", 1)[0][3:].strip()
        body = f"Product FAQ — {heading}\n{block}"
        chunks.append(
            Chunk(
                chunk_id=f"faq-{index}",
                source=path.name,
                section=heading,
                text=body,
                tokens=count_tokens(body),
            )
        )
    return chunks


def _split_policy(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    chunks: list[Chunk] = []
    parts = re.split(r"\n(?=## )", text)
    title = "Billing and refunds policy"
    for index, block in enumerate(parts):
        block = block.strip()
        if not block:
            continue
        first = block.split("\n", 1)[0].lstrip("# ").strip()
        body = f"{title} — {first}\n{block}"
        chunks.append(
            Chunk(
                chunk_id=f"policy-{index}",
                source=path.name,
                section=first,
                text=body,
                tokens=count_tokens(body),
            )
        )
    return chunks


def load_chunks() -> list[Chunk]:
    return _split_faq(DATA_DIR / "faq.txt") + _split_policy(DATA_DIR / "policy.txt")


def _score(query: str, chunk: Chunk) -> float:
    query_terms = set(re.findall(r"[a-z0-9-]+", query.lower()))
    text_terms = set(re.findall(r"[a-z0-9-]+", chunk.text.lower()))
    if not query_terms:
        return 0.0
    overlap = len(query_terms & text_terms)
    identifier_bonus = 2.0 if any(term in chunk.text.lower() for term in query_terms if "-" in term) else 0.0
    return overlap + identifier_bonus


def retrieve(query: str, k: int = 3) -> list[Chunk]:
    ranked = sorted(load_chunks(), key=lambda chunk: _score(query, chunk), reverse=True)
    return [chunk for chunk in ranked[:k] if _score(query, chunk) > 0]


def format_context(chunks: list[Chunk]) -> str:
    if not chunks:
        return "(no retrieved passages)"
    return "\n\n".join(
        f"[{chunk.source} / {chunk.section}]\n{chunk.text}" for chunk in chunks
    )
