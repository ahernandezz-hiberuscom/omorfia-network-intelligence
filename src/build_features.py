"""
Geographic signals per branch: verified coordinate, drive-time catchment,
cannibalisation and competitor density.

Cannibalisation is asymmetric (computed per site, not per pair: if a large
catchment absorbs a small one, the small site loses most of its territory and
the large one barely notices) and only counts within the same customer segment.
Cross-segment overlap is computed the same way but reported separately: Jazz
Lounge Spa shares a building with Tips & Toes in four places, which is
deliberate couple-coverage, not a network error.

Outputs: group_shops_features.csv, overlap_pairs.csv, group_shops.geojson,
catchments.geojson.
"""
import csv, json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verified_locations import VERIFIED
import isochrones as iso

from shapely.geometry import Polygon

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

# row index in group_shops.csv -> (comp_1km, comp_2km, comp_3km)
#
# Derived from the same OpenStreetMap extraction as src/competitor_points.py:
# 2,606 beauty POIs across the UAE, 872 within 3 km of a group site.
#
# IMPORTANT: these counts are measured from the VERIFIED coordinate where one
# exists, not from the geocode. An earlier pass measured them from the geocodes
# and the difference moved six recommendations - the same failure mode, and the
# same size of effect, as the catchment overlap. Regenerate with:
#     python -c "import sys; sys.path.insert(0,'src'); import competitor_points as c; print(c.density(lat, lon))"
COMP = """0:0/0/1 1:0/35/70 2:0/0/1 3:0/0/1 4:0/0/2 5:1/2/3 6:2/8/8 7:1/1/2
8:1/29/51 9:27/97/222 10:4/8/12 11:8/82/180 12:3/10/12 13:2/4/22 14:1/6/8
15:3/4/9 16:1/1/6 17:0/2/2 18:0/0/1 19:2/3/6 20:0/2/2 21:0/0/2 22:4/6/11
23:1/1/6 24:1/33/69 25:0/0/0 26:0/0/1 27:0/0/1 28:2/9/11 29:2/9/11 30:0/1/1
31:0/0/0 32:1/1/4 33:9/19/31 34:6/13/38 35:0/3/14 36:0/1/4 37:0/1/11
38:35/62/63 39:12/17/18 40:1/3/7 41:0/3/11 42:1/3/10 43:0/17/70 44:0/2/5
45:0/0/0 46:0/6/57 47:0/28/50 48:2/7/18 49:0/26/67 50:0/0/0 51:0/6/29
52:0/19/77 53:0/0/1 54:0/5/49 55:0/39/177 56:1/2/3 57:0/0/0 58:4/20/38
59:11/17/48 60:1/5/23 61:0/0/0 62:0/0/0 63:2/2/3 64:1/3/7 65:0/5/49
66:2/66/81 67:1/3/9 68:2/2/3 69:0/19/77 70:0/0/1 71:0/39/177 72:0/3/11
73:0/17/70"""

R_EARTH = 6371.0
LAT0 = 24.9          # origin of the local flat projection


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def to_km(lat, lon):
    # local equirectangular projection, good enough at this scale
    return (lon * 111.320 * math.cos(math.radians(LAT0)), lat * 110.574)


def shapely_catchment(shop_id, lat, lon):
    pts, fallback = iso.polygon(shop_id, lat, lon)
    return Polygon([to_km(la, lo) for la, lo in pts]), fallback, pts


def parse_comp():
    out = {}
    for tok in COMP.split():
        i, vals = tok.split(":")
        out[int(i)] = [int(v) for v in vals.split("/")]
    return out


