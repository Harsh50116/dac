"""Synthetic ad data generator — Phase 1 of DAC project."""

import argparse
import numpy as np
import pandas as pd

# =============================================================================
# EFFECTS CONFIG — ground-truth multipliers (Phase 2 answer key)
# =============================================================================

EFFECTS_CONFIG = {
    # --- Base KPI values ---
    "base_roas": 3.0,
    "base_ctr": 0.008,
    "base_conv_rate": 0.020,

    # --- Noise (lognormal sigma) ---
    "noise_sigma": 0.10,

    # --- Spend / impressions sampling (lognormal parameters) ---
    "spend_mean": 200,
    "spend_sigma": 0.6,
    "impressions_mean": 18500,
    "impressions_sigma": 0.5,

    # --- Body length threshold ---
    "body_long_threshold": 50,

    # --- Attribute sampling probabilities ---
    "attribute_probs": {
        "media_type": {"image": 0.60, "video": 0.40},
        "aspect_ratio": {"1:1": 0.35, "4:5": 0.40, "9:16": 0.25},
        "headline_has_numbers": 0.30,
        "body_has_numbers": 0.25,
        "body_has_emoji": 0.20,
        "body_long": 0.25,
    },
    "category_weights": {
        "accessories": 0.12, "adult": 0.08, "adventure": 0.12,
        "casual": 0.10, "commute": 0.10, "gravel": 0.10,
        "mountain": 0.12, "road": 0.10, "sale": 0.08, "urban": 0.08,
    },

    # --- ROAS durable effects ---
    "roas_effects": {
        "media_type": {"image": 1.45, "video": 0.80},
        "aspect_ratio": {"1:1": 1.00, "4:5": 1.53, "9:16": 0.82},
        "headline_has_numbers": 1.46,
        "body_has_numbers": 1.43,
        "body_has_emoji": 1.20,
        "body_long": 0.70,
        "label_type": {
            "Image": 1.00, "Video": 1.00,
            "Phrase": 1.15, "Noun": 1.00, "Verb": 0.88,
        },
    },

    # --- CTR durable effects (dampened) ---
    "ctr_effects": {
        "media_type": {"image": 1.10, "video": 0.92},
        "aspect_ratio": {"1:1": 1.00, "4:5": 1.10, "9:16": 0.95},
        "headline_has_numbers": 1.12,
        "body_has_numbers": 1.08,
        "body_has_emoji": 1.05,
        "body_long": 0.92,
        "label_type": {
            "Image": 1.00, "Video": 1.00,
            "Phrase": 1.06, "Noun": 1.00, "Verb": 0.96,
        },
    },

    # --- Conversion rate durable effects (dampened) ---
    "conv_rate_effects": {
        "media_type": {"image": 1.12, "video": 0.90},
        "aspect_ratio": {"1:1": 1.00, "4:5": 1.12, "9:16": 0.90},
        "headline_has_numbers": 1.10,
        "body_has_numbers": 1.08,
        "body_has_emoji": 1.06,
        "body_long": 0.88,
        "label_type": {
            "Image": 1.00, "Video": 1.00,
            "Phrase": 1.08, "Noun": 1.00, "Verb": 0.94,
        },
    },

    # --- Seasonal effects (month number -> multiplier, applied to all KPIs) ---
    "seasonal": {
        1: 0.85, 2: 0.88, 3: 1.05, 4: 1.15,
        5: 1.20, 6: 1.15, 7: 1.10, 8: 1.05,
        9: 0.95, 10: 0.90, 11: 0.85, 12: 0.82,
    },

    # --- Category temporal effects (ephemeral) ---
    # multiplier(t) = base + amplitude * sin(2π * t / period + phase)
    # adventure: min=0.40 (-60%), max=1.90 (+90%) matching spec
    "categories": {
        "accessories": {"base": 1.00, "amplitude": 0.15, "period": 12, "phase": 0.0},
        "adult":       {"base": 0.95, "amplitude": 0.10, "period": 12, "phase": 1.0},
        "adventure":   {"base": 1.15, "amplitude": 0.75, "period": 8,  "phase": 0.5},
        "casual":      {"base": 1.05, "amplitude": 0.20, "period": 10, "phase": 2.0},
        "commute":     {"base": 1.00, "amplitude": 0.25, "period": 12, "phase": 3.0},
        "gravel":      {"base": 1.10, "amplitude": 0.30, "period": 9,  "phase": 1.5},
        "mountain":    {"base": 1.05, "amplitude": 0.40, "period": 11, "phase": 4.0},
        "road":        {"base": 1.00, "amplitude": 0.15, "period": 12, "phase": 0.5},
        "sale":        {"base": 0.90, "amplitude": 0.35, "period": 6,  "phase": 0.0},
        "urban":       {"base": 1.00, "amplitude": 0.20, "period": 10, "phase": 2.5},
    },

    # --- Phrase temporal effects (ephemeral, gaussian bump) ---
    # multiplier(t) = 1.0 + (peak_mult - 1.0) * exp(-0.5 * ((t - peak_month) / sigma)^2)
    # peak_month: months from start date (0 = first month)
    "phrases": {
        "your spring wardrobe":    {"peak_month": 3,  "sigma": 3, "peak_mult": 1.35},
        "ride in comfort":         {"peak_month": 6,  "sigma": 4, "peak_mult": 1.25},
        "gear up for summer":      {"peak_month": 5,  "sigma": 3, "peak_mult": 1.30},
        "cold weather essentials": {"peak_month": 11, "sigma": 3, "peak_mult": 1.40},
        "new arrivals":            {"peak_month": 9,  "sigma": 5, "peak_mult": 1.20},
        "trail tested":            {"peak_month": 14, "sigma": 3, "peak_mult": 1.28},
        "race day ready":          {"peak_month": 17, "sigma": 4, "peak_mult": 1.32},
        "all day comfort":         {"peak_month": 20, "sigma": 3, "peak_mult": 1.22},
        "built to last":           {"peak_month": 8,  "sigma": 4, "peak_mult": 1.18},
        "lightweight layers":      {"peak_month": 4,  "sigma": 3, "peak_mult": 1.26},
        "gravel ready":            {"peak_month": 15, "sigma": 3, "peak_mult": 1.30},
        "adventure awaits":        {"peak_month": 12, "sigma": 4, "peak_mult": 1.35},
    },

    # --- Label type sampling probabilities (independent per ad) ---
    "label_type_probs": {
        "Noun": 0.70,
        "Verb": 0.50,
        "Phrase": 0.40,
    },

    # --- Volume shaping (Dirichlet alpha — lower = spikier) ---
    "volume_alpha": 0.15,
}


