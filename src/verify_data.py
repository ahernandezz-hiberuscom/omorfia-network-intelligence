"""
Sanity checks over the dataset, run after build_features.py. The point is to
stop a silent geocoding error from reaching the decision model.
"""

import csv, pathlib, collections

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

# Approximate bounding boxes per emirate (lat_min, lat_max, lon_min, lon_max)
BOX = {
    "Abu Dhabi":      (22.6, 25.0, 51.5, 56.0),
    "Dubai":          (24.8, 25.4, 54.9, 55.6),
    "Sharjah":        (25.2, 25.6, 55.3, 56.4),
    "Ras Al Khaimah": (25.5, 26.2, 55.6, 56.2),
    "Fujairah":       (25.0, 25.8, 56.0, 56.4),
}

fails, warns = [], []


def main():
    shops = list(csv.DictReader(open(DATA / "group_shops_features.csv", encoding="utf-8")))
    print(f"Verifying {len(shops)} branches\n")

    seen_coord = collections.defaultdict(list)
    for s in shops:
        lat, lon = float(s["lat"]), float(s["lon"])
        tag = f"{s['brand']} {s['branch_name']}"

        # 1. inside the UAE
        if not (22.5 <= lat <= 26.2 and 51.4 <= lon <= 56.5):
            fails.append(f"OUTSIDE THE UAE: {tag} ({lat},{lon})")

        # 2. consistent with the declared emirate
        box = BOX.get(s["emirate"])
        if box and not (box[0] <= lat <= box[1] and box[2] <= lon <= box[3]):
            fails.append(f"EMIRATE MISMATCH: {tag} says {s['emirate']} but falls at ({lat},{lon})")

        # 3. exact duplicate coordinates
        seen_coord[(round(lat, 5), round(lon, 5))].append(tag)

        # 4. zero competition in an urban area = suspicious
        if s["emirate"] in ("Dubai", "Sharjah") and int(s["comp_3km"]) == 0:
            warns.append(f"NO COMPETITION within 3 km in an urban area: {tag} (bad coordinate?)")

    dupes = {k: v for k, v in seen_coord.items() if len(v) > 1}
    for coord, names in dupes.items():
        warns.append(f"SHARED COORDINATE {coord}: " + " | ".join(names))

    low = [s for s in shops if s["geo_confidence"] == "low"]

    print(f"Blocking errors : {len(fails)}")
    for f in fails:
        print("   ✗", f)
    print(f"\nWarnings        : {len(warns)}")
    for w in warns:
        print("   !", w)
    print(f"\nLow-confidence coordinates: {len(low)}")
    for s in low:
        print(f"   ~ {s['brand']} {s['branch_name']} — {s['address']}")

    print("\nSummary by brand:")
    for b, n in collections.Counter(s["brand"] for s in shops).items():
        print(f"   {b:<18} {n}")
    print("\nSummary by emirate:")
    for e, n in sorted(collections.Counter(s["emirate"] for s in shops).items()):
        print(f"   {e:<18} {n}")

    print("\nVERDICT:", "FIT for analysis" if not fails else "REVIEW BEFORE PROCEEDING")


if __name__ == "__main__":
    main()
