"""
Adversarial checks over the whole pipeline.

    python tests/test_pipeline.py

Not happy-path tests. Every defect that mattered in this project was silent:
coordinates verified without recomputing what depended on them, opportunity
zones that turned out to be industrial estates, an AI router fed the output a
real model actually returns rather than the one I assumed. So each check
asserts an invariant a silent failure would break, or feeds a component
something hostile.

No framework, on purpose: one file, no dependencies, exits non-zero on failure.
"""

import csv, pathlib, sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
DATA = BASE / "data"

FAILS = []


def chk(name, cond, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + name + ("" if cond else f" -> {detail}"))
    if not cond:
        FAILS.append(name)


def rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def data_integrity():
    print("== data integrity ==")
    sh, ms = rows("group_shops_features.csv"), rows("master.csv")
    pr, ce = rows("overlap_pairs.csv"), rows("opportunity_cells.csv")
    ids = [s["shop_id"] for s in sh]

    chk("shop ids are unique", len(set(ids)) == len(ids))
    chk("master is a subset of the shop list", set(m["shop_id"] for m in ms) <= set(ids))
    optional = ("duel", "worst_overlap_with", "worst_overlap_brand", "worst_overlap_km")
    chk("no empty required fields in master",
        all(v != "" for m in ms for k, v in m.items() if k not in optional))

    # If this drifts, the score decomposition shown to the user is a lie.
    chk("score equals the sum of its contributions",
        all(abs(float(m["score"]) - (float(m["c_health"]) + float(m["c_attract"])
                                     + float(m["c_cannib"]))) < 0.02 for m in ms))
    chk("percentile signals stay within 0..100",
        all(0 <= float(m[k]) <= 100 for m in ms
            for k in ("sig_health", "sig_attract", "sig_cannib", "sig_demand", "sig_pressure")))
    chk("stability stays within 0..100", all(0 <= float(m["stability"]) <= 100 for m in ms))
    chk("overlap fractions stay within 0..1",
        all(0 <= float(p["overlap_frac"]) <= 1.0001 for p in pr))
    chk("labels are from the allowed set",
        set(m["recommendation"] for m in ms) <= {"PROTECT", "HOLD", "SHRINK"})
    chk("opportunity labels are from the allowed set",
        set(c["opportunity"] for c in ce) <= {"GROW", "WATCH", "SKIP"})
    chk("every catchment has positive area", all(float(s["catchment_km2"]) > 0 for s in sh))

    # The 34 km Al Taif Mall error would have been caught here.
    chk("every coordinate falls inside the UAE",
        all(22.5 <= float(s["lat"]) <= 26.3 and 51.4 <= float(s["lon"]) <= 56.6 for s in sh))

    # Competitor and demand counts must be measured at the coordinate actually
    # used. A branch with a real catchment and zero of everything around it is
    # the signature of the provenance bug: signals computed somewhere else.
    suspect = [m for m in ms if int(m["demand_2km"]) == 0 and int(m["comp_2km"]) == 0
               and m["emirate"] in ("Dubai", "Sharjah")]
    chk("no urban branch reads zero demand and zero competition",
        not suspect, [m["branch_name"] for m in suspect])


def rule_coherence():
    print("\n== rule coherence ==")
    import scoring as S
    ms, ce = rows("master.csv"), rows("opportunity_cells.csv")

    causeless = [m for m in ms if m["recommendation"] == "SHRINK"
                 and not (float(m["sig_cannib"]) >= S.MIN_CANNIB_FOR_SHRINK
                          or float(m["sig_health"]) < S.MAX_HEALTH_FOR_SHRINK)]
    chk("every SHRINK has a nameable cause", not causeless,
        [m["branch_name"] for m in causeless])
    chk("every branch has a written reason", all(len(m["reason"]) > 20 for m in ms))
    chk("every GROW zone has a residential catchment",
        all(c["residential_catchment"] == "True" for c in ce if c["opportunity"] == "GROW"))
    chk("every GROW zone is genuinely uncovered",
        all(int(c["coverage"]) == 0 for c in ce if c["opportunity"] == "GROW"))
    chk("GROW zones are named, not grid ids",
        all(c["zone_name"] for c in ce if c["opportunity"] == "GROW"))


