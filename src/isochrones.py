"""
Catchment areas by drive time rather than by radius.

For each salon, 16 radials (one every 22.5 degrees) with six sampling points
each (0.4 / 0.8 / 1.2 / 1.8 / 2.5 / 3.5 km). OSRM's `table` service returns the
real driving time to every point, and the furthest reachable point per radial
within the threshold is kept. The 16 vertices form the isochrone.

The 6-minute threshold is a decision, not a fact. At 12 minutes almost every
salon saturated the 3.5 km sampling and the model stopped discriminating.

Some coordinates are not routable (inside a mall, a marina basin, private
roads) and return a degenerate polygon. Those fall back to a 2 km circle,
flagged so the user knows which sites carry no travel-time logic.

Extracted 2026-09-07 from router.project-osrm.org.
"""
import math

THRESHOLD_S = 360
N_BEARINGS = 16
SAMPLE_KM = [0.4, 0.8, 1.2, 1.8, 2.5, 3.5]
FALLBACK_RADIUS_KM = 2.0

# shop_id -> 16 radii in km, starting due north and turning clockwise
RADII = {
    "bd_al_ain": [0.4,3.5,3.5,3.5,1.8,2.5,1.2,1.2,1.2,0.8,1.2,2.5,0.4,0.4,0.0,0.0],
    "bd_al_barsha": [2.5,0.8,0.4,0.4,0.4,2.5,2.5,1.8,1.8,2.5,1.8,1.2,1.8,1.8,1.2,1.2],
    "bd_al_dhafra": [1.8,0.0,0.0,0.8,2.5,2.5,1.8,2.5,3.5,1.8,1.2,1.2,2.5,1.8,1.8,2.5],
    "bd_al_falah": [1.2,1.8,1.2,0.8,1.2,1.2,1.8,2.5,2.5,1.2,1.8,1.8,1.8,1.8,1.8,1.8],
    "bd_al_jada": [0.0,0.4,0.8,1.2,1.8,0.0,0.0,0.0,0.4,0.8,1.2,0.0,0.0,0.0,0.0,0.0],
    "bd_al_maqta": [1.2,1.2,0.8,1.8,1.2,2.5,2.5,1.8,0.8,1.2,0.4,0.4,0.4,1.8,1.2,0.8],
    "bd_al_taif_mall": [1.8,2.5,1.8,2.5,3.5,2.5,1.2,1.2,0.8,1.2,1.2,1.2,2.5,1.8,1.8,2.5],
    "bd_baniyas": [2.5,1.8,2.5,1.8,1.8,2.5,1.8,0.8,0.4,1.2,0.8,1.2,0.4,2.5,1.2,1.2],
    "bd_city_walk": [1.8,3.5,1.2,0.8,1.8,1.2,0.4,0.4,1.8,1.8,1.8,1.8,1.8,1.2,1.8,1.8],
    "bd_delma": [2.5,3.5,3.5,1.8,2.5,1.8,3.5,3.5,2.5,3.5,3.5,3.5,2.5,1.8,2.5,3.5],
    "bd_jumeirah_park": [1.2,1.8,0.4,1.8,1.2,1.2,0.8,0.4,0.4,0.4,0.4,0.4,0.4,1.2,1.8,2.5],
    "bd_khaleej_al_arabi": [3.5,3.5,2.5,2.5,1.8,2.5,3.5,2.5,2.5,1.8,2.5,1.8,3.5,2.5,2.5,3.5],
    "bd_khalifa_city_a": [1.2,1.8,3.5,3.5,2.5,1.8,2.5,3.5,1.8,1.2,1.8,2.5,1.8,1.8,1.8,1.2],
    "bd_ministries_complex": [0.0,0.0,0.0,0.0,0.0,2.5,1.8,1.8,0.8,0.8,0.8,0.8,1.2,1.8,1.2,0.8],
    "bd_mirdif_35": [0.0,0.0,0.0,0.0,0.8,0.8,1.2,1.2,1.8,1.2,1.8,1.8,1.2,0.8,0.8,1.2],
    "bd_mohammed_bin_zayed_city": [2.5,1.8,1.8,1.2,1.8,1.2,1.2,1.2,1.8,1.2,0.8,0.4,0.8,1.8,1.8,1.8],
    "bd_nad_al_sheba": [2.5,1.8,1.8,1.2,0.4,0.8,0.4,1.8,1.8,1.8,1.8,1.8,1.8,1.8,2.5,2.5],
    "bd_noya_plaza": [0.4,0.4,0.4,0.4,0.4,0.4,1.2,0.8,0.8,1.8,1.2,1.2,1.2,0.4,0.4,0.0],
    "bd_ras_al_khaimah": [3.5,3.5,3.5,2.5,1.2,1.8,1.8,1.8,1.2,1.2,1.8,2.5,2.5,3.5,1.8,3.5],
    "bd_shahama": [1.2,1.8,1.2,0.4,0.0,0.0,0.0,0.4,0.4,1.2,2.5,1.8,1.8,1.8,1.2,1.2],
    "bd_shakhbout_city": [2.5,2.5,3.5,1.8,1.2,2.5,2.5,3.5,2.5,3.5,1.2,3.5,2.5,2.5,3.5,2.5],
    "bd_west_yas": [1.8,1.8,1.8,1.8,2.5,1.2,0.8,1.2,1.8,2.5,2.5,1.8,1.2,1.2,2.5,2.5],
    "bd_zawaya_walk": [1.8,1.8,1.2,1.2,1.8,1.8,1.8,1.2,1.2,2.5,2.5,2.5,2.5,1.2,1.8,1.8],
    "bd_zayed_international_airport": [2.5,1.2,0.4,0.8,0.8,0.8,0.0,0.0,1.2,0.8,1.2,1.2,1.8,0.8,1.8,1.8],
    "tt_al_barsha": [1.8,1.8,0.8,0.8,1.8,2.5,1.2,1.2,0.8,1.2,1.8,1.8,1.8,1.8,1.2,1.2],
    "tt_al_dhannah_mall": [1.2,2.5,0.8,0.8,0.4,0.0,0.0,0.0,0.4,0.4,0.4,0.0,1.8,1.8,1.2,1.8],
    "tt_al_falah_1": [1.8,1.2,1.8,1.8,1.8,2.5,1.2,1.2,1.2,1.2,1.8,0.8,0.4,0.0,0.0,3.5],
    "tt_al_falah_5": [1.8,1.2,1.8,1.8,1.8,2.5,1.2,1.2,1.2,1.2,1.8,0.8,0.4,0.0,0.0,3.5],
    "tt_al_furjan_pavilion": [0.8,0.4,1.2,1.2,1.2,1.2,0.8,1.2,1.2,1.8,2.5,1.8,2.5,3.5,3.5,1.2],
    "tt_al_furjan_west": [0.8,0.4,1.2,1.2,1.2,1.2,0.8,1.2,1.2,1.8,2.5,1.8,2.5,3.5,3.5,1.2],
    "tt_al_hamra_mall": [0.8,1.2,1.2,0.0,0.0,1.8,1.2,2.5,2.5,1.8,2.5,2.5,1.2,1.2,1.8,1.2],
    "tt_al_shamkhah_villa": [1.8,0.8,0.8,1.8,2.5,1.8,1.8,2.5,1.2,1.8,1.8,0.8,1.2,1.8,1.8,1.8],
    "tt_arabian_ranches": [0.4,0.4,0.8,1.8,1.2,0.8,0.8,0.0,0.0,0.0,0.4,0.8,1.8,0.8,0.4,0.4],
    "tt_arjan": [1.8,0.8,1.2,1.2,1.2,0.8,0.4,0.4,0.4,0.0,1.8,0.0,1.2,1.2,1.2,1.2],
    "tt_business_bay": [0.8,0.8,1.2,1.2,1.8,1.2,0.8,1.2,1.2,1.2,1.8,1.2,1.2,0.8,0.4,0.4],
    "tt_city_centre_mirdif": [0.8,0.8,2.5,1.8,2.5,3.5,2.5,1.2,0.4,0.0,0.0,0.8,0.0,0.0,0.4,0.0],
    "tt_creek_beach": [0.8,0.8,1.2,1.2,1.2,0.8,0.8,0.8,1.2,1.2,1.2,0.0,1.2,0.8,0.8,0.8],
    "tt_dubai_festival_city": [1.8,1.8,1.8,1.8,1.2,1.8,1.8,1.2,1.8,0.8,0.8,0.4,2.5,0.4,1.2,1.8],
    "tt_dubai_marina_mall": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    "tt_dubai_silicon_central": [0.0,0.0,0.0,0.8,1.2,0.8,0.8,0.4,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
    "tt_golden_mile_2": [1.8,1.8,1.8,1.2,1.2,0.0,1.8,1.2,1.2,1.8,1.2,1.8,1.8,3.5,3.5,1.8],
    "tt_hili_mall": [1.8,2.5,2.5,1.2,0.4,0.0,0.0,0.0,0.4,0.4,1.2,2.5,2.5,1.2,1.8,2.5],
    "tt_jimi_district": [1.2,1.8,1.8,2.5,1.2,1.8,1.8,2.5,3.5,2.5,3.5,1.8,3.5,2.5,1.8,1.8],
    "tt_khaleej_al_arabi": [2.5,2.5,2.5,2.5,3.5,3.5,2.5,0.8,0.8,0.8,0.8,2.5,2.5,1.2,1.8,1.8],
    "tt_khalifa_city": [1.2,1.2,1.2,1.8,2.5,1.8,1.8,1.8,2.5,1.2,1.8,2.5,1.8,1.2,1.2,1.2],
    "tt_makani": [2.5,2.5,2.5,1.8,2.5,2.5,2.5,1.8,1.8,1.2,1.8,2.5,1.2,1.2,0.8,3.5],
    "tt_marina_mall_auh": [3.5,2.5,1.8,1.8,1.2,1.2,1.8,2.5,1.8,2.5,0.8,0.8,2.5,3.5,3.5,3.5],
    "tt_marina_vista": [0.8,0.8,0.8,0.8,0.4,1.2,1.2,1.8,1.8,0.4,1.8,1.8,0.4,0.0,0.4,0.4],
    "tt_me_aisem_city_centre": [0.0,0.0,0.0,0.0,0.4,0.4,1.2,1.2,0.4,0.8,0.8,0.8,0.8,0.4,0.0,0.0],
    "tt_meadows_mall": [1.8,1.2,1.2,0.8,0.8,1.2,1.2,0.8,0.4,0.4,0.4,0.4,0.4,0.8,0.8,0.8],
    "tt_mira_town_centre": [1.2,1.2,0.8,0.4,0.4,0.4,0.4,0.4,0.8,0.8,0.4,0.4,0.8,1.2,1.2,1.2],
    "tt_mohammed_bin_zayed_city": [2.5,2.5,1.8,1.8,1.8,2.5,1.8,2.5,2.5,2.5,3.5,2.5,1.8,2.5,1.8,2.5],
    "tt_nation_towers": [0.8,3.5,3.5,3.5,2.5,3.5,2.5,1.2,1.8,2.5,1.8,1.8,1.2,1.2,1.8,1.2],
    "tt_park_point": [1.2,1.2,0.8,1.2,1.2,0.8,0.8,1.2,0.8,0.8,1.8,1.8,1.2,0.8,0.8,1.2],
    "tt_port_de_la_mer": [0.4,0.4,0.0,2.5,2.5,1.2,1.8,1.8,1.8,1.2,0.4,1.2,1.8,3.5,2.5,0.8],
    "tt_reem_mall": [1.2,1.2,2.5,1.8,1.8,1.8,3.5,0.8,0.8,0.4,1.2,0.8,1.8,1.8,1.8,1.8],
    "tt_saadiyat_island": [0.0,0.0,1.8,1.2,1.2,0.0,0.8,0.8,1.2,0.0,1.8,0.4,0.0,0.0,0.0,0.0],
    "tt_shamkha_mall": [1.8,1.8,1.2,1.2,1.8,1.2,2.5,0.4,1.2,2.5,1.2,1.8,1.8,1.8,1.8,1.2],
    "tt_the_dubai_mall": [1.8,3.5,1.2,1.2,0.4,0.8,0.8,0.4,1.2,0.8,0.8,2.5,0.8,1.8,1.8,0.8],
    "tt_the_greens_souk": [1.8,1.2,1.2,1.8,1.2,2.5,1.8,1.8,1.2,1.8,0.0,0.0,0.0,0.4,1.2,1.2],
    "tt_the_springs_souk": [2.5,2.5,1.8,0.4,0.4,0.4,0.4,0.8,1.8,0.8,1.8,1.8,0.4,0.4,2.5,1.2],
    "tt_the_valley": [0.4,0.4,0.8,0.8,0.0,0.0,0.0,0.0,0.4,0.4,0.8,0.4,0.4,0.4,0.4,0.4],
    "tt_the_villa": [1.2,1.2,0.8,0.4,0.4,0.4,0.4,0.4,0.8,0.8,0.4,0.4,0.8,1.2,1.2,1.2],
    "tt_yas_mall": [1.8,0.8,0.8,0.8,1.8,1.8,0.8,0.4,0.4,2.5,0.8,0.4,1.8,1.8,1.8,0.8],
}

# Below this area (km2) the isochrone is degenerate: the coordinate is not
# routable and OSRM returns almost everything as unreachable.
MIN_AREA_KM2 = 0.8


def polygon(shop_id, lat, lon):
    """(list of (lat, lon), is_fallback). The ring is closed."""
    r = RADII.get(shop_id)
    use_fallback = r is None or _area_km2(r) < MIN_AREA_KM2
    if use_fallback:
        r = [FALLBACK_RADIUS_KM] * N_BEARINGS
    pts = []
    for b, d in enumerate(r):
        th = 2 * math.pi * b / N_BEARINGS
        dlat = (d * math.cos(th)) / 110.574
        dlon = (d * math.sin(th)) / (111.320 * math.cos(math.radians(lat)))
        pts.append((lat + dlat, lon + dlon))
    pts.append(pts[0])
    return pts, use_fallback


def _area_km2(radii):
    # area of the radial polygon: sum of its triangular sectors
    a = 0.0
    n = len(radii)
    half = math.sin(2 * math.pi / n) / 2
    for i in range(n):
        a += radii[i] * radii[(i + 1) % n] * half
    return a


def area_km2(shop_id):
    r = RADII.get(shop_id)
    if r is None or _area_km2(r) < MIN_AREA_KM2:
        return math.pi * FALLBACK_RADIUS_KM ** 2
    return _area_km2(r)


def stats():
    ok, fb = [], []
    for sid, r in RADII.items():
        (fb if _area_km2(r) < MIN_AREA_KM2 else ok).append(sid)
    return ok, fb


if __name__ == "__main__":
    ok, fb = stats()
    print(f"{THRESHOLD_S//60}-minute isochrones for {len(RADII)} salons")
    print(f"  valid       : {len(ok)}")
    print(f"  degenerate  : {len(fb)}  -> fall back to a {FALLBACK_RADIUS_KM} km circle")
    for s in fb:
        print("     !", s)
    areas = sorted(((area_km2(s), s) for s in RADII), reverse=True)
    print("\nLargest area reachable in 6 min:")
    for a, s in areas[:5]:
        print(f"   {a:6.2f} km2  {s}")
    print("\nSmallest:")
    for a, s in areas[-5:]:
        print(f"   {a:6.2f} km2  {s}")
