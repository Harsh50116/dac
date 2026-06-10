"""Synthetic ad data generator — Phase 1 of DAC project."""

import argparse
import numpy as np
import pandas as pd

# =============================================================================
# EFFECTS CONFIG — ground-truth multipliers (Phase 2 answer key)
# =============================================================================

EFFECTS_CONFIG = {
    # --- Base KPI values ---
    "base_roas": 2.01,
    "base_ctr": 0.00655,
    "base_conv_rate": 0.01412,

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
    """Return list of YYYY-MM strings from start (inclusive) to end (inclusive)."""
    months = pd.date_range(start, end, freq="MS", inclusive="both")
    return [m.strftime("%Y-%m") for m in months]


def generate_monthly_counts(n_ads, months, rng, config=None):
    """Sample spiky per-month ad counts that sum to n_ads."""
    cfg = config or EFFECTS_CONFIG
    n_months = len(months)
    alpha = cfg["volume_alpha"]
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

def sample_attributes(monthly_counts, rng, config=None):
    """Sample per-ad attributes based on config probabilities."""
    cfg = config or EFFECTS_CONFIG
    probs = cfg["attribute_probs"]
    cat_weights = cfg["category_weights"]
    label_probs = cfg["label_type_probs"]
    phrases = list(cfg["phrases"].keys())

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


# =============================================================================
# STEP 4 — Forward effect model (KPIs)
# =============================================================================

def category_temporal_effect(category, month_index, config=None):
    """Sine-wave multiplier for a category at a given month index."""
    cfg = (config or EFFECTS_CONFIG)["categories"][category]
    angle = 2 * np.pi * month_index / cfg["period"] + cfg["phase"]
    return cfg["base"] + cfg["amplitude"] * np.sin(angle)


def phrase_temporal_effect(phrase, month_index, config=None):
    """Gaussian bump multiplier for a phrase at a given month index."""
    cfg = (config or EFFECTS_CONFIG)["phrases"][phrase]
    decay = np.exp(-0.5 * ((month_index - cfg["peak_month"]) / cfg["sigma"]) ** 2)
    return 1.0 + (cfg["peak_mult"] - 1.0) * decay


def compute_kpi_multiplier(row, month_index, effect_key, config=None):
    """Compute the combined multiplier for one KPI (roas/ctr/conv_rate)."""
    cfg = config or EFFECTS_CONFIG
    effects = cfg[f"{effect_key}_effects"]

    mult = 1.0
    mult *= effects["media_type"][row["media_type"]]
    mult *= effects["aspect_ratio"][row["aspect_ratio"]]
    mult *= effects["headline_has_numbers"] if row["headline_has_numbers"] else 1.0
    mult *= effects["body_has_numbers"] if row["body_has_numbers"] else 1.0
    mult *= effects["body_has_emoji"] if row["body_has_emoji"] else 1.0
    mult *= effects["body_long"] if row["body_long"] else 1.0

    for ltype in row["label_types"]:
        mult *= effects["label_type"][ltype]

    mult *= category_temporal_effect(row["category"], month_index, config=cfg)
    if row["assigned_phrase"]:
        mult *= phrase_temporal_effect(row["assigned_phrase"], month_index, config=cfg)

    mult *= cfg["seasonal"][int(row["date"].split("-")[1])]

    return mult


def apply_effect_model(df, rng, start_date="2023-01", config=None):
    """Apply the forward effect model to compute KPIs for each ad."""
    cfg = config or EFFECTS_CONFIG
    start_month = int(start_date.split("-")[0]) * 12 + int(start_date.split("-")[1])
    sigma = cfg["noise_sigma"]

    roas_list, ctr_list, conv_list = [], [], []
    for _, row in df.iterrows():
        ad_month = int(row["date"].split("-")[0]) * 12 + int(row["date"].split("-")[1])
        month_index = ad_month - start_month

        roas_mult = compute_kpi_multiplier(row, month_index, "roas", config=cfg)
        ctr_mult = compute_kpi_multiplier(row, month_index, "ctr", config=cfg)
        conv_mult = compute_kpi_multiplier(row, month_index, "conv_rate", config=cfg)

        noise_r = rng.lognormal(0, sigma)
        noise_c = rng.lognormal(0, sigma)
        noise_v = rng.lognormal(0, sigma)

        roas_list.append(cfg["base_roas"] * roas_mult * noise_r)
        ctr_list.append(cfg["base_ctr"] * ctr_mult * noise_c)
        conv_list.append(cfg["base_conv_rate"] * conv_mult * noise_v)

    df["roas"] = roas_list
    df["ctr"] = ctr_list
    df["conv_rate"] = conv_list
    return df


# =============================================================================
# STEP 5 — Back out raw metrics
# =============================================================================

def compute_raw_metrics(df, rng, config=None):
    """Derive spend, revenue, impressions, clicks, purchases from KPIs."""
    cfg = config or EFFECTS_CONFIG
    n = len(df)

    spend_mu = np.log(cfg["spend_mean"]) - 0.5 * cfg["spend_sigma"] ** 2
    df["spend"] = rng.lognormal(spend_mu, cfg["spend_sigma"], n).round(2)

    imp_mu = np.log(cfg["impressions_mean"]) - 0.5 * cfg["impressions_sigma"] ** 2
    df["impressions"] = np.round(rng.lognormal(imp_mu, cfg["impressions_sigma"], n)).astype(int)

    df["revenue"] = (df["spend"] * df["roas"]).round(2)
    df["clicks"] = np.round(df["impressions"] * df["ctr"]).astype(int)
    df["purchases"] = np.round(df["clicks"] * df["conv_rate"]).astype(int)

    return df


# =============================================================================
# STEP 6 — Copy text generation
# =============================================================================

NOUNS = [
    "jersey", "bibs", "jacket", "gloves", "socks", "vest", "shorts",
    "tights", "cap", "wardrobe", "kit", "baselayer", "shell", "armwarmers",
]

VERBS = [
    "ride", "climb", "train", "race", "gear", "explore", "conquer",
    "push", "pedal", "layer", "sprint", "cruise", "descend", "shred",
]

EMOJI_POOL = ["🚴", "⛰️", "🔥", "💪", "🏔️", "☀️", "❄️", "🌧️"]

HEADLINE_TEMPLATES = [
    "{noun} for every {verb}",
    "new {noun} collection",
    "{verb} further in our {noun}",
    "premium {noun} built to {verb}",
    "the {noun} you need to {verb}",
]

# Short templates: ≤ 35 chars with longest noun/verb, leaving room for number + emoji
BODY_TEMPLATES_SHORT = [
    "Our {noun} lets you {verb} better.",
    "Built to {verb}. Premium {noun}.",
    "{verb} further in our new {noun}.",
    "Ride ready. Try our {noun} today.",
]

# Long templates: > 55 chars guaranteed, so always > 50 even after substitution
BODY_TEMPLATES_LONG = [
    "Engineered for performance on every terrain. Our {noun} is designed to help you {verb} with total confidence, whether you are on a mountain pass or a city commute through changing weather.",
    "Built for the long haul. Our premium {noun} combines technical fabrics with a refined fit so you can {verb} harder and go further, no matter what the forecast brings this season.",
    "Lightweight and breathable, this {noun} keeps you comfortable from the first pedal stroke to the last. Designed for riders who {verb} in all conditions and demand the very best from their gear.",
]


def _insert_number(text, rng):
    words = text.split()
    pos = rng.integers(0, max(len(words) - 1, 1))
    num = str(rng.integers(2, 30))
    words.insert(pos, num)
    return " ".join(words)


def generate_copy(df, rng, config=None):
    """Generate headline, body, and labels column consistent with sampled flags."""
    cfg = config or EFFECTS_CONFIG
    threshold = cfg["body_long_threshold"]
    headlines, bodies, labels_col = [], [], []

    for _, row in df.iterrows():
        noun = rng.choice(NOUNS)
        verb = rng.choice(VERBS)

        hl = rng.choice(HEADLINE_TEMPLATES).format(noun=noun, verb=verb)
        if row["headline_has_numbers"]:
            hl = _insert_number(hl, rng)

        if row["body_long"]:
            body = rng.choice(BODY_TEMPLATES_LONG).format(noun=noun, verb=verb)
        else:
            body = rng.choice(BODY_TEMPLATES_SHORT).format(noun=noun, verb=verb)

        if row["body_has_numbers"]:
            body = _insert_number(body, rng)

        if row["body_has_emoji"]:
            body = body + " " + rng.choice(EMOJI_POOL)

        label_parts = []
        media_label = "img_" + noun if row["media_type"] == "image" else "vid_" + noun
        label_parts.append(f"{media_label}:{'Image' if row['media_type'] == 'image' else 'Video'}")

        if "Noun" in row["label_types"]:
            label_parts.append(f"{noun}:Noun")
        if "Verb" in row["label_types"]:
            label_parts.append(f"{verb}:Verb")
        if "Phrase" in row["label_types"] and row["assigned_phrase"]:
            label_parts.append(f"{row['assigned_phrase']}:Phrase")

        headlines.append(hl)
        bodies.append(body)
        labels_col.append("|".join(label_parts))

    df["headline"] = headlines
    df["body"] = bodies
    df["labels"] = labels_col
    return df


# =============================================================================
# STEP 7 — CSV assembly & export
# =============================================================================

OUTPUT_COLUMNS = [
    "ad_id", "date", "spend", "revenue", "impressions", "clicks",
    "purchases", "headline", "body", "media_type", "aspect_ratio",
    "category", "labels",
]


def generate(n_ads, start, end, seed, out, config=None):
    """Full pipeline: sample → effect model → raw metrics → copy → CSV."""
    cfg = config or EFFECTS_CONFIG
    rng = np.random.default_rng(seed)
    months = generate_month_list(start, end)
    counts = generate_monthly_counts(n_ads, months, rng, config=cfg)
    df = sample_attributes(counts, rng, config=cfg)
    df = apply_effect_model(df, rng, start_date=start, config=cfg)
    df = compute_raw_metrics(df, rng, config=cfg)
    df = generate_copy(df, rng, config=cfg)
    df[OUTPUT_COLUMNS].to_csv(out, index=False)
    print(f"Wrote {len(df)} ads to {out}")
    return df


def _build_flipped_config():
    """Deep-copy EFFECTS_CONFIG with 3 dramatic sign reversals across all KPI tables."""
    import copy
    cfg = copy.deepcopy(EFFECTS_CONFIG)

    flips = {
        "roas_effects": {
            "media_type": {"image": 0.75, "video": 1.50},
            "headline_has_numbers": 0.70,
            "body_long": 1.40,
        },
        "ctr_effects": {
            "media_type": {"image": 0.88, "video": 1.15},
            "headline_has_numbers": 0.85,
            "body_long": 1.12,
        },
        "conv_rate_effects": {
            "media_type": {"image": 0.85, "video": 1.18},
            "headline_has_numbers": 0.82,
            "body_long": 1.15,
        },
    }
    for table, overrides in flips.items():
        for key, value in overrides.items():
            cfg[table][key] = value
    return cfg


FLIPPED_EFFECTS_CONFIG = _build_flipped_config()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic ad data")
    parser.add_argument("--n-ads", type=int, default=2650)
    parser.add_argument("--start", default="2023-01")
    parser.add_argument("--end", default="2025-01")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="ads.csv")
    parser.add_argument("--config", choices=["default", "flipped"], default="default")
    args = parser.parse_args()
    cfg = FLIPPED_EFFECTS_CONFIG if args.config == "flipped" else None
    generate(args.n_ads, args.start, args.end, args.seed, args.out, config=cfg)
