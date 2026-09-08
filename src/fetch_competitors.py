"""
First-pass extraction of external competition (salons, hairdressers, spas,
massage centres) from OpenStreetMap via the Overpass API.

    python src/fetch_competitors.py

SUPERSEDED, kept for provenance. This pass queried `node` only, so it missed
the 61 competitors mapped as building polygons, and it measured per-branch
densities against the pre-verification geocodes. It returned 2,543 POIs across
the UAE, 1,129 of them within 3 km of a group branch.

The extraction actually used by the model is the `nwr` re-run of 2026-09-07,
committed inline in src/competitor_points.py (2,606 POIs, 872 within 3 km) with
the per-branch counts in the COMP table of src/build_features.py. Nothing in
the pipeline reads the two CSVs this script writes, so you never need to run it.

On reproducibility: OpenStreetMap changes daily, so a re-run will not reproduce
either set of numbers exactly.
"""
import csv, json, math, pathlib, urllib.parse, urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = (22.6, 51.5, 26.2, 56.5)          # the whole UAE: S, W, N, E
RADII_KM = (1, 2, 3)

QUERY = """[out:json][timeout:180];
(
  node["shop"="beauty"]({s},{w},{n},{e});
  node["shop"="hairdresser"]({s},{w},{n},{e});
  node["leisure"="spa"]({s},{w},{n},{e});
  node["shop"="massage"]({s},{w},{n},{e});
);
out tags center;"""

R_EARTH = 6371.0


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def fetch():
    q = QUERY.format(s=BBOX[0], w=BBOX[1], n=BBOX[2], e=BBOX[3])
    body = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(
        OVERPASS, data=body,
        headers={"User-Agent": "omorfia-network-case-study/1.0 (interview exercise)"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


KIND = {("shop", "beauty"): "beauty", ("shop", "hairdresser"): "hairdresser",
        ("shop", "massage"): "massage", ("leisure", "spa"): "spa"}


def kind_of(tags):
    for (k, v), name in KIND.items():
        if tags.get(k) == v:
            return name
    return "other"


def main():
    shops = list(csv.DictReader(open(DATA / "group_shops.csv", encoding="utf-8")))
    for s in shops:
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])

    print("Querying the Overpass API...")
    data = fetch()
    pois = [e for e in data["elements"] if e.get("lat") and e.get("lon")]
    print(f"  {len(pois)} competitor POIs across the UAE")

    # keep only the relevant ones: within 3 km of a group branch
    rows, counts = [], {s["shop_id"]: [0] * len(RADII_KM) for s in shops}
    for e in pois:
        tags = e.get("tags", {})
        dmin = min(haversine(s["lat"], s["lon"], e["lat"], e["lon"]) for s in shops)
        for s in shops:
            d = haversine(s["lat"], s["lon"], e["lat"], e["lon"])
            for i, rk in enumerate(RADII_KM):
                if d <= rk:
                    counts[s["shop_id"]][i] += 1
        if dmin <= max(RADII_KM):
            rows.append({
                "osm_id": e["id"],
                "name": tags.get("name", ""),
                "kind": kind_of(tags),
                "lat": round(e["lat"], 6),
                "lon": round(e["lon"], 6),
                "nearest_group_shop_km": round(dmin, 3),
            })

    with open(DATA / "competitors_osm.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    with open(DATA / "competitor_density.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["shop_id"] + [f"comp_{r}km" for r in RADII_KM])
        for sid, c in counts.items():
            w.writerow([sid] + c)

    print(f"competitors_osm.csv     -> {len(rows)} competitors within 3 km of the group")
    print(f"competitor_density.csv  -> {len(counts)} rows")


if __name__ == "__main__":
    main()
