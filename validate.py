"""Validate generated ad data: lift recovery + totals check."""

import sys
import numpy as np
import pandas as pd
from generate import EFFECTS_CONFIG, EMOJI_POOL
from dashboard.analytics.lift_engine import compute_lift as _engine_lift

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
LIFT_TOLERANCE = {
    "roas": 0.35,
    "ctr": 0.35,
    "conv_rate": 0.60,
}


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


def raw_lift_ratio(df, kpi_col, present_mask):
    """Compute raw lift ratio. Uses the engine for dashboard KPIs,
    direct column access for validation-only metrics (conv_rate)."""
    engine_kpis = {"roas": "ROAS", "ctr": "CTR"}
    if kpi_col in engine_kpis:
        result = _engine_lift(df, present_mask, engine_kpis[kpi_col])
        if np.isnan(result.mean_absent) or result.mean_absent == 0:
            return float("nan")
        return result.mean_present / result.mean_absent
    present = df.loc[present_mask, kpi_col].mean()
    absent = df.loc[~present_mask, kpi_col].mean()
    if absent == 0 or np.isnan(absent):
        return float("nan")
    return present / absent


def check_lifts(df):
    """Recover per-attribute lift and compare against designed multipliers."""
    df = df.copy()
    df["roas"] = df["revenue"] / df["spend"]
    df["ctr"] = df["clicks"] / df["impressions"]
    df["conv_rate"] = np.where(df["clicks"] > 0, df["purchases"] / df["clicks"], 0)
    df["has_digit_headline"] = df["headline"].str.contains(r"\d", regex=True)
    df["has_digit_body"] = df["body"].str.contains(r"\d", regex=True)
    df["has_emoji_body"] = df["body"].apply(lambda b: any(e in b for e in EMOJI_POOL))
    df["body_long"] = df["body"].str.len() > 50

    text_label_types = ["Noun", "Verb", "Phrase"]
    for lt in text_label_types:
        df[f"has_{lt}"] = df["labels"].str.contains(f":{lt}(?:\\||$)", regex=True)

    all_ok = True
    for kpi, effect_key in [("roas", "roas"), ("ctr", "ctr"), ("conv_rate", "conv_rate")]:
        effects = EFFECTS_CONFIG[f"{effect_key}_effects"]
        tol = LIFT_TOLERANCE[kpi]
        print(f"\n=== {kpi.upper()} Lift Recovery (tolerance {tol:.0%}) ===")

        print("\n  Media type:")
        for mt in ["image", "video"]:
            lift = raw_lift_ratio(df, kpi, df["media_type"] == mt)
            designed = effects["media_type"][mt]
            diff = abs(lift / designed - 1)
            status = "OK" if diff < tol else "DRIFT"
            if diff >= tol:
                all_ok = False
            print(f"    {mt:<10s} lift={lift:.2f}  designed={designed:.2f}  [{status}]")

        print("\n  Aspect ratio:")
        for ar in ["1:1", "4:5", "9:16"]:
            lift = raw_lift_ratio(df, kpi, df["aspect_ratio"] == ar)
            designed = effects["aspect_ratio"][ar]
            print(f"    {ar:<10s} lift={lift:.2f}  designed={designed:.2f}")

        print("\n  Structural flags:")
        for flag, label, cfg_key in [
            ("has_digit_headline", "hl_numbers", "headline_has_numbers"),
            ("has_digit_body", "bd_numbers", "body_has_numbers"),
            ("has_emoji_body", "bd_emoji", "body_has_emoji"),
            ("body_long", "body_long", "body_long"),
        ]:
            lift = raw_lift_ratio(df, kpi, df[flag])
            designed = effects[cfg_key]
            diff = abs(lift / designed - 1)
            status = "OK" if diff < tol else "DRIFT"
            if diff >= tol:
                all_ok = False
            print(f"    {label:<14s} lift={lift:.2f}  designed={designed:.2f}  [{status}]")

        print("\n  Label types (text only — Image/Video validated via media_type):")
        for lt in text_label_types:
            lift = raw_lift_ratio(df, kpi, df[f"has_{lt}"])
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
