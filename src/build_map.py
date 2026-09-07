"""
Exploratory map of the Omorfia Group network in the UAE.

Layers:
  1. Branches by brand (Bedashing / Tips & Toes / Jazz Lounge Spa)
  2. Catchment areas (configurable radius, 2 km by default)
  3. External competitor density (circle size = competitors within 1 km)
  4. Cannibalisation links: a line between overlapping same-segment pairs
  5. Low-confidence coordinates, highlighted for manual review

Output: out/network_map.html (self-contained, opens in any browser)
"""
import csv, pathlib

import sys
import folium
from folium.plugins import Fullscreen, MiniMap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import competitor_points as comp

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = BASE / "data", BASE / "out"
OUT.mkdir(exist_ok=True)

CATCHMENT_M = 2000

BRAND_STYLE = {
    "Bedashing":       {"color": "#B3306E", "label": "Bedashing (women)"},
    "Tips & Toes":     {"color": "#1F6FB2", "label": "Tips & Toes (women)"},
    "Jazz Lounge Spa": {"color": "#1C7C54", "label": "Jazz Lounge Spa (men)"},
}


def popup_html(s):
    conf_badge = {
        "high":   "<span style='color:#1C7C54'>high</span>",
        "medium": "<span style='color:#B3560F'>medium</span>",
        "low":    "<span style='color:#9E2B2B'>LOW - review</span>",
        "verified": "<span style='color:#1C7C54'><b>VERIFIED</b> (Google place page)</span>",
    }[s["geo_confidence"]]
    cann = float(s["cannibalisation"]) * 100
    cann_col = "#9E2B2B" if cann >= 40 else "#B3560F" if cann >= 20 else "#1C7C54"
    worst = ""
    if s["worst_overlap_with"]:
        worst = (f"<tr><td>Biggest overlap with</td><td>{s['worst_overlap_brand']} "
                 f"· {s['worst_overlap_with']} ({s['worst_overlap_km']} km)</td></tr>")
    return f"""
    <div style="font-family:system-ui,sans-serif;font-size:13px;width:310px">
      <div style="font-weight:600;font-size:15px;margin-bottom:2px">{s['branch_name']}</div>
      <div style="color:{BRAND_STYLE[s['brand']]['color']};font-weight:600;margin-bottom:6px">
        {s['brand']} · {s['format']} · {s['segment']}'s segment</div>
      <div style="color:#555;margin-bottom:8px">{s['address']}<br>{s['emirate']}</div>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="color:#666;padding:2px 6px 2px 0">Competitors 1 km</td><td><b>{s['comp_1km']}</b></td></tr>
        <tr><td style="color:#666;padding:2px 6px 2px 0">Competitors 2 km</td><td>{s['comp_2km']}</td></tr>
        <tr><td style="color:#666;padding:2px 6px 2px 0">Competitors 3 km</td><td>{s['comp_3km']}</td></tr>
        <tr><td style="color:#666;padding:2px 6px 2px 0">Cannibalisation</td>
            <td style="color:{cann_col};font-weight:600">{cann:.0f}%</td></tr>
        {worst}
        <tr><td style="color:#666;padding:2px 6px 2px 0">Group sites &lt;2 km</td><td>{s['n_group_shops_2km']}</td></tr>
        <tr><td style="color:#666;padding:2px 6px 2px 0">Coordinate confidence</td><td>{conf_badge}</td></tr>
      </table>
    </div>"""


