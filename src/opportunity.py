"""
Opportunity layer: GROW / WATCH / SKIP over the territory.

The two classifications live in different geographic units. PROTECT/HOLD/SHRINK
is one row per site; GROW/WATCH/SKIP is one row per zone, here a 0.02-degree
grid cell (~2.2 x 2.0 km), which is the scale an expansion director thinks at.

Signals per cell: demand (retail and service POIs), saturation (competing
salons), coverage (group catchments reaching the cell centre, using the real
isochrones), and residential / industrial landuse polygons within 2 km.

  GROW    high demand, no group coverage, competition not extreme, and the
          zone has a residential catchment
  WATCH   high demand but half covered, saturated, or not residential
  SKIP    low demand, or fully covered

The residential test exists because without it the top GROW zones were
Musaffah, Khalid Port, Al Quoz Industrial and Dubai International Airport:
places thick with OSM points and thin on people who live there. The flaw was
invisible while the output was grid ids and obvious once the cells were named.

Scope: the Abu Dhabi and Dubai metropolitan areas, 192 cells with at least 15
POIs. OSM extraction 2026-09-07.
"""
import csv, json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import isochrones as iso
from shapely.geometry import Polygon, Point

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

STEP, LAT0, LON0 = 0.02, 24.0, 54.0
LATREF = 24.9

# "latIdx_lonIdx,poi,competitors"
GRID_RAW = """
61_71,67,3 62_65,721,70 63_65,3485,106 63_66,805,60 58_61,97,11 52_55,25,0
64_67,185,38 61_69,59,4 65_68,431,70 54_57,182,18 68_69,350,18 67_68,24,3
59_63,273,7 57_61,106,0 58_62,136,11 55_61,74,0 65_70,173,1 65_71,77,0
69_73,329,22 56_60,129,1 62_66,272,19 62_64,333,23 52_58,23,3 56_59,41,3
56_61,97,3 61_64,84,6 61_65,183,9 54_56,23,1 61_66,19,0 63_64,798,7
55_57,43,4 54_58,128,13 64_68,476,58 64_69,275,24 67_70,604,46 65_69,429,42
66_69,964,124 63_67,168,10 60_63,205,17 65_72,60,1 51_55,30,3 55_59,217,29
67_69,1680,134 53_57,192,19 57_60,64,13 63_68,109,5 56_69,15,0 55_69,76,10
53_56,260,25 57_70,33,4 59_70,66,3 55_58,58,3 69_72,513,57 52_62,51,4
66_68,343,63 59_61,57,6 59_62,95,5 62_68,80,2 58_70,67,4 60_70,45,1
62_72,15,1 57_59,51,0 54_59,32,1 55_56,28,0 61_63,610,34 58_68,26,1
52_56,59,4 55_60,288,34 61_62,59,3 60_62,140,6 70_71,483,24 69_71,250,28
68_73,34,2 70_72,1036,67 63_69,103,4 70_75,169,20 69_74,90,2 57_62,196,23
56_62,57,0 63_71,55,4 64_70,44,3 70_73,55,1 63_70,33,2 71_75,58,4
64_66,122,8 60_68,25,1 61_67,103,1 51_57,61,4 61_68,79,0 54_60,23,3
48_53,17,0 60_64,26,1 55_68,112,7 52_60,57,12 62_67,103,7 64_72,25,0
67_71,35,2 59_67,83,0 52_59,22,2 67_73,25,0 71_77,29,2 71_76,28,1
58_69,18,0 49_59,27,1 51_59,16,1 59_64,63,5 51_63,24,2 68_70,83,2
59_68,50,0 62_63,24,0 53_60,41,3 66_71,78,4 69_75,157,15 70_74,52,7
66_70,114,2 65_73,15,0 45_48,20,0 69_76,23,4 58_60,65,3 60_69,19,2
52_61,35,5 64_65,28,2 68_75,15,0 64_71,22,1 53_61,26,5 53_65,33,0
69_70,41,3 57_64,16,3 67_81,37,1 49_54,17,0 71_78,16,1 45_50,32,0
59_69,20,2 61_73,31,2 68_72,22,2 66_76,17,0 55_62,15,0 53_62,26,5
46_50,20,0 57_69,24,5 52_57,27,3 24_18,2144,184 23_16,116,8 18_24,93,7
17_23,20,0 23_17,670,76 21_22,78,3 24_17,217,10 22_18,34,4 22_16,28,0
22_19,212,12 23_18,675,59 23_19,250,23 25_18,160,13 20_24,51,1 26_33,59,2
26_18,46,0 16_26,495,22 21_21,224,32 17_26,104,2 24_19,381,41 27_34,21,2
21_20,136,8 18_25,451,10 22_20,137,20 22_30,69,9 21_28,30,2 21_23,26,0
26_20,29,2 24_20,39,3 18_26,46,1 21_30,27,1 15_31,32,2 19_25,48,1
25_19,34,0 20_28,23,0 26_21,28,1 24_30,304,2 22_33,27,5 20_22,20,0
15_26,45,6 20_23,40,3 21_32,31,2 17_25,126,8 14_31,32,0 17_24,117,6
14_32,24,0 20_25,30,1 26_34,31,3 29_35,16,3 20_17,18,0 11_34,16,0
"""

