"""
Decision engine: PROTECT / HOLD / SHRINK.

Four normalised signals, one weighted sum, explicit thresholds. No trained
model: see docs/02_decision_model.md for why.

Scored universe: women's segment (Bedashing + Tips & Toes) with a rating
available. Jazz Lounge Spa is a men's spa and does not compete for the same
customer, so it is excluded from the score.
"""
import csv, math, pathlib, random, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ratings import RATINGS
from review_themes import summary_line

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

# --- Base weights. A business decision, not an output of the data. ---
W_HEALTH, W_ATTRACT, W_CANNIB = 0.40, 0.35, 0.25

# How hard competition discounts demand when scoring a market.
#
# The first version used percentile(demand) - percentile(pressure), which puts
# the two on equal footing. Ras Al Khaimah has 32 retail POIs within 2 km and
# zero competitors, and that formula ranked its market in the 92nd percentile.
# An empty region is not attractive just because nobody else is there; there is
# nobody to serve. So demand leads and competition discounts it, on raw
# magnitudes rather than ranks, with LAMBDA < 1 so demand always dominates.
LAMBDA_COMPETITION = 0.5

# Classification thresholds, as percentiles of the scored universe.
P_PROTECT, P_SHRINK = 66, 33
CANNIB_ALERT = 30.0     # above this, the head-to-head duel kicks in


def pct_rank(values):
    """0-100 percentile of each value, ties averaged."""
    order = sorted(values)
    n = len(order)
    out = []
    for v in values:
        lo = order.index(v)
        hi = n - 1 - order[::-1].index(v)
        out.append(100.0 * ((lo + hi) / 2) / (n - 1) if n > 1 else 50.0)
    return out


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    return s[int(k)] if f == c else s[f] + (s[c] - s[f]) * (k - f)


# Guardrail. A bare percentile cut forces a third of the network into SHRINK
# even when the network is healthy: a percentile says which site is relatively
# worst, not which one is unviable. So SHRINK also demands a nameable cause,
# either cannibalisation or poor health.
MIN_CANNIB_FOR_SHRINK = 30.0
MAX_HEALTH_FOR_SHRINK = 40.0


def classify(score, thr_protect, thr_shrink, cannib=None, health=None):
    if score >= thr_protect:
        return "PROTECT"
    if score < thr_shrink:
        if cannib is None or health is None:
            return "SHRINK"
        if cannib >= MIN_CANNIB_FOR_SHRINK or health < MAX_HEALTH_FOR_SHRINK:
            return "SHRINK"
        return "HOLD"      # relatively weak, but with no cause that justifies it
    return "HOLD"


def reason_for(s):
    r, bits = s["recommendation"], []
    if s["sig_cannib"] >= MIN_CANNIB_FOR_SHRINK:
        bits.append(f"it shares {s['sig_cannib']:.0f}% of its catchment with "
                    f"{s['worst_overlap_brand']} "
                    f"{s.get('worst_overlap_name') or s['worst_overlap_with']} "
                    f"{s['worst_overlap_km']} km away")
    if s["sig_health"] < MAX_HEALTH_FOR_SHRINK:
        bits.append(f"health at network percentile {s['sig_health']:.0f} "
                    f"({s['rating']} from {s['n_reviews']} reviews)")
    elif s["sig_health"] >= 75:
        bits.append(f"health at percentile {s['sig_health']:.0f} "
                    f"({s['rating']} from {s['n_reviews']} reviews)")
    if s["sig_attract"] < 25:
        bits.append(f"weak market (demand p{s['sig_demand']:.0f}, competitive "
                    f"pressure p{s['sig_pressure']:.0f})")
    elif s["sig_attract"] >= 70:
        bits.append(f"attractive market (demand p{s['sig_demand']:.0f}, "
                    f"pressure p{s['sig_pressure']:.0f})")
    if not bits:
        bits.append("no dominant signal; nothing stands out either way")
    head = {"PROTECT": "Protect because", "HOLD": "Hold:",
            "SHRINK": "Shrink or do not renew because"}[r]
    txt = head + " " + "; ".join(bits) + "."
    th = summary_line(s["shop_id"])
    if th:
        txt += " " + th
    return txt


