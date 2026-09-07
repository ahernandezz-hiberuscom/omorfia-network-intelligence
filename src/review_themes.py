"""
Review topics from the "chips" Google Maps builds on each place page
(aria-labels of the form "pedicure, mentioned in 62 reviews").

The rating says how well a branch is doing; the topics say why. They do not
enter the score: the chips carry no polarity, so turning them into a number
would need sentiment analysis over the full review text. They enrich the
written reason and the AI layer instead.

Collected 2026-09-07, 23 of 24 Bedashing branches.

Google's extraction is unsupervised and picks up staff names ("faouzia") and
mis-parses ("cherry", "poetry", "rage"). They are left in rather than quietly
cleaned; only the topics in OPERATIONAL_FLAGS are acted on.
"""

# shop_id -> [(topic, number of reviews mentioning it), ...]
THEMES = {
    "bd_al_barsha": [("services", 123), ("pedicure", 41), ("hammam", 22),
                     ("technician", 20), ("blow dry", 12), ("hair care", 10)],
    "bd_al_falah": [("cherry", 25), ("poetry", 18), ("artists", 18), ("rage", 17)],
    "bd_al_maqta": [("technician", 79), ("bid", 41), ("hammam", 22),
                    ("blow dry", 15), ("receptionist", 9)],
    "bd_baniyas": [("services", 60), ("nails", 11), ("technician", 11), ("receptionist", 9)],
    "bd_city_walk": [("services", 98), ("manicure", 39), ("technician", 13),
                     ("threading", 11), ("atmosphere", 10), ("blow dry", 10)],
    "bd_delma": [("services", 75), ("manicure", 30), ("technician", 24),
                 ("eyebrows", 19), ("receptionist", 11)],
    "bd_jumeirah_park": [("pedicure", 62), ("services", 45), ("technician", 21),
                         ("smile", 11), ("princess", 9), ("blow dry", 7),
                         ("treatment", 7)],
    "bd_khaleej_al_arabi": [("technician", 86), ("receptionist", 32), ("hair colour", 19),
                            ("books", 16), ("poetry", 10), ("hot chocolate", 9)],
    "bd_khalifa_city_a": [("technician", 137), ("receptionist", 54), ("hair colour", 41),
                          ("blow dry", 37), ("front desk", 10)],
    "bd_ministries_complex": [("technician", 61), ("treatment", 15), ("blow dry", 14),
                              ("threading", 10), ("asmahan", 8)],
    "bd_mirdif_35": [("services", 121), ("pedicure", 59), ("technician", 35),
                     ("workmanship", 24), ("cleanliness", 21), ("hair dye", 19),
                     ("blow dry", 8)],
    "bd_mohammed_bin_zayed_city": [("services", 52), ("technician", 35), ("eyebrows", 31),
                                   ("poetry", 16)],
    "bd_nad_al_sheba": [("services", 68), ("pedicure", 41), ("blow dry", 30),
                        ("receptionist", 12)],
    "bd_al_ain": [("services", 166), ("pedicure", 50), ("treatment", 22), ("faouzia", 22)],
    "bd_al_jada": [("services", 40), ("pedicure", 34), ("eyebrows", 24), ("cleanliness", 19)],
    "bd_al_taif_mall": [("services", 43), ("moroccan bath", 27), ("workmanship", 18),
                        ("hair colour", 16)],
    "bd_noya_plaza": [("pedicure", 22), ("technician", 9), ("blow dry", 8), ("foot", 7)],
    "bd_ras_al_khaimah": [("services", 38), ("hair colour", 27), ("pedicure", 22),
                          ("workmanship", 19)],
    "bd_shahama": [("services", 50), ("eyebrows", 38), ("fun", 18), ("technician", 15)],
    "bd_shakhbout_city": [("services", 97), ("technician", 58), ("cleanliness", 25),
                          ("nails", 23)],
    "bd_west_yas": [("services", 53), ("technician", 52), ("nails", 19), ("flat iron", 10)],
    "bd_zawaya_walk": [("services", 46), ("pedicure", 22), ("products", 12), ("blow dry", 9)],
    "bd_zayed_international_airport": [("manicure", 73), ("flight", 58), ("layover", 26),
                                       ("blow dry", 12)],
}

# Topics that, when they show up with weight, point at a concrete operational
# issue. Google's chips carry no sentiment, so this is a business reading of
# what deserves a look, not an automatic classification.
OPERATIONAL_FLAGS = {
    "cleanliness": "in-store hygiene",
    "receptionist": "front-desk experience, booking or welcome",
    "front desk": "front-desk experience, booking or welcome",
    "wait": "waiting times",
    "price": "price perception",
    "appointment": "appointment handling",
}


def flagged(shop_id):
    """Topics for this branch that point at operations, not at the menu."""
    out, seen = [], set()
    for topic, n in THEMES.get(shop_id, []):
        for k, desc in OPERATIONAL_FLAGS.items():
            if k in topic.lower() and desc not in seen:
                seen.add(desc)
                out.append((topic, n, desc))
    return out


def summary_line(shop_id):
    """Short, data-anchored sentence, ready for the narrator."""
    th = THEMES.get(shop_id)
    if not th:
        return ""
    top = ", ".join(f"{t} ({n})" for t, n in th[:3])
    line = f"Customers mostly talk about {top}."
    fl = flagged(shop_id)
    if fl:
        line += " Operational signals worth a look: " + ", ".join(
            f"{desc} ({n} mentions)" for _, n, desc in fl) + "."
    return line


if __name__ == "__main__":
    print(f"Topics collected for {len(THEMES)} branches\n")
    for sid in sorted(THEMES):
        print(f"{sid}\n  {summary_line(sid)}\n")
