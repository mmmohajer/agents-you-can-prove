from __future__ import annotations

import re
from functools import lru_cache

from agent.paths import PROMPTS_DIR

HEADER_RE = re.compile(
    r"^---\s*\nversion:\s*(?P<version>.+?)\s*\ndate:\s*(?P<date>.+?)\s*\nnote:\s*(?P<note>.+?)\s*\n---\s*\n",
    re.S,
)
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PromptLoadError(ValueError):
    pass


@lru_cache(maxsize=64)
def _read(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise PromptLoadError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


def load(name: str, **variables: str) -> tuple[str, str]:
    raw = _read(name)
    match = HEADER_RE.match(raw)
    if not match:
        raise PromptLoadError(f"{name} is missing a version header.")
    body = raw[match.end() :]
    needed = set(PLACEHOLDER_RE.findall(body))
    missing = needed - set(variables)
    if missing:
        raise PromptLoadError(f"{name} missing values for: {sorted(missing)}")
    extra = set(variables) - needed
    if extra:
        raise PromptLoadError(f"{name} unused values: {sorted(extra)}")
    return body.format(**variables), match.group("version").strip()
