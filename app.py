"""
Omorfia Network Intelligence: decision support for the salon portfolio.

    streamlit run app.py

Everything is read from the CSVs in data/. No network access and no
credentials. If GEMINI_API_KEY, GROQ_API_KEY or OPENAI_API_KEY is set the
Analyst tab uses a tool-calling model, otherwise it runs in no-model mode.
"""
import csv, json, math, pathlib, sys

import streamlit as st
import folium
from folium.plugins import Fullscreen
import streamlit.components.v1 as components

BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))
DATA = BASE / "data"

import isochrones as iso            # noqa: E402
from ai_layer import ask, LLM       # noqa: E402
import prices                        # noqa: E402
import competitor_points as comp     # noqa: E402

REC_COLOR = {"PROTECT": "#1C7C54", "HOLD": "#B3860F", "SHRINK": "#9E2B2B"}
OPP_COLOR = {"GROW": "#1C7C54", "WATCH": "#B3860F", "SKIP": "#9AA0A6"}
BRAND_COLOR = {"Bedashing": "#B3306E", "Tips & Toes": "#1F6FB2",
               "Jazz Lounge Spa": "#1C7C54"}

st.set_page_config(page_title="Omorfia Network Intelligence",
                   page_icon="🗺️", layout="wide")


# ----------------------------------------------------------------- data ---
@st.cache_data
def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@st.cache_data
def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def pctile(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    return s[int(k)] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def rescore(rows, wh, wa, wc, p_protect, p_shrink, min_cannib, max_health):
    # the signals do not depend on the weights, only the combination moves
    out = []
    for r in rows:
        d = dict(r)
        h, a, c = float(r["sig_health"]), float(r["sig_attract"]), float(r["sig_cannib"])
        d["_h"], d["_a"], d["_c"] = h, a, c
        d["c_health"], d["c_attract"], d["c_cannib"] = wh * h, wa * a, -wc * c
        d["score"] = d["c_health"] + d["c_attract"] + d["c_cannib"]
        out.append(d)
    scores = [r["score"] for r in out]
    tp, ts = pctile(scores, p_protect), pctile(scores, p_shrink)
    for r in out:
        if r["score"] >= tp:
            r["recommendation"] = "PROTECT"
        elif r["score"] < ts and (r["_c"] >= min_cannib or r["_h"] < max_health):
            r["recommendation"] = "SHRINK"
        else:
            r["recommendation"] = "HOLD"
    return out, tp, ts


# -------------------------------------------------------------- sidebar ---
st.sidebar.title("Omorfia Network Intelligence")
st.sidebar.caption("Network decision support · salon portfolio")

st.sidebar.markdown("### Scope")
brands = st.sidebar.multiselect("Brand", ["Bedashing", "Tips & Toes"],
                                default=["Bedashing", "Tips & Toes"])
emirates = st.sidebar.multiselect(
    "Emirate", ["Abu Dhabi", "Dubai", "Sharjah", "Ras Al Khaimah", "Fujairah"],
    default=["Abu Dhabi", "Dubai", "Sharjah", "Ras Al Khaimah", "Fujairah"])

st.sidebar.markdown("### Model weights")
st.sidebar.caption("These are a business decision, not an output of the data. "
                   "Move them and see which recommendations survive.")
wh = st.sidebar.slider("Branch health", 0.0, 1.0, 0.40, 0.05)
wa = st.sidebar.slider("Market attractiveness", 0.0, 1.0, 0.35, 0.05)
wc = st.sidebar.slider("Cannibalisation penalty", 0.0, 1.0, 0.25, 0.05)
tot = max(wh + wa + wc, 1e-6)
wh, wa, wc = wh / tot, wa / tot, wc / tot

with st.sidebar.expander("Thresholds and guardrail"):
    p_protect = st.slider("PROTECT percentile", 50, 90, 66)
    p_shrink = st.slider("SHRINK percentile", 10, 50, 33)
    min_cannib = st.slider("Minimum cannibalisation for SHRINK (%)", 0, 80, 30)
    max_health = st.slider("Maximum health for SHRINK (percentile)", 0, 80, 40)
    st.caption("The second SHRINK condition stops a bare percentile cut from "
               "flagging a third of the network for closure even when the "
               "network is healthy.")

master = load("master.csv")
rows, thr_p, thr_s = rescore(master, wh, wa, wc, p_protect, p_shrink,
                             min_cannib, max_health)
view = [r for r in rows if r["brand"] in brands and r["emirate"] in emirates]

llm = LLM()
st.sidebar.markdown("### Language model")
if llm.available:
    st.sidebar.success(f"Active provider: {llm.provider}")
else:
    st.sidebar.info("No credentials found. The Analyst tab runs in no-model "
                    "mode, with a deterministic router and templates.")

# --------------------------------------------------------------- header ---
st.title("Salon network decisions · Omorfia Group")
c1, c2, c3, c4, c5 = st.columns(5)
n = {k: sum(1 for r in view if r["recommendation"] == k)
     for k in ("PROTECT", "HOLD", "SHRINK")}
c1.metric("Salons in scope", len(view))
c2.metric("PROTECT", n["PROTECT"])
c3.metric("HOLD", n["HOLD"])
c4.metric("SHRINK", n["SHRINK"])
c5.metric("Fragile", sum(1 for r in view if r["robust"] == "FRAGILE"),
          help="The recommendation flips if you move the weights within a "
               "reasonable range. Do not take irreversible decisions there.")

tabs = st.tabs(["Map", "Branch record", "Quadrant",
                "Opportunity", "Analyst", "Method and limits"])

# ------------------------------------------------------------------ map ---
with tabs[0]:
    left, right = st.columns([3, 1])
    with right:
        show_catch = st.checkbox("Catchment areas (6 min drive)", True)
        show_cann = st.checkbox("Cannibalisation links", True)
        show_comp = st.checkbox("Competitors (OpenStreetMap)", False)
        show_opp = st.checkbox("Opportunity zones", False)
        st.caption("The catchment is a real drive-time isochrone computed with "
                   "OSRM, not a circle. That is why the shapes are irregular: "
                   "they pick up motorways, creeks and severed streets.")
        if show_comp:
            st.caption("872 beauty POIs within 3 km of a group site. The model "
                       "uses their density, not the individual pins — this "
                       "layer is for looking at one street, not for deciding.")
    with left:
        m = folium.Map(location=[24.9, 55.0], zoom_start=8,
                       tiles="OpenStreetMap", control_scale=True)
        Fullscreen().add_to(m)

        if show_opp:
            fg = folium.FeatureGroup(name="Opportunity", show=True)
            for c in load("opportunity_cells.csv"):
                if c["opportunity"] == "SKIP":
                    continue
                la, lo, s = float(c["lat"]), float(c["lon"]), 0.01
                folium.Rectangle(
                    [[la - s, lo - s], [la + s, lo + s]],
                    color=OPP_COLOR[c["opportunity"]], weight=1,
                    fill=True, fill_opacity=0.22,
                    tooltip=(f"{c['opportunity']} · "
                             f"{c['zone_name'] or 'cell ' + c['cell_id']}"
                             f"<br>{c['reason']}")
                ).add_to(fg)
            fg.add_to(m)

        if show_comp:
            fg = folium.FeatureGroup(name="Competitors", show=True)
            for la, lo, t in comp.points():
                folium.CircleMarker(
                    [la, lo], radius=2.4, color="#6B6B66", weight=0.6,
                    fill=True, fill_color="#8A8A82", fill_opacity=0.55,
                    tooltip=comp.TYPE_LABEL[t]).add_to(fg)
            fg.add_to(m)

        ids = {r["shop_id"] for r in view}
        if show_catch:
            fg = folium.FeatureGroup(name="Catchment", show=True)
            for feat in load_json("catchments.geojson")["features"]:
                if feat["properties"]["shop_id"] not in ids:
                    continue
                folium.Polygon(
                    [[la, lo] for lo, la in feat["geometry"]["coordinates"][0]],
                    color=BRAND_COLOR.get(feat["properties"]["brand"], "#888"),
                    weight=1, fill=True, fill_opacity=0.07,
                    tooltip=(f"{feat['properties']['branch_name']} · "
                             f"{feat['properties']['area_km2']} km2 · "
                             f"{feat['properties']['source']}")).add_to(fg)
            fg.add_to(m)

        if show_cann:
            byid = {r["shop_id"]: r for r in rows}
            fg = folium.FeatureGroup(name="Cannibalisation", show=True)
            seen = set()
            for p in load("overlap_pairs.csv"):
                if p["geocode_artifact"] == "True" or p["same_segment"] != "True":
                    continue
                if float(p["overlap_frac"]) < 0.20:
                    continue
                a, b = byid.get(p["shop_id"]), byid.get(p["other_id"])
                if not a or not b or a["shop_id"] not in ids:
                    continue
                k = tuple(sorted([a["shop_id"], b["shop_id"]]))
                if k in seen:
                    continue
                seen.add(k)
                folium.PolyLine(
                    [[float(a["lat"]), float(a["lon"])], [float(b["lat"]), float(b["lon"])]],
                    color="#9E2B2B", weight=1 + 5 * float(p["overlap_frac"]), opacity=0.55,
                    tooltip=(f"{a['branch_name']} ↔ {b['branch_name']}<br>"
                             f"{float(p['overlap_frac'])*100:.0f}% · {p['distance_km']} km")
                ).add_to(fg)
            fg.add_to(m)

        fgs = {k: folium.FeatureGroup(name=k, show=True) for k in REC_COLOR}
        for r in view:
            col = REC_COLOR[r["recommendation"]]
            frag = r["robust"] == "FRAGILE"
            folium.CircleMarker(
                [float(r["lat"]), float(r["lon"])],
                radius=6 + (int(r["n_reviews"]) ** 0.5) / 9,
                color="#222" if frag else col, weight=2.5 if frag else 1.2,
                dash_array="4,3" if frag else None,
                fill=True, fill_color=col, fill_opacity=0.82,
                tooltip=f"{r['brand']} · {r['branch_name']} — {r['recommendation']}",
                popup=folium.Popup(
                    f"<b>{r['branch_name']}</b><br>{r['brand']} · {r['emirate']}<br>"
                    f"<span style='color:{col};font-weight:600'>{r['recommendation']}</span>"
                    f" · stability {r['stability']}%<br><br>{r['reason']}", max_width=340)
            ).add_to(fgs[r["recommendation"]])
        for g in fgs.values():
            g.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        components.html(m._repr_html_(), height=560)

# --------------------------------------------------------------- record ---
with tabs[1]:
    if not view:
        st.warning("No branches in the selected scope.")
    else:
        names = [f"{r['brand']} · {r['branch_name']}" for r in view]
        pick = st.selectbox("Branch", names)
        r = view[names.index(pick)]
        a, b = st.columns([1, 1])
        with a:
            st.subheader(r["branch_name"])
            st.markdown(
                f"**{r['recommendation']}** · score {r['score']:.1f} · "
                f"stability {r['stability']}% ({r['robust']})")
            st.write(r["reason"])
            st.markdown("**Contribution of each signal to the score**")
            st.bar_chart({"contribution": {
                "Health": round(r["c_health"], 1),
                "Attractiveness": round(r["c_attract"], 1),
                "Cannibalisation": round(r["c_cannib"], 1)}})
        with b:
            st.markdown("**Signals (network percentile)**")
            st.dataframe({
                "signal": ["Health", "Market attractiveness", "Cannibalisation"],
                "percentile": [r["_h"], r["_a"], r["_c"]]}, hide_index=True,
                width="stretch")
            st.markdown("**Source data**")
            st.dataframe({
                "field": ["Rating", "Reviews", "Competitors 2 km",
                          "Retail POIs 2 km", "Biggest overlap with", "Distance",
                          "Coordinate"],
                "value": [r["rating"], r["n_reviews"], r["comp_2km"],
                          r["demand_2km"], r["worst_overlap_brand"] or "—",
                          f"{r['worst_overlap_km']} km" if r["worst_overlap_km"] else "—",
                          r["geo_confidence"]]},
                hide_index=True, width="stretch")
            if r["duel"]:
                st.info(f"Head-to-head: {r['duel']}")

# ------------------------------------------------------------- quadrant ---
with tabs[2]:
    st.caption("Branch health against the attractiveness of its market. Bubble "
               "size is review volume. Top right, protect; bottom left, review.")
    try:
        import pandas as pd
        import altair as alt
        df = pd.DataFrame([{
            "Attractiveness": r["_a"], "Health": r["_h"], "Reviews": int(r["n_reviews"]),
            "Branch": f"{r['brand']} · {r['branch_name']}",
            "Recommendation": r["recommendation"], "Cannibalisation": r["_c"],
        } for r in view])
        ch = alt.Chart(df).mark_circle(opacity=0.75).encode(
            x=alt.X("Attractiveness", scale=alt.Scale(domain=[-2, 102])),
            y=alt.Y("Health", scale=alt.Scale(domain=[-2, 102])),
            size=alt.Size("Reviews", scale=alt.Scale(range=[60, 900]), legend=None),
            color=alt.Color("Recommendation", scale=alt.Scale(
                domain=list(REC_COLOR), range=list(REC_COLOR.values()))),
            tooltip=["Branch", "Recommendation", "Health", "Attractiveness",
                     "Cannibalisation", "Reviews"],
        ).properties(height=520)
        st.altair_chart(ch, width="stretch")
    except Exception as e:
        st.error(f"Could not draw the quadrant: {e}")

# ---------------------------------------------------------- opportunity ---
with tabs[3]:
    cells = load("opportunity_cells.csv")
    g = [c for c in cells if c["opportunity"] == "GROW"]
    w = [c for c in cells if c["opportunity"] == "WATCH"]
    k1, k2, k3 = st.columns(3)
    k1.metric("GROW zones", len(g))
    k2.metric("WATCH zones", len(w))
    k3.metric("Coverage gaps",
              sum(1 for c in cells if int(c["coverage"]) == 0),
              help="Cells with commercial activity that no group salon reaches "
                   "within a 6-minute drive.")
    st.markdown("#### GROW zones, ranked by demand")
    g.sort(key=lambda c: -int(c["demand"]))
    st.dataframe([{
        "Zone": c["zone_name"] or c["cell_id"], "Retail POIs": int(c["demand"]),
        "Competitors": int(c["competitors"]),
        "Residential parcels": int(c["residential"]),
        "Nearest group site (km)": float(c["nearest_group_km"]),
        "Lat": round(float(c["lat"]), 4), "Lon": round(float(c["lon"]), 4),
    } for c in g], hide_index=True, width="stretch")
    st.caption("GROW = high demand, no group catchment reaches it, competition "
               "not saturated, and a residential catchment exists. WATCH = high "
               "demand but already half covered, saturated, or not residential.")

    rej = [c for c in cells if c["opportunity"] == "WATCH"
           and c["residential_catchment"] == "False"]
    if rej:
        with st.expander(f"Zones rejected for having no residential catchment ({len(rej)})"):
            st.caption("A salon serves residents, not warehouses. Without this "
                       "test the top recommendations were Musaffah, Khalid Port "
                       "and Dubai International Airport — places with a lot of "
                       "OSM points and nobody living in them. The flaw only "
                       "became visible once the cells were given their real "
                       "names instead of grid ids.")
            rej.sort(key=lambda c: -int(c["demand"]))
            st.dataframe([{
                "Zone": c["zone_name"] or c["cell_id"], "Retail POIs": int(c["demand"]),
                "Residential parcels": int(c["residential"]),
                "Industrial parcels": int(c["industrial"]),
            } for c in rej], hide_index=True, width="stretch")

# -------------------------------------------------------------- analyst ---
with tabs[4]:
    st.markdown("#### Network analyst")
    st.caption("The model never sees free text about the business: it picks a "
               "tool, the system runs that tool against the CSVs, and the model "
               "writes the answer using only what the tool returned. It cannot "
               "invent a recommendation, only narrate one.")
    ex = ["which branches should we close?",
          "where should we open a new site?",
          "compare Mirdif 35 with City Centre Mirdif",
          "why does Al Barsha get that recommendation?",
          "give me a summary of the network"]
    q = st.text_input("Question", value=ex[0])
    cols = st.columns(len(ex))
    for i, e in enumerate(ex):
        if cols[i].button(e[:22] + "…", key=f"ex{i}"):
            q = e
    if st.button("Ask", type="primary") or q:
        res = ask(q, llm)
        st.success(res["answer"])
        with st.expander(f"Traceability · tool `{res['tool']}` · mode: {res['mode']}"):
            st.write("**Arguments**"); st.json(res["args"])
            st.write("**Tool output (the only thing the model sees)**")
            st.json(res["tool_output"])

# --------------------------------------------------------------- method ---
with tabs[5]:
    st.markdown(f"""
#### Who decides, and what
The user is the **Head of Operations of Omorfia Group**, who signs off lease
renewals and terminations. For each branch, at renewal: invest, hold, or reduce
footprint and do not renew.

#### The four signals
| Signal | How it is built |
|---|---|
| Health | rating × log₁₀(reviews), converted to a percentile |
| Demand | retail and service POIs (OSM) inside the catchment |
| Competitive pressure | competing salons (OSM) in the same catchment |
| Cannibalisation | % of own catchment shared with another group site **in the same customer segment** |

`score = {wh:.2f}·health + {wa:.2f}·attractiveness − {wc:.2f}·cannibalisation`
with thresholds at network percentiles {p_shrink} and {p_protect}
(current scores: SHRINK < {thr_s:.1f}, PROTECT ≥ {thr_p:.1f}).

#### Why there is no trained model
There are no ground-truth labels: no history of closures marked as right or
wrong. A supervised classifier would be trained on labels derived from a rule,
so it would learn this same heuristic with more opacity, and with 53
observations it would overfit. On top of that, whoever uses this has to defend
a closure in front of a committee, and "the model says so" is not an argument.

#### Drive-time catchments
{iso.THRESHOLD_S // 60}-minute isochrones computed with OSRM over 16 radials
per site. 12 minutes was also tested: almost every salon saturated the sampling
and the model stopped discriminating. {len(iso.stats()[1])} sites fall back to
a circle because their coordinate is not routable.

#### Price positioning
Comparable manicure basket: **AED {prices.verdict()['basket_bedashing_aed']:.0f}**
at Bedashing against **AED {prices.verdict()['basket_tips_and_toes_aed']:.0f}**
at Tips & Toes, a {abs(prices.verdict()['index']-1)*100:.0f}% gap. Same price
tier, so the hypothesis that they compete for the same customer holds, and the
cannibalisation metric is valid.

#### Where NOT to trust this
1. **A rating is not revenue.** The whole health axis is a proxy. A neighbourhood
   salon with a loyal base can have few reviews and the best margin in the network.
2. **The health proxy punishes new branches**, because review count accumulates
   with age. Bedashing Noya Plaza rates 4.7 on 209 reviews because it opened
   recently, and the model reads that as health percentile 17. **That SHRINK is
   an artifact and should not be acted on.** The fix is opening date as a feature.
3. **Review volume favours urban and old.** Part of a high count is quality and
   part is simply age and footfall.
4. **Tips & Toes and Jazz coordinates are still geocoded.** All 24 Bedashing
   coordinates were verified one by one against their Google Maps place page,
   and doing so changed six recommendations. Assume verifying the other 50 will
   change some of theirs.
5. **11 Tips & Toes ratings are missing** in peripheral markets. None of them
   overlaps a Bedashing branch, so no recommendation in the brief moves.
6. **OpenStreetMap coverage in the UAE is uneven**: density partly measures how
   well an area is mapped, not only how saturated it really is. Al Ain returns
   1 retail POI within 2 km, which is a mapping fact, not a market fact.
7. **A mall site breaks the catchment model**: it draws on mall footfall, not on
   the neighbourhood. There is an `in_mall` flag the model does not yet use.
8. **The thresholds are relative**: the model says who is worst inside this
   network, not who loses money. That needs P&L data.

#### What I would do with four more weeks and POS access
A demand model on actual revenue (revenue ≈ f(location)) applied to the GROW
zones to size the return on an opening; sentiment analysis over the review text
rather than just the topics; and a catchment correction for mall footfall.
""")
