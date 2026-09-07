"""
Price positioning of Bedashing against Tips & Toes.

The cannibalisation model assumes both brands compete for the same customer.
If one were premium and the other budget that assumption would be false and the
cannibalisation axis inflated, so this exists to test it.

A comparable basket of standard manicure services from each brand's online
booking store (both run on Zenoti), 2026-09-07. Manicure is the only service
named equivalently in both catalogues.

Prices do not vary by branch: Eyebrow Lamination is AED 262.50 and Back Massage
AED 157.50 at both Khalifa City A and City Walk. Price is a brand decision, so
this sits at brand level and does not enter the per-branch score.
"""

# normalised service -> (bedashing_aed, tips_and_toes_aed)
BASKET = {
    "basic_manicure":      (85.0,  90.0),   # Bedashing "Manicure" / T&T "Basic Manicure"
    "express_manicure":    (105.0, 100.0),  # "File Manicure" / "Express Manicure"
    "russian_manicure":    (152.0, 120.0),  # "Russian Manicure" / "Russian Manicure"
}

# Other observed prices, not matchable one to one but useful as context
CONTEXT = {
    "Bedashing": {
        "Eyebrow Lamination": 262.5, "Back Massage": 157.5,
        "Manicure Gel Polish": 135.0, "Shape & Polish Change": 60.0,
        "Gel Polish Removal": 37.0, "Stick On Nails Set": 120.0,
        "Hair treatments": (262.5, 525.0), "Balayage/highlights": 1050.0,
    },
    "Tips & Toes": {
        "Signature Manicure": 210.0, "Builder Gel Manicure": 210.0,
        "Russian File Manicure": 115.0, "Little Princess Manicure": 50.0,
        "Moroccan Hammam Ritual": 250.0, "InfraSlim X": 350.0,
        "Hydrating facial": 550.0, "Hair treatment": 400.0,
    },
}


def price_index():
    """Bedashing price index against Tips & Toes. 1.00 means identical."""
    bd = sum(v[0] for v in BASKET.values())
    tt = sum(v[1] for v in BASKET.values())
    return bd / tt, bd, tt


def verdict():
    idx, bd, tt = price_index()
    same_tier = 0.80 <= idx <= 1.25
    return {
        "index": round(idx, 3),
        "basket_bedashing_aed": bd,
        "basket_tips_and_toes_aed": tt,
        "same_price_tier": same_tier,
        "conclusion": (
            "Both brands operate in the same price tier: the comparable "
            f"basket differs by {abs(idx-1)*100:.0f}%. The hypothesis that they "
            "compete for the same customer HOLDS, so the cannibalisation metric "
            "is valid."
            if same_tier else
            "The brands sit in different price tiers: the measured "
            "cannibalisation is overstated and would need to be discounted."
        ),
    }


if __name__ == "__main__":
    v = verdict()
    print("Comparable manicure basket (AED)")
    print(f"{'service':<22}{'Bedashing':>11}{'Tips & Toes':>13}{'diff':>8}")
    for k, (b, t) in BASKET.items():
        print(f"{k:<22}{b:>11.0f}{t:>13.0f}{(b/t-1)*100:>7.0f}%")
    print(f"{'TOTAL':<22}{v['basket_bedashing_aed']:>11.0f}"
          f"{v['basket_tips_and_toes_aed']:>13.0f}"
          f"{(v['index']-1)*100:>7.0f}%")
    print(f"\nBedashing/T&T price index: {v['index']}")
    print(f"Same price tier: {'YES' if v['same_price_tier'] else 'NO'}")
    print("\n" + v["conclusion"])