def pure_functions():
    print("\n== pure functions, edge cases ==")
    import scoring as S, isochrones as iso, prices, review_themes as rt
    import competitor_points as cp

    chk("pct_rank of a single value", S.pct_rank([5.0]) == [50.0])
    chk("pct_rank when everything ties", S.pct_rank([2, 2, 2]) == [50.0, 50.0, 50.0])
    chk("percentile at both extremes",
        S.percentile([1, 2, 3], 0) == 1 and S.percentile([1, 2, 3], 100) == 3)

    pts, fb = iso.polygon("a_shop_id_that_does_not_exist", 25.0, 55.0)
    chk("unknown shop falls back to a circle", fb and len(pts) >= 17)
    chk("isochrone ring is closed", pts[0] == pts[-1])
    chk("known isochrone has positive area", (iso.area_km2("bd_al_barsha") or 0) > 0)

    chk("competitor density is zero in the Atlantic", cp.density(0.0, 0.0) == [0, 0, 0])
    d = cp.density(25.1131, 55.2156)
    chk("competitor density grows with radius", d[0] <= d[1] <= d[2], d)

    idx, bd, tt = prices.price_index()
    chk("price index matches its own basket", abs(idx - bd / tt) < 1e-9)
    chk("price verdict agrees with the index",
        prices.verdict()["same_price_tier"] == (0.80 <= idx <= 1.25))

    chk("review themes tolerate an unknown shop", rt.summary_line("nope") == "")
    fl = rt.flagged("bd_khalifa_city_a")
    chk("operational flags are not duplicated", len(fl) == len(set(x[2] for x in fl)))


def ai_layer():
    print("\n== AI layer, hostile input ==")
    import ai_layer as A

    for q in ["", "   ", "?????", "DROP TABLE shops;", "a" * 3000,
              "compare with", "compare  with  ", "¿qué tal?"]:
        try:
            r = A.ask(q)
            ok = isinstance(r.get("answer"), str) and len(r["answer"]) > 0
            detail = ""
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        chk(f"ask({q[:16]!r}) returns an answer", ok, detail)

    chk("get_branch reports an unknown branch", "error" in A.get_branch("zzz"))
    chk("compare reports an unknown branch", "error" in A.compare("zzz", "yyy"))
    chk("list_branches handles an empty filter",
        A.list_branches(recommendation="NOPE")["count"] == 0)

    # A real model returns fenced JSON, invents tool names, invents argument
    # names, and dies mid-answer. Each of those crashed something at some point.
    class Stub(A.LLM):
        def __init__(self, out, die=False):
            self.provider, self._out, self._die = "stub", out, die
        @property
        def available(self):
            return True
        def complete(self, system, user):
            if system.startswith("You are the router"):
                return self._out
            if self._die:
                raise ConnectionError("provider died")
            return "written by the model"

    cases = [
        ("fenced json", '```json\n{"tool":"network_summary","args":{}}\n```', False),
        ("hallucinated tool", '{"tool":"drop_everything","args":{}}', False),
        ("unparseable output", 'sorry, I cannot do that', False),
        ("invented argument names", '{"tool":"compare","args":{"foo":1}}', False),
        ("missing required arguments", '{"tool":"compare","args":{}}', False),
        ("surplus arguments", '{"tool":"network_summary","args":{"x":1}}', False),
        ("provider dies while writing", '{"tool":"network_summary","args":{}}', True),
    ]
    for label, out, die in cases:
        try:
            r = A.ask("compare Mirdif 35 with City Centre Mirdif", Stub(out, die))
            ok, detail = isinstance(r.get("answer"), str) and len(r["answer"]) > 0, ""
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        chk(f"router survives: {label}", ok, detail)


def outputs():
    print("\n== generated outputs ==")
    out = BASE / "out"
    for f, floor in (("decision_map.html", 50_000), ("network_map.html", 50_000)):
        p = out / f
        chk(f"{f} exists and has markers",
            p.exists() and len(p.read_bytes()) > floor
            and p.read_text(encoding="utf-8").lower().count("circlemarker") > 10)
    png = out / "quadrant.png"
    chk("quadrant.png is a valid PNG",
        png.exists() and png.read_bytes()[:8] == bytes([0x89]) + b"PNG\r\n\x1a\n")


def main():
    data_integrity()
    rule_coherence()
    pure_functions()
    ai_layer()
    outputs()
    print(f"\n=== {len(FAILS)} failed ===")
    for f in FAILS:
        print("   !", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