MALL_WORDS = ("mall", "centre", "center", "souk", "plaza", "pavilion", "walk")


def load():
    shops = list(csv.DictReader(open(DATA / "group_shops_features.csv", encoding="utf-8")))
    demand = {r["shop_id"]: r
              for r in csv.DictReader(open(DATA / "demand_density.csv", encoding="utf-8"))}
    for s in shops:
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])
        d = demand[s["shop_id"]]
        for km in ("1km", "2km", "3km"):
            s["demand_" + km] = int(d["demand_" + km])
        r = RATINGS.get(s["shop_id"])
        s["rating"], s["n_reviews"] = (r[0], r[1]) if r else ("", "")
        s["rating_confidence"] = r[2] if r else "missing"
        s["cannibalisation"] = float(s["cannibalisation"])
        s["comp_2km"] = int(s["comp_2km"])
        s["in_mall"] = any(k in s["address"].lower() for k in MALL_WORDS)
    return shops


def main():
    shops = load()

    scored = [s for s in shops if s["segment"] == "women" and s["rating"] != ""]
    scored_ids = {s["shop_id"] for s in scored}
    skipped = [s for s in shops if s["shop_id"] not in scored_ids]
    print(f"Scored universe: {len(scored)} women's-segment branches")
    print(f"Excluded: {len(skipped)} ({sum(1 for s in skipped if s['segment']=='men')} men's "
          f"segment, {sum(1 for s in skipped if s['segment']=='women')} with no rating)\n")

    # ---------------- signals normalised 0-100 ----------------
    # Health: rating weighted by review volume.
    # log(reviews) because the information value of a review decays: going from
    # 100 to 200 says a lot, from 2,000 to 2,100 says almost nothing.
    health_raw = [s["rating"] * math.log10(s["n_reviews"] + 10) for s in scored]
    demand_raw = [math.log10(s["demand_2km"] + 10) for s in scored]
    press_raw = [math.log10(s["comp_2km"] + 10) for s in scored]
    # Market attractiveness: demand discounted by competition, on magnitudes.
    attract_raw = [math.log10(s["demand_2km"] + 1)
                   - LAMBDA_COMPETITION * math.log10(s["comp_2km"] + 1)
                   for s in scored]

    for s, h, d, p in zip(scored, pct_rank(health_raw), pct_rank(demand_raw), pct_rank(press_raw)):
        s["sig_health"] = round(h, 1)
        s["sig_demand"] = round(d, 1)
        s["sig_pressure"] = round(p, 1)
        s["sig_cannib"] = round(s["cannibalisation"] * 100, 1)

    for s, a in zip(scored, pct_rank(attract_raw)):
        s["sig_attract"] = round(a, 1)

    # ---------------- score and classification ----------------
    for s in scored:
        s["c_health"] = round(W_HEALTH * s["sig_health"], 2)
        s["c_attract"] = round(W_ATTRACT * s["sig_attract"], 2)
        s["c_cannib"] = round(-W_CANNIB * s["sig_cannib"], 2)
        s["score"] = round(s["c_health"] + s["c_attract"] + s["c_cannib"], 2)

    all_scores = [s["score"] for s in scored]
    thr_p = percentile(all_scores, P_PROTECT)
    thr_s = percentile(all_scores, P_SHRINK)
    for s in scored:
        s["recommendation"] = classify(s["score"], thr_p, thr_s,
                                       s["sig_cannib"], s["sig_health"])

    # ---------------- head-to-head duel on overlapping pairs ----------------
    by_id = {s["shop_id"]: s for s in scored}
    for s in scored:
        s["duel"] = ""
        w = s["worst_overlap_with"]
        s["worst_overlap_name"] = by_id[w]["branch_name"] if w in by_id else ""
        if s["sig_cannib"] >= CANNIB_ALERT and w in by_id:
            other = by_id[w]
            if s["sig_health"] < other["sig_health"]:
                s["duel"] = f"loses to {other['brand']} {other['branch_name']}"
            elif s["sig_health"] > other["sig_health"]:
                s["duel"] = f"beats {other['brand']} {other['branch_name']}"
            else:
                s["duel"] = "tied"

    # ---------------- sensitivity analysis ----------------
    # Which recommendations hold if the weights move within a reasonable range?
    # This answers the brief's "where should we trust the model, and where
    # should we be careful?" far better than any model accuracy metric would.
    random.seed(7)
    N = 2000
    votes = {s["shop_id"]: {"PROTECT": 0, "HOLD": 0, "SHRINK": 0} for s in scored}
    for _ in range(N):
        wh = max(0.05, random.gauss(W_HEALTH, 0.08))
        wa = max(0.05, random.gauss(W_ATTRACT, 0.08))
        wc = max(0.05, random.gauss(W_CANNIB, 0.08))
        tot = wh + wa + wc
        wh, wa, wc = wh / tot, wa / tot, wc / tot
        sc = [wh * s["sig_health"] + wa * s["sig_attract"] - wc * s["sig_cannib"] for s in scored]
        tp, ts = percentile(sc, P_PROTECT), percentile(sc, P_SHRINK)
        for s, v in zip(scored, sc):
            votes[s["shop_id"]][classify(v, tp, ts, s["sig_cannib"], s["sig_health"])] += 1

    for s in scored:
        v = votes[s["shop_id"]]
        s["stability"] = round(100.0 * v[s["recommendation"]] / N, 1)
        s["robust"] = "robust" if s["stability"] >= 85 else \
                      "medium" if s["stability"] >= 60 else "FRAGILE"

    for s in scored:
        s["reason"] = reason_for(s)

    # ---------------- outputs ----------------
    cols = ["shop_id", "brand", "branch_name", "emirate", "address", "lat", "lon",
            "geo_confidence", "in_mall", "rating", "n_reviews", "rating_confidence",
            "demand_2km", "comp_2km", "cannibalisation", "worst_overlap_with",
            "worst_overlap_brand", "worst_overlap_km",
            "sig_health", "sig_demand", "sig_pressure", "sig_attract", "sig_cannib",
            "c_health", "c_attract", "c_cannib", "score",
            "recommendation", "stability", "robust", "duel", "reason"]
    with open(DATA / "master.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(scored, key=lambda s: -s["score"]))

    # console report, Bedashing only (the brand the brief is about)
    bd = sorted([s for s in scored if s["brand"] == "Bedashing"], key=lambda s: s["score"])
    print(f"Thresholds:  SHRINK < {thr_s:.1f}   |   PROTECT >= {thr_p:.1f}\n")
    print("BEDASHING · 24 branches, worst to best")
    print(f"{'branch':<26}{'score':>7} {'rec':<9}{'stab':>6}  {'hlth':>6}{'attr':>6}{'cann':>6}  duel")
    for s in bd:
        print(f"{s['branch_name'][:25]:<26}{s['score']:>7.1f} {s['recommendation']:<9}"
              f"{s['stability']:>5.0f}%  {s['sig_health']:>6.0f}{s['sig_attract']:>6.0f}"
              f"{s['sig_cannib']:>6.0f}  {s['duel']}")

    print("\nBedashing split:", {r: sum(1 for s in bd if s["recommendation"] == r)
                                  for r in ("PROTECT", "HOLD", "SHRINK")})
    frag = [s for s in scored if s["robust"] == "FRAGILE"]
    print(f"Fragile recommendations across the universe: {len(frag)}")
    for s in frag:
        print(f"   ! {s['brand']} {s['branch_name']} - {s['recommendation']} only "
              f"{s['stability']}% of the time")


if __name__ == "__main__":
    main()
