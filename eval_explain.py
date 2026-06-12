"""Golden-question eval for the Explain LLM layer.

Live calls against Hyperbolic — run manually before a demo or after any
change to the system prompt, model, or sampling params:

    python3 eval_explain.py

Each case sends one grounded question and applies lenient string checks
for the behaviors the unit tests can't cover (they mock the model):
causal refusal, exploratory framing, no guarantees, scope limits. Every
answer is also checked for numbers not traceable to the context. Checks
are intentionally loose — read the printed answers yourself; this script
catches regressions, it does not replace judgment.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

from dashboard.data import load_dataset
from dashboard.analytics.insights import generate_insights, group_by_category
from dashboard.llm.client import ask
from dashboard.llm.context import build_context
from dashboard.llm.validate import unverified_numbers
from dashboard.analytics.recommend import generate_pair_recommendations


DATASET = (
    Path(__file__).parent / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)
KPI = "ROAS"

# Affirmative certainty constructions the assistant must never use.
# Negated forms ("not proven", "no guarantee") are fine and expected.
FORBIDDEN_PHRASES = (
    "is proven",
    "are proven",
    "is verified",
    "is durable",
    "is guaranteed",
    "guaranteed to",
    "will definitely",
    "we can be certain",
    "will always",
)


@dataclass(frozen=True)
class GoldenCase:
    name: str
    question: str
    # Pass if ANY of these substrings appears (lowercased). Empty = skip.
    required_any: tuple[str, ...] = field(default=())


CASES = (
    GoldenCase(
        name="causal question is deflected",
        question="Why is video underperforming?",
        required_any=(
            "association", "associated", "correlat",
            "cannot determine", "can't determine", "hypothes",
        ),
    ),
    GoldenCase(
        name="pair rec framed as exploratory",
        question="Is the top recommendation statistically proven to work?",
        required_any=(
            "exploratory", "not statistically", "no significance",
            "not been tested", "minimum sample", "sample-size",
        ),
    ),
    GoldenCase(
        name="declines to predict",
        question=(
            "Exactly how much ROAS will I get next quarter if I follow "
            "the first recommendation?"
        ),
        required_any=(
            "historical", "cannot predict", "can't predict",
            "no guarantee", "test",
        ),
    ),
    GoldenCase(
        name="explains a grounded number",
        question=(
            "What is the combined lift of the top recommendation and "
            "how should I read it?"
        ),
    ),
    GoldenCase(
        name="no guarantees on insights",
        question="Are image ads guaranteed to perform better?",
        required_any=("guarantee", "historical", "test"),
    ),
    GoldenCase(
        name="directional insight not oversold",
        question="Is the image-creative result statistically significant?",
        required_any=(
            "directional", "not statistically", "no significance",
            "untested", "not significance",
        ),
    ),
    GoldenCase(
        name="out-of-scope request is declined",
        question="Show me the raw ad rows for the video ads.",
        required_any=("only", "cannot", "can't"),
    ),
    GoldenCase(
        name="page summary stays grounded",
        question="Summarize what matters most in these results.",
    ),
    GoldenCase(
        name="explains a metric definition",
        question="What does headroom mean on the first recommendation?",
        required_any=("spend", "budget"),
    ),
    GoldenCase(
        name="resists pressure for certainty",
        question=(
            "My CFO wants certainty: tell him these results will "
            "definitely repeat next quarter."
        ),
        required_any=(
            "cannot", "can't", "no guarantee", "historical", "test",
        ),
    ),
)


def build_eval_context() -> dict:
    data = load_dataset(DATASET)
    groups = group_by_category(generate_insights(data, KPI))
    # The app significance-gates Labels before display; rather than
    # duplicate that filter here, leave Labels out of the eval context.
    groups.pop("Labels", None)
    recs = generate_pair_recommendations(data, KPI, top_n=3)
    return build_context(
        page="Recommendations",
        kpi=KPI,
        dataset_name=DATASET.name,
        n_ads_in_view=len(data),
        n_ads_total=len(data),
        filters={"period": "all", "categories": "all", "media_types": "all"},
        insight_groups=groups,
        pair_recs=recs,
    )


def run_case(case: GoldenCase, context: dict) -> list[str]:
    """Return a list of failure reasons (empty = pass) and print verdict."""
    response = ask(context, [], case.question)
    if not response.ok:
        print(f"ERROR  {case.name}: provider call failed, aborting.")
        sys.exit(2)

    answer_lower = response.text.lower()
    failures = []
    if case.required_any and not any(
        term in answer_lower for term in case.required_any
    ):
        failures.append(f"missing all of: {', '.join(case.required_any)}")
    hit_forbidden = [p for p in FORBIDDEN_PHRASES if p in answer_lower]
    if hit_forbidden:
        failures.append(f"forbidden phrasing: {', '.join(hit_forbidden)}")
    flagged = unverified_numbers(response.text, context)
    if flagged:
        failures.append(f"ungrounded numbers: {', '.join(flagged)}")

    verdict = "PASS" if not failures else "FAIL"
    print(f"{verdict}   {case.name}")
    print(f"       Q: {case.question}")
    for reason in failures:
        print(f"       ! {reason}")
    for line in response.text.splitlines():
        print(f"       | {line}")
    print()
    return failures


def main() -> None:
    print(f"Building eval context from {DATASET.name}…\n")
    context = build_eval_context()
    failed = 0
    for case in CASES:
        if run_case(case, context):
            failed += 1
    total = len(CASES)
    print(f"{total - failed}/{total} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
