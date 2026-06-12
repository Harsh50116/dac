"""Slim output validation for Explain answers.

Flags numeric claims in an LLM answer that cannot be traced back to the
grounding context. Flag-only — the answer is still shown, with a caveat.
"""

import re


NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")

# Small integers are conversational noise (list numbering, "3 moves",
# ranks) — not worth flagging.
SMALL_INT_MAX = 10
TOLERANCE = 0.05


def _to_float(token: str) -> float:
    return float(token.replace(",", "").lstrip("+"))


def _collect_numbers(value, out: set[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        out.add(float(value))
    elif isinstance(value, str):
        for match in NUMBER_RE.finditer(value):
            out.add(_to_float(match.group()))
    elif isinstance(value, dict):
        for child in value.values():
            _collect_numbers(child, out)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _collect_numbers(child, out)


def _is_grounded(x: float, grounded: set[float]) -> bool:
    magnitude = abs(x)
    if magnitude <= SMALL_INT_MAX and float(magnitude).is_integer():
        return True
    for g in grounded:
        for candidate in (g, abs(g), round(g), round(abs(g)), round(g, 1)):
            if abs(magnitude - abs(candidate)) <= TOLERANCE:
                return True
    return False


def unverified_numbers(answer: str, context: dict) -> list[str]:
    """Return numeric tokens in ``answer`` not traceable to ``context``."""
    grounded: set[float] = set()
    _collect_numbers(context, grounded)

    flagged: list[str] = []
    seen: set[str] = set()
    for match in NUMBER_RE.finditer(answer):
        token = match.group()
        if token in seen:
            continue
        seen.add(token)
        if not _is_grounded(_to_float(token), grounded):
            flagged.append(token)
    return flagged