# Thresholds, as percentiles of the cells themselves. A business decision.
P_DEMAND_HIGH = 60      # above this, the zone "carries" a salon
P_SATURATED = 85        # above this, the market is crowded

# "residential/industrial" landuse polygon counts within 2 km of the cell centre.
# OSM landuse=residential and landuse=industrial, extracted 2026-09-07.
LANDUSE_RAW = """61_71:3/0 62_65:5/0 63_65:3/0 63_66:2/0 58_61:13/1 52_55:1/8 64_67:5/18 61_69:2/7 65_68:3/0 54_57:34/6 68_69:12/2 67_68:14/4 59_63:43/4 57_61:18/6 58_62:19/2 55_61:10/6 65_70:0/8 65_71:0/6 69_73:8/5 56_60:4/3 62_66:4/1 62_64:84/1 52_58:85/2 56_59:4/2 56_61:1/17 61_64:126/2 61_65:64/0 54_56:10/2 61_66:7/2 63_64:7/0 55_57:39/2 54_58:33/1 64_68:3/9 64_69:0/4 67_70:12/2 65_69:1/4 66_69:2/2 63_67:5/19 60_63:77/27 65_72:42/3 51_55:4/11 55_59:31/7 67_69:14/1 53_57:83/1 57_60:8/0 63_68:6/20 56_69:11/3 55_69:7/4 53_56:29/5 57_70:11/6 59_70:3/1 55_58:29/9 69_72:6/1 52_62:22/5 66_68:8/1 59_61:39/1 59_62:49/3 62_68:3/10 58_70:13/1 60_70:1/0 62_72:7/0 57_59:5/0 54_59:23/0 55_56:48/2 61_63:72/4 58_68:26/6 52_56:11/11 55_60:17/4 61_62:31/0 60_62:51/23 70_71:3/0 69_71:11/0 68_73:2/2 70_72:11/3 63_69:3/3 70_75:15/3 69_74:2/4 57_62:19/11 56_62:7/17 63_71:6/3 64_70:2/7 70_73:30/5 63_70:4/3 71_75:13/3 64_66:3/12 60_68:12/0 61_67:9/1 51_57:12/14 61_68:9/2 54_60:8/2 48_53:2/8 60_64:99/4 55_68:24/6 52_60:113/2 62_67:2/2 64_72:2/2 67_71:17/2 59_67:7/2 52_59:73/1 67_73:5/2 71_77:1/10 71_76:1/6 58_69:29/4 49_59:5/3 51_59:54/2 59_64:70/5 51_63:76/2 68_70:19/2 59_68:26/5 62_63:32/7 53_60:59/3 66_71:10/5 69_75:2/2 70_74:40/5 66_70:4/4 65_73:45/2 45_48:0/10 69_76:11/0 58_60:5/0 60_69:2/0 52_61:41/5 64_65:0/10 68_75:1/0 64_71:0/7 53_61:26/0 53_65:21/1 69_70:9/2 57_64:13/2 67_81:0/4 49_54:1/6 71_78:6/10 45_50:0/2 59_69:25/3 61_73:1/0 68_72:5/2 66_76:1/2 55_62:22/5 53_62:6/0 46_50:0/6 57_69:9/2 52_57:65/2 24_18:7/0 23_16:11/2 18_24:0/14 17_23:0/12 23_17:15/0 21_22:14/2 24_17:2/0 22_18:20/0 22_16:3/0 22_19:10/0 23_18:30/0 23_19:14/0 25_18:2/1 20_24:1/4 26_33:4/0 26_18:1/2 16_26:12/1 21_21:16/2 17_26:12/11 24_19:21/2 27_34:4/2 21_20:13/0 18_25:0/26 22_20:4/0 22_30:2/1 21_28:2/0 21_23:8/3 26_20:8/2 24_20:18/1 18_26:6/19 21_30:1/3 15_31:10/1 19_25:2/7 25_19:8/3 20_28:2/6 26_21:14/2 24_30:2/4 22_33:0/11 20_22:1/1 15_26:4/1 20_23:0/3 21_32:0/3 17_25:0/15 14_31:4/0 17_24:1/15 14_32:5/0 20_25:2/3 26_34:3/0 29_35:1/3 20_17:0/0 11_34:0/0"""

