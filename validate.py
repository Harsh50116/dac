"""Validate generated ad data: lift recovery + totals check."""

import sys
import numpy as np
import pandas as pd
from generate import EFFECTS_CONFIG

DEMO_TARGETS = {
    "n_ads": 2650,
    "spend": 535_606,
    "revenue": 2_099_174,
    "impressions": 49_256_880,
    "clicks": 410_058,
    "purchases": 8_307,
    "roas": 3.92,
}

TOLERANCE = 0.10
LIFT_TOLERANCE = 0.35


def check_totals(df):
    """Check aggregate totals are within tolerance of demo targets."""
    actuals = {
        "n_ads": len(df),
        "spend": df["spend"].sum(),
        "revenue": df["revenue"].sum(),
        "impressions": df["impressions"].sum(),
        "clicks": df["clicks"].sum(),
        "purchases": df["purchases"].sum(),
        "roas": df["revenue"].sum() / df["spend"].sum(),
    }
    print("=== Totals Check ===")
    all_ok = True
    for key, target in DEMO_TARGETS.items():
        actual = actuals[key]
        pct = (actual - target) / target
        ok = abs(pct) <= TOLERANCE
        status = "OK" if ok else "FAIL"
        print(f"  {key:<14s} actual={actual:>12,.1f}  target={target:>12,.1f}  diff={pct:+.1%}  [{status}]")
        if not ok:
            all_ok = False
    return all_ok


def compute_lift(df, col, present_mask):
    """Compute lift = mean(col | present) / mean(col | absent)."""
    present = df.loc[present_mask, col].mean()
    absent = df.loc[~present_mask, col].mean()
    if absent == 0 or np.isnan(absent):
        return float("nan")
    return present / absent


def _expected_lift(effect_val, prob):
    """Expected lift given a binary attribute's multiplier and prevalence.

    When attribute is present, mean KPI ∝ effect_val.
    When absent, mean KPI ∝ 1.0.
    lift = mean_present / mean_absent
         = effect_val / (population_mean_excluding_present)
    Approximation: lift ≈ effect_val / weighted_avg_of_absent
    For binary: absent_mean ∝ 1.0, so lift ≈ effect_val / 1.0 = effect_val.
    But since compute_lift divides by absent mean (not overall),
    lift ≈ effect_val for flags (present vs absent = multiplier vs 1.0).
    """
    return effect_val


def check_lifts(df):
    """Recover per-attribute lift and compare against designed multipliers."""
    df = df.copy()
    df["roas"] = df["revenue"] / df["spend"]
    df["ctr"] = df["clicks"] / df["impressions"]
    df["conv_rate"] = np.where(df["clicks"] > 0, df["purchases"] / df["clicks"], 0)
    df["has_digit_headline"] = df["headline"].str.contains(r"\d", regex=True)
    df["has_digit_body"] = df["body"].str.contains(r"\d", regex=True)
    df["body_long"] = df["body"].str.len() > 50

    label_types = ["Image", "Video", "Noun", "Verb", "Phrase"]
    for lt in label_types:
        df[f"has_{lt}"] = df["labels"].str.contains(f":{lt}(?:\\||$)", regex=True)

    all_ok = True
    for kpi, effect_key in [("roas", "roas"), ("ctr", "ctr"), ("conv_rate", "conv_rate")]:
        effects = EFFECTS_CONFIG[f"{effect_key}_effects"]
        print(f"\n=== {kpi.upper()} Lift Recovery ===")

        print("\n  Media type:")
        for mt in ["image", "video"]:
            lift = compute_lift(df, kpi, df["media_type"] == mt)
            designed = effects["media_type"][mt]
            diff = abs(lift / designed - 1)
            status = "OK" if diff < LIFT_TOLERANCE else "DRIFT"
            if diff >= LIFT_TOLERANCE:
                all_ok = False
            print(f"    {mt:<10s} lift={lift:.2f}  designed={designed:.2f}  [{status}]")

        print("\n  Aspect ratio:")
        for ar in ["1:1", "4:5", "9:16"]:
            lift = compute_lift(df, kpi, df["aspect_ratio"] == ar)
            designed = effects["aspect_ratio"][ar]
            print(f"    {ar:<10s} lift={lift:.2f}  designed={designed:.2f}")

        print("\n  Structural flags:")
        for flag, label, cfg_key in [
            ("has_digit_headline", "hl_numbers", "headline_has_numbers"),
            ("has_digit_body", "bd_numbers", "body_has_numbers"),
            ("body_long", "body_long", "body_long"),
        ]:
            lift = compute_lift(df, kpi, df[flag])
            designed = effects[cfg_key]
            diff = abs(lift / designed - 1)
            status = "OK" if diff < LIFT_TOLERANCE else "DRIFT"
            if diff >= LIFT_TOLERANCE:
                all_ok = False
            print(f"    {label:<14s} lift={lift:.2f}  designed={designed:.2f}  [{status}]")

        print("\n  Label types:")
        for lt in label_types:
            lift = compute_lift(df, kpi, df[f"has_{lt}"])
            designed = effects["label_type"][lt]
            print(f"    {lt:<10s} lift={lift:.2f}  designed={designed:.2f}")

    print("\n=== Category Variation ===")
    overall_mean = df["roas"].mean()
    for cat in sorted(df["category"].unique()):
        cat_mean = df.loc[df["category"] == cat, "roas"].mean()
        print(f"  {cat:<14s} mean_roas={cat_mean:.2f}  vs_overall={cat_mean / overall_mean:.2f}")

    return all_ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ads.csv"
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path}\n")
    totals_ok = check_totals(df)
    lifts_ok = check_lifts(df)
    both_ok = totals_ok and lifts_ok
    print("\n" + ("=== ALL CHECKS PASSED ===" if both_ok else "=== SOME CHECKS FAILED ==="))
    return 0 if both_ok else 1


if __name__ == "__main__":
    sys.exit(main())