def main():
    shops = list(csv.DictReader(open(DATA / "group_shops.csv", encoding="utf-8")))
    comp = parse_comp()

    n_fixed, max_shift = 0, 0.0
    for i, s in enumerate(shops):
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])
        if s["shop_id"] in VERIFIED:
            vlat, vlon = VERIFIED[s["shop_id"]]
            shift = haversine(s["lat"], s["lon"], vlat, vlon)
            max_shift = max(max_shift, shift)
            n_fixed += shift > 0.05
            s["geocode_shift_km"] = round(shift, 3)
            s["lat"], s["lon"] = vlat, vlon
            s["geo_confidence"] = "verified"
        else:
            s["geocode_shift_km"] = ""
        c = comp.get(i, [0, 0, 0])
        s["comp_1km"], s["comp_2km"], s["comp_3km"] = c

    # ---- drive-time catchment areas ----
    geoms, rings = {}, {}
    n_fb = 0
    for s in shops:
        g, fb, pts = shapely_catchment(s["shop_id"], s["lat"], s["lon"])
        geoms[s["shop_id"]] = g
        rings[s["shop_id"]] = pts
        s["catchment_km2"] = round(g.area, 2)
        s["catchment_source"] = ("circle_2km" if fb
                                 else f"isochrone_{iso.THRESHOLD_S//60}min")
        n_fb += fb

    # ---- cannibalisation ----
    pairs = []
    for a in shops:
        ga = geoms[a["shop_id"]]
        same_seg, cross_seg, worst = 0.0, 0.0, None
        for b in shops:
            if a["shop_id"] == b["shop_id"]:
                continue
            gb = geoms[b["shop_id"]]
            if not ga.intersects(gb):
                continue
            inter = ga.intersection(gb).area
            if inter <= 0 or ga.area <= 0:
                continue
            frac = inter / ga.area           # fraction OF A that it shares with B
            d = haversine(a["lat"], a["lon"], b["lat"], b["lon"])

            # Quality control: two sites geocoded to the same centroid give a
            # distance of ~0 and total overlap. That is an artifact, not a finding.
            artifact = d < 0.15 and not (
                a["geo_confidence"] in ("high", "verified")
                and b["geo_confidence"] in ("high", "verified"))

            pairs.append({
                "shop_id": a["shop_id"], "other_id": b["shop_id"],
                "other_brand": b["brand"], "distance_km": round(d, 3),
                "overlap_frac": round(frac, 4),
                "overlap_km2": round(inter, 3),
                "same_segment": a["segment"] == b["segment"],
                "geocode_artifact": artifact,
            })
            if artifact:
                continue
            if a["segment"] == b["segment"]:
                if frac > same_seg:
                    same_seg = frac
                if worst is None or frac > worst[1]:
                    worst = (b["shop_id"], frac, b["brand"], round(d, 2))
            else:
                cross_seg = max(cross_seg, frac)

        a["cannibalisation"] = round(same_seg, 4)
        a["cross_segment_overlap"] = round(cross_seg, 4)
        a["worst_overlap_with"] = worst[0] if worst else ""
        a["worst_overlap_brand"] = worst[2] if worst else ""
        a["worst_overlap_km"] = worst[3] if worst else ""
        a["n_group_shops_2km"] = sum(
            1 for b in shops if b["shop_id"] != a["shop_id"]
            and haversine(a["lat"], a["lon"], b["lat"], b["lon"]) <= 2.0)

    cols = list(shops[0].keys())
    with open(DATA / "group_shops_features.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(shops)
    with open(DATA / "overlap_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys())); w.writeheader(); w.writerows(pairs)

    (DATA / "group_shops.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
             "properties": {k: v for k, v in s.items() if k not in ("lat", "lon")}}
            for s in shops]}, ensure_ascii=False), encoding="utf-8")

    (DATA / "catchments.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Polygon",
                          "coordinates": [[[lo, la] for la, lo in rings[s["shop_id"]]]]},
             "properties": {"shop_id": s["shop_id"], "brand": s["brand"],
                            "branch_name": s["branch_name"],
                            "segment": s["segment"],
                            "source": s["catchment_source"],
                            "area_km2": s["catchment_km2"]}}
            for s in shops]}, ensure_ascii=False), encoding="utf-8")

    n_art = sum(1 for p in pairs if p["geocode_artifact"])
    print(f"Verified coordinates : {n_fixed} corrected (max {max_shift:.1f} km)")
    print(f"Catchment            : {iso.THRESHOLD_S//60}-min isochrone "
          f"({len(shops)-n_fb} sites), fallback circle ({n_fb})")
    print(f"Overlapping pairs    : {len(pairs)} ({n_art} artifacts excluded)\n")

    hot = [s for s in sorted(shops, key=lambda x: -x["cannibalisation"])
           if s["cannibalisation"] > 0][:14]
    print("Internal cannibalisation (same customer segment, real catchment area):")
    for s in hot:
        print(f"  {s['cannibalisation']*100:5.1f}%  {s['brand']:<16}{s['branch_name']:<26}"
              f" vs {s['worst_overlap_brand']:<14} ({s['worst_overlap_km']} km)")


if __name__ == "__main__":
    main()