# Neighbourhood names for the cells that reach GROW, reverse-geocoded with
# Nominatim (2026-09-07). A grid id is not something a director can act on.
CELL_NAMES = {
    '16_26': 'Mohammed Bin Zayed City, Abu Dhabi',
    '17_24': 'Musaffah Industrial Area, Abu Dhabi',
    '17_25': 'Musaffah, Abu Dhabi',
    '17_26': 'Mohammed Bin Zayed City, Abu Dhabi',
    '18_24': 'Musaffah, Abu Dhabi',
    '18_25': 'Musaffah, Abu Dhabi',
    '21_20': 'Al Qubaisat, Abu Dhabi',
    '21_21': 'Al Rehhan, Abu Dhabi',
    '21_22': 'Khalifa Park, Abu Dhabi',
    '22_19': 'Al Etihad, Abu Dhabi',
    '22_20': 'Qasr Al Bahr, Abu Dhabi',
    '23_17': 'Al Manhal, Abu Dhabi',
    '23_18': 'Al Manhal, Abu Dhabi',
    '23_19': 'Al Nahyan, Abu Dhabi',
    '24_17': 'Al Markaziyah West, Abu Dhabi',
    '24_18': 'Al Danah, Abu Dhabi',
    '24_19': 'Al Reem Island, Abu Dhabi',
    '24_30': 'Yas Island, Abu Dhabi',
    '25_18': 'Zayed Port, Abu Dhabi',
    '53_56': 'Al Thanyah 5, Dubai',
    '54_57': 'Al Sufouh 2, Dubai',
    '54_58': 'Al Thanyah 3, Dubai',
    '55_59': 'Al Barsha 1, Dubai',
    '55_60': 'Al Barsha 2, Dubai',
    '55_68': 'City of Arabia, Dubai',
    '56_60': 'Umm Al Sheif, Dubai',
    '56_61': 'Al Quoz Industrial 3, Dubai',
    '57_61': 'Al Quoz Industrial 1, Dubai',
    '57_62': 'Al Quoz Community, Dubai',
    '58_61': 'Al Safa, Dubai',
    '58_62': 'Al Quoz 1, Dubai',
    '59_62': 'Al Wasl, Dubai',
    '59_63': 'Business Bay, Dubai',
    '59_67': 'Ras Al Khor, Dubai',
    '60_62': 'Jumeirah, Dubai',
    '60_63': 'Al Satwa, Dubai',
    '61_63': "Al Bada'a, Dubai",
    '61_64': 'Zabeel, Dubai',
    '61_65': 'Zabeel, Dubai',
    '61_67': 'Dubai Festival City, Dubai',
    '61_68': 'Umm Ramool, Dubai',
    '62_64': 'Al Mankhool, Dubai',
    '62_65': 'Al Karama, Dubai',
    '62_66': 'Port Saeed, Dubai',
    '62_67': 'Dubai International Airport',
    '62_68': 'Dubai International Airport',
    '63_64': 'Al Shindagha, Dubai',
    '63_65': 'Naif, Dubai',
    '63_66': 'Al Muraqqabat, Dubai',
    '63_67': 'Dubai International Airport',
    '63_68': 'Al Twar, Dubai',
    '63_69': 'Al Qusais, Dubai',
    '64_66': 'Abu Hail, Dubai',
    '64_67': 'Al Mamzar, Dubai',
    '64_68': 'Al Nahda, Dubai',
    '64_69': 'Al Qusais Industrial Area, Dubai',
    '65_68': 'Al Khan, Sharjah',
    '65_69': 'Industrial Area, Sharjah',
    '65_70': 'Industrial Area, Sharjah',
    '66_68': 'Al Khan, Sharjah',
    '66_69': 'Al Majaz, Sharjah',
    '66_70': 'Industrial Area, Sharjah',
    '66_71': 'Mughaidir, Sharjah',
    '67_69': 'Al Qasimia, Sharjah',
    '67_70': 'Halwan, Sharjah',
    '68_69': 'Khalid Port, Sharjah',
    '68_70': 'Al Sharq, Sharjah',
    '69_71': 'Al Heera, Sharjah',
    '69_72': 'Al Nuaimia, Ajman',
    '69_73': 'Al Nuaimia, Ajman',
    '69_74': 'New Industrial, Ajman',
    '69_75': 'Al Zahraa, Ajman',
    '70_71': 'Ajman centre, Ajman',
    '70_72': 'Al Bustan, Ajman',
    '70_75': 'Al Jerf, Ajman',
}