# =============================================================================
# STEP 2 — Volume shaping
# =============================================================================

def generate_month_list(start, end):
    """Return list of YYYY-MM strings from start (inclusive) to end (exclusive)."""
    months = pd.date_range(start, end, freq="MS", inclusive="both")
    return [m.strftime("%Y-%m") for m in months]


def generate_monthly_counts(n_ads, months, rng):
    """Sample spiky per-month ad counts that sum to n_ads."""
    n_months = len(months)
    alpha = EFFECTS_CONFIG["volume_alpha"]
    proportions = rng.dirichlet(np.full(n_months, alpha))
    raw = proportions * n_ads
    counts = np.floor(raw).astype(int)
    remainder = n_ads - counts.sum()
    fractional = raw - counts
    top_indices = np.argsort(fractional)[-remainder:]
    counts[top_indices] += 1
    return dict(zip(months, counts))


# =============================================================================
# STEP 3 — Attribute sampling
# =============================================================================

def sample_attributes(monthly_counts, rng):
    """Sample per-ad attributes based on config probabilities."""
    probs = EFFECTS_CONFIG["attribute_probs"]
    cat_weights = EFFECTS_CONFIG["category_weights"]
    label_probs = EFFECTS_CONFIG["label_type_probs"]
    phrases = list(EFFECTS_CONFIG["phrases"].keys())

    categories = list(cat_weights.keys())
    cat_probs = np.array(list(cat_weights.values()))
    cat_probs = cat_probs / cat_probs.sum()

    media_types = list(probs["media_type"].keys())
    media_probs = np.array(list(probs["media_type"].values()))

    aspect_types = list(probs["aspect_ratio"].keys())
    aspect_probs = np.array(list(probs["aspect_ratio"].values()))

    rows = []
    ad_counter = 0
    for month, count in monthly_counts.items():
        for _ in range(count):
            media = rng.choice(media_types, p=media_probs)
            aspect = rng.choice(aspect_types, p=aspect_probs)
            category = rng.choice(categories, p=cat_probs)
            hl_numbers = bool(rng.random() < probs["headline_has_numbers"])
            bd_numbers = bool(rng.random() < probs["body_has_numbers"])
            bd_emoji = bool(rng.random() < probs["body_has_emoji"])
            bd_long = bool(rng.random() < probs["body_long"])

            label_types = ["Image"] if media == "image" else ["Video"]
            for ltype, lprob in label_probs.items():
                if rng.random() < lprob:
                    label_types.append(ltype)

            assigned_phrase = None
            if "Phrase" in label_types:
                assigned_phrase = rng.choice(phrases)

            rows.append({
                "ad_id": f"ad_{ad_counter:05d}",
                "date": month,
                "media_type": media,
                "aspect_ratio": aspect,
                "category": category,
                "headline_has_numbers": hl_numbers,
                "body_has_numbers": bd_numbers,
                "body_has_emoji": bd_emoji,
                "body_long": bd_long,
                "label_types": label_types,
                "assigned_phrase": assigned_phrase,
            })
            ad_counter += 1

    return pd.DataFrame(rows)
