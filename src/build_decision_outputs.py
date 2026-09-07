"""
Decision outputs:
  out/decision_map.html   map coloured by recommendation, with the reason
  out/quadrant.png        health vs market attractiveness, the network in one chart
"""
import csv, pathlib

import folium
from folium.plugins import Fullscreen
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = BASE / "data", BASE / "out"
OUT.mkdir(exist_ok=True)

REC_COLOR = {"PROTECT": "#1C7C54", "HOLD": "#B3860F", "SHRINK": "#9E2B2B"}


def load():
    rows = list(csv.DictReader(open(DATA / "master.csv", encoding="utf-8")))
    for r in rows:
        for k in ("lat", "lon", "score", "sig_health", "sig_attract",
                  "sig_cannib", "stability", "rating"):
            r[k] = float(r[k])
        r["n_reviews"] = int(r["n_reviews"])
    return rows


def build_map(rows):
    m = folium.Map(location=[24.9, 55.0], zoom_start=8,
                   tiles="OpenStreetMap", control_scale=True)
    Fullscreen().add_to(m)

    groups = {r: folium.FeatureGroup(name=f"{r} ({sum(1 for x in rows if x['recommendation']==r)})")
              for r in ("PROTECT", "HOLD", "SHRINK")}

    for r in rows:
        col = REC_COLOR[r["recommendation"]]
        dashed = r["robust"] == "FRAGILE"
        popup = f"""
        <div style="font-family:system-ui,sans-serif;font-size:13px;width:330px">
          <div style="font-weight:600;font-size:15px">{r['branch_name']}</div>
          <div style="color:#666;margin-bottom:6px">{r['brand']} · {r['emirate']}</div>
          <div style="background:{col};color:#fff;display:inline-block;
                      padding:2px 9px;border-radius:2px;font-weight:600;
                      letter-spacing:.04em;margin-bottom:8px">
            {r['recommendation']}</div>
          <div style="margin:8px 0;line-height:1.45">{r['reason']}</div>
          <table style="border-collapse:collapse;width:100%;font-size:12.5px">
            <tr><td style="color:#666">Score</td><td><b>{r['score']:.1f}</b></td></tr>
            <tr><td style="color:#666">Health (percentile)</td><td>{r['sig_health']:.0f}</td></tr>
            <tr><td style="color:#666">Attractiveness (percentile)</td><td>{r['sig_attract']:.0f}</td></tr>
            <tr><td style="color:#666">Cannibalisation</td><td>{r['sig_cannib']:.0f}%</td></tr>
            <tr><td style="color:#666">Rating</td><td>{r['rating']} ({r['n_reviews']} reviews)</td></tr>
            <tr><td style="color:#666">Stability</td>
                <td style="color:{'#9E2B2B' if dashed else '#1C7C54'}">
                  {r['stability']:.0f}% · {r['robust']}</td></tr>
            {f"<tr><td style='color:#666'>Head-to-head</td><td>{r['duel']}</td></tr>" if r['duel'] else ""}
          </table>
        </div>"""
        folium.CircleMarker(
            [r["lat"], r["lon"]],
            radius=6 + (r["n_reviews"] ** 0.5) / 9,
            color="#333" if dashed else col,
            weight=2.5 if dashed else 1.2,
            dash_array="4,3" if dashed else None,
            fill=True, fill_color=col, fill_opacity=0.8,
            tooltip=f"{r['brand']} · {r['branch_name']} — {r['recommendation']}",
            popup=folium.Popup(popup, max_width=360),
        ).add_to(groups[r["recommendation"]])

    for g in groups.values():
        g.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    n_bd = sum(1 for r in rows if r["brand"] == "Bedashing")
    legend = f"""
    <div style="position:fixed;bottom:22px;left:22px;z-index:9999;
                background:rgba(255,255,255,.96);border:1px solid #d5d5d5;
                border-radius:4px;padding:12px 15px;
                font:12.5px/1.55 system-ui,sans-serif;max-width:300px;
                box-shadow:0 2px 10px rgba(0,0,0,.12)">
      <div style="font-weight:700;margin-bottom:7px">Network decision &middot; women&rsquo;s segment</div>
      <div style="color:#1C7C54">● PROTECT — invest and defend</div>
      <div style="color:#B3860F">● HOLD — renew and revisit</div>
      <div style="color:#9E2B2B">● SHRINK — reduce or do not renew</div>
      <hr style="border:0;border-top:1px solid #e5e5e5;margin:8px 0">
      <div><b>Size</b> = review volume</div>
      <div><b>Dashed outline</b> = fragile recommendation,
           it flips if you move the weights</div>
      <hr style="border:0;border-top:1px solid #e5e5e5;margin:8px 0">
      <div style="color:#777;font-size:11.5px">
        {len(rows)} branches scored ({n_bd} Bedashing).<br>
        Jazz Lounge Spa excluded: men&rsquo;s segment.<br>
        Click a dot to see why.</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))
    p = OUT / "decision_map.html"
    m.save(str(p))
    return p


def build_quadrant(rows):
    fig, ax = plt.subplots(figsize=(10, 7.2), dpi=140)
    fig.patch.set_facecolor("#FBFBFA")
    ax.set_facecolor("#FBFBFA")

    ax.axhline(50, color="#CFCFCB", lw=1, zorder=1)
    ax.axvline(50, color="#CFCFCB", lw=1, zorder=1)

    for r in rows:
        col = REC_COLOR[r["recommendation"]]
        edge = "#222" if r["brand"] == "Bedashing" else "none"
        ax.scatter(r["sig_attract"], r["sig_health"],
                   s=28 + r["n_reviews"] / 6,
                   c=col, alpha=0.72, edgecolors=edge, linewidths=1.1, zorder=3)

    # label only the extreme Bedashing sites, to avoid clutter
    for r in rows:
        if r["brand"] != "Bedashing":
            continue
        if r["recommendation"] == "SHRINK" or r["sig_cannib"] >= 30 or r["score"] >= 55:
            ax.annotate(r["branch_name"], (r["sig_attract"], r["sig_health"]),
                        fontsize=7.6, color="#333",
                        xytext=(6, 5), textcoords="offset points", zorder=4)

    # very light quadrant tints, so position reads at a glance
    ax.axhspan(50, 103, xmin=0.0, xmax=0.5, color="#C9A227", alpha=0.05, zorder=0)
    ax.axhspan(50, 103, xmin=0.5, xmax=1.0, color="#1C7C54", alpha=0.06, zorder=0)
    ax.axhspan(-3, 50, xmin=0.0, xmax=0.5, color="#9E2B2B", alpha=0.05, zorder=0)
    ax.axhspan(-3, 50, xmin=0.5, xmax=1.0, color="#2B5F9E", alpha=0.05, zorder=0)

    Q = dict(fontsize=7.6, color="#9A9A94", weight="bold", transform=ax.transAxes)
    ax.text(0.012, 0.975, "STRONG EXECUTION\nWEAK MARKET", va="top", **Q)
    ax.text(0.988, 0.975, "PROTECT", va="top", ha="right", **Q)
    ax.text(0.012, 0.025, "REVIEW", va="bottom", **Q)
    ax.text(0.988, 0.025, "GOOD MARKET\nWEAK EXECUTION", va="bottom", ha="right", **Q)

    ax.set_xlabel("Market attractiveness  (demand \u2212 competitive pressure, percentile)", fontsize=10)
    ax.set_ylabel("Branch health  (rating \u00d7 review volume, percentile)", fontsize=10)
    ax.set_title("Omorfia network, women's segment \u00b7 black outline = Bedashing",
                 fontsize=12.5, weight="600", pad=13)
    ax.set_xlim(-3, 103); ax.set_ylim(-3, 103)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color("#CFCFCB")
    ax.tick_params(colors="#666", labelsize=9)

    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k, markersize=8)
               for k, c in REC_COLOR.items()]
    ax.legend(handles=handles, loc="upper center", frameon=False, fontsize=9,
              ncol=3, bbox_to_anchor=(0.5, -0.10))

    fig.subplots_adjust(bottom=0.16)
    p = OUT / "quadrant.png"
    fig.savefig(p, facecolor=fig.get_facecolor())
    return p


if __name__ == "__main__":
    rows = load()
    print("map      ->", build_map(rows))
    print("quadrant ->", build_quadrant(rows))