def landuse():
    out = {}
    for tok in LANDUSE_RAW.split():
        k, v = tok.split(":")
        r, i = v.split("/")
        out[k] = (int(r), int(i))
    return out


def to_km(lat, lon):
    return (lon * 111.320 * math.cos(math.radians(LATREF)), lat * 110.574)


def percentile(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    return s[int(k)] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def load_cells():
    cells = []
    for tok in GRID_RAW.split():
        k, poi, comp = tok.split(",")
        la_i, lo_i = (int(x) for x in k.split("_"))
        cells.append({
            "cell_id": k,
            "lat": LAT0 + (la_i + 0.5) * STEP,
            "lon": LON0 + (lo_i + 0.5) * STEP,
            "demand": int(poi),
            "competitors": int(comp),
        })
    lu = landuse()
    for c in cells:
        c["residential"], c["industrial"] = lu.get(c["cell_id"], (0, 0))
        c["zone_name"] = CELL_NAMES.get(c["cell_id"], "")
    return cells


def main():
    shops = list(csv.DictReader(open(DATA / "group_shops_features.csv", encoding="utf-8")))
    women = [s for s in shops if s["segment"] == "women"]
    catch = {}
    for s in women:
        pts, _ = iso.polygon(s["shop_id"], float(s["lat"]), float(s["lon"]))
        catch[s["shop_id"]] = (Polygon([to_km(la, lo) for la, lo in pts]), s)

    cells = load_cells()
    for c in cells:
        p = Point(to_km(c["lat"], c["lon"]))
        covering = [s["shop_id"] for g, s in catch.values() if g.contains(p)]
        c["coverage"] = len(covering)
        c["covered_by"] = ";".join(covering[:3])
        c["nearest_group_km"] = round(min(
            math.dist(to_km(c["lat"], c["lon"]), to_km(float(s["lat"]), float(s["lon"])))
            for s in women), 2)

    dem = [c["demand"] for c in cells]
    sat = [c["competitors"] for c in cells]
    d_hi = percentile(dem, P_DEMAND_HIGH)
    s_hi = percentile(sat, P_SATURATED)

    for c in cells:
        high_demand = c["demand"] >= d_hi
        saturated = c["competitors"] >= s_hi
        # A salon serves residents, not warehouses. See the module docstring.
        residential = c["residential"] >= 1 and c["residential"] > c["industrial"]
        c["residential_catchment"] = residential
        if high_demand and c["coverage"] == 0 and not saturated and residential:
            c["opportunity"] = "GROW"
            c["reason"] = (f"High demand ({c['demand']} retail POIs) with no group "
                           f"catchment reaching it; moderate competition "
                           f"({c['competitors']} salons). Nearest group site "
                           f"{c['nearest_group_km']} km away.")
        elif high_demand and (c["coverage"] <= 1 or saturated or not residential):
            c["opportunity"] = "WATCH"
            why = []
            if saturated:
                why.append(f"saturated market ({c['competitors']} competitors)")
            if c["coverage"] >= 1:
                why.append(f"already covered by {c['coverage']} group site(s)")
            if not residential:
                why.append(f"no residential catchment ({c['residential']} residential vs "
                           f"{c['industrial']} industrial land parcels within 2 km) - the "
                           f"demand is there but the resident customer base is not")
            c["reason"] = (f"High demand ({c['demand']} retail POIs) but " +
                           " and ".join(why) + ".")
        else:
            c["opportunity"] = "SKIP"
            if not high_demand:
                c["reason"] = f"Insufficient demand ({c['demand']} retail POIs)."
            else:
                c["reason"] = f"Fully covered by {c['coverage']} group sites."

    cols = ["cell_id", "zone_name", "lat", "lon", "demand", "competitors",
            "residential", "industrial", "residential_catchment", "coverage",
            "covered_by", "nearest_group_km", "opportunity", "reason"]
    with open(DATA / "opportunity_cells.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(cells)

    (DATA / "opportunity_cells.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Polygon", "coordinates": [[
                 [c["lon"] - STEP/2, c["lat"] - STEP/2], [c["lon"] + STEP/2, c["lat"] - STEP/2],
                 [c["lon"] + STEP/2, c["lat"] + STEP/2], [c["lon"] - STEP/2, c["lat"] + STEP/2],
                 [c["lon"] - STEP/2, c["lat"] - STEP/2]]]},
             "properties": {k: c[k] for k in cols if k not in ("lat", "lon")}}
            for c in cells]}, ensure_ascii=False), encoding="utf-8")

    from collections import Counter
    print(f"Cells analysed: {len(cells)}  (high-demand threshold >= {d_hi:.0f} POIs, "
          f"saturation >= {s_hi:.0f} competitors)")
    print("Split:", dict(Counter(c["opportunity"] for c in cells)))
    grow = sorted([c for c in cells if c["opportunity"] == "GROW"],
                  key=lambda c: -c["demand"])
    print(f"\nTop GROW zones ({len(grow)} in total):")
    for c in grow[:12]:
        print(f"  {(c['zone_name'] or c['cell_id'])[:34]:<36} demand {c['demand']:>5}  "
              f"competition {c['competitors']:>3}  nearest group site {c['nearest_group_km']:>5} km")
    rej = [c for c in cells if c["opportunity"] == "WATCH" and not c["residential_catchment"]]
    print(f"\nRejected for having no residential catchment: {len(rej)}")
    for c in sorted(rej, key=lambda c: -c["demand"])[:6]:
        print(f"  {(c['zone_name'] or c['cell_id'])[:34]:<36} demand {c['demand']:>5}  "
              f"residential {c['residential']:>3}  industrial {c['industrial']:>3}")
    print(f"\nCoverage gaps: {sum(1 for c in cells if c['coverage'] == 0)} cells with "
          f"commercial activity that no group site reaches within "
          f"{iso.THRESHOLD_S//60} min by car")


if __name__ == "__main__":
    main()