def main():
    shops = list(csv.DictReader(open(DATA / "group_shops_features.csv", encoding="utf-8")))
    pairs = list(csv.DictReader(open(DATA / "overlap_pairs.csv", encoding="utf-8")))
    by_id = {s["shop_id"]: s for s in shops}
    for s in shops:
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])

    m = folium.Map(location=[24.9, 55.0], zoom_start=8, tiles="OpenStreetMap",
                   control_scale=True)
    Fullscreen().add_to(m)
    MiniMap(toggle_display=True, minimized=True).add_to(m)

    # --- catchment layer ---
    fg_catch = folium.FeatureGroup(name=f"Catchment areas ({CATCHMENT_M//1000} km)", show=False)
    for s in shops:
        folium.Circle(
            [s["lat"], s["lon"]], radius=CATCHMENT_M,
            color=BRAND_STYLE[s["brand"]]["color"], weight=1,
            fill=True, fill_opacity=0.06,
        ).add_to(fg_catch)
    fg_catch.add_to(m)

    # --- cannibalisation layer ---
    fg_cann = folium.FeatureGroup(name="Cannibalisation links (same customer)", show=True)
    seen = set()
    for p in pairs:
        if p["geocode_artifact"] == "True" or p["same_segment"] != "True":
            continue
        key = tuple(sorted([p["shop_id"], p["other_id"]]))
        if key in seen:
            continue
        seen.add(key)
        frac = float(p["overlap_frac"])
        if frac < 0.15:
            continue
        a, b = by_id[p["shop_id"]], by_id[p["other_id"]]
        folium.PolyLine(
            [[a["lat"], a["lon"]], [b["lat"], b["lon"]]],
            color="#9E2B2B", weight=1 + 5 * frac, opacity=0.55,
            tooltip=(f"{a['brand']} {a['branch_name']} ↔ {b['brand']} {b['branch_name']}<br>"
                     f"overlap {frac*100:.0f}% · {p['distance_km']} km"),
        ).add_to(fg_cann)
    fg_cann.add_to(m)

    # --- competitor layer ---
    # Off by default: the model uses competitor DENSITY, and 855 individual
    # pins are visual noise at network scale. It exists because a director
    # looking at one specific branch does want to see who is on that street.
    fg_comp = folium.FeatureGroup(name="Competitors (OpenStreetMap)", show=False)
    for la, lo, ty in comp.points():
        folium.CircleMarker(
            [la, lo], radius=2.4, color="#6B6B66", weight=0.6,
            fill=True, fill_color="#8A8A82", fill_opacity=0.55,
            tooltip=comp.TYPE_LABEL[ty]).add_to(fg_comp)
    fg_comp.add_to(m)

    # --- brand layers ---
    for brand, style in BRAND_STYLE.items():
        fg = folium.FeatureGroup(name=style["label"], show=True)
        for s in shops:
            if s["brand"] != brand:
                continue
            comp1 = int(s["comp_1km"])
            radius = 5 + min(comp1, 40) * 0.42          # size = competitive pressure
            cann = float(s["cannibalisation"])
            folium.CircleMarker(
                [s["lat"], s["lon"]], radius=radius,
                color="#9E2B2B" if cann >= 0.40 else style["color"],
                weight=3 if cann >= 0.40 else 1.5,
                fill=True, fill_color=style["color"],
                fill_opacity=0.75,
                tooltip=f"{s['brand']} · {s['branch_name']} · {comp1} competitors within 1 km",
                popup=folium.Popup(popup_html(s), max_width=340),
            ).add_to(fg)
        fg.add_to(m)

    # --- data-quality layer ---
    fg_low = folium.FeatureGroup(name="⚠ Low-confidence coordinate", show=False)
    for s in shops:
        if s["geo_confidence"] != "low":
            continue
        folium.Marker(
            [s["lat"], s["lon"]],
            icon=folium.Icon(color="orange", icon="question-sign"),
            tooltip=f"REVIEW: {s['brand']} {s['branch_name']} — approximate coordinate",
        ).add_to(fg_low)
    fg_low.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    n_low = sum(1 for s in shops if s["geo_confidence"] == "low")
    legend = f"""
    <div style="position:fixed;bottom:22px;left:22px;z-index:9999;
                background:rgba(255,255,255,.96);border:1px solid #d5d5d5;
                border-radius:4px;padding:12px 14px;font:12.5px/1.5 system-ui,sans-serif;
                max-width:290px;box-shadow:0 2px 10px rgba(0,0,0,.12)">
      <div style="font-weight:700;margin-bottom:6px">Omorfia network · UAE</div>
      <div style="color:#B3306E">● Bedashing — 24 salons (women)</div>
      <div style="color:#1F6FB2">● Tips &amp; Toes — 40 salons (women)</div>
      <div style="color:#1C7C54">● Jazz Lounge Spa — 10 spas (men)</div>
      <hr style="border:0;border-top:1px solid #e5e5e5;margin:8px 0">
      <div><b>Size</b> = external competitors within 1 km</div>
      <div><b>Red outline</b> = cannibalisation ≥ 40%</div>
      <div><b>Red line</b> = overlap with a group site competing
           for the same customer</div>
      <div><b>Grey dots</b> = competitor POIs (layer off by default)</div>
      <hr style="border:0;border-top:1px solid #e5e5e5;margin:8px 0">
      <div style="color:#9E2B2B">{n_low} low-confidence coordinates,
           still to verify (⚠ layer)</div>
      <div style="color:#777;margin-top:6px;font-size:11.5px">
        Competitors: OpenStreetMap, 2,543 POIs across the UAE.<br>
        Branches: official store locators, 2026-09-03.</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))

    path = OUT / "network_map.html"
    m.save(str(path))
    print(f"map -> {path}")
    print(f"  {len(shops)} branches · {len(seen)} cannibalisation links drawn")


if __name__ == "__main__":
    main()
