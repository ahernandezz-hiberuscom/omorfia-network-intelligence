# Omorfia Network Intelligence

AI-enabled geospatial decision support for retail network right-sizing.
Case study submission · Bedashing Beauty Lounge / Omorfia Group.

**Demo video:** https://youtu.be/vR3sH8KYIfw

## Run it

Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

No API keys, no network access, no database. Every number in the app comes from
the CSVs committed in `data/`, and the Analyst tab works with zero credentials.
If you have no Python to hand, `out/decision_map.html` and `out/network_map.html`
open in any browser.

Two things worth reading next:
[`docs/01_business_framing.md`](docs/01_business_framing.md), which defines who
decides and what and was written before any code, and the "Method and limits"
tab in the app, which is the same reasoning next to the numbers it produced.

## What it produces

For each of the 53 scored branches, a recommendation at lease renewal with a
written reason, the score decomposition, and a stability measure:

| Label | Meaning |
|---|---|
| PROTECT | Renew and invest: refit, headcount, local marketing |
| HOLD | Renew as-is, revisit next quarter |
| SHRINK | Renegotiate down, do not renew, or relocate |

And over the territory rather than the estate, GROW / WATCH / SKIP by named
zone, plus the coverage gaps.

Bedashing's 24 branches come out **12 PROTECT / 10 HOLD / 2 SHRINK**. Of the 17
SHRINK recommendations across the network, **15 are Tips & Toes**: the
right-sizing problem is not inside Bedashing, it is in the overlap Tips & Toes
has with Bedashing and with itself. On the growth side, 192 grid cells come out
21 GROW / 54 WATCH / 117 SKIP, with 152 cells of commercial activity that no
group site reaches within a 6-minute drive. Best candidate: Al Shindagha,
Dubai, with 798 retail POIs, 7 competing salons and the nearest group site 5.1
km away.

## The model in short

Four signals, each a 0–100 percentile within the scored universe: **health**
(rating × log₁₀ reviews), **demand** (retail POIs within 2 km), **competitive
pressure** (competing salons within 2 km), and **cannibalisation** (% of own
drive-time catchment shared with a group site in the same customer segment).

```
attractiveness = percentile( log(demand) - 0.5·log(competitors) )
score          = 0.40·health + 0.35·attractiveness - 0.25·cannibalisation

PROTECT   score >= 66th percentile
SHRINK    score <  33rd percentile  AND  (cannibalisation >= 30%  OR  health < p40)
HOLD      everything else
```

The weights are a business decision, not an output of the data, which is why
they are sliders in the app. The second SHRINK condition is deliberate: a bare
percentile cut sends a third of the network to SHRINK even when the network is
healthy, so the model demands a nameable cause before recommending a closure.

Three choices worth arguing with, all argued in
[`docs/02_decision_model.md`](docs/02_decision_model.md):

- **The scope is the group, not the brand.** The brief asks where "we" overlap
  with ourselves. Bedashing belongs to Omorfia Group alongside Tips & Toes and
  Jazz Lounge Spa, formed by merging chains that used to compete, so the
  perimeter is 74 sites across three brands. Analysing Bedashing against
  Bedashing answers the literal question and misses the real one.
- **Cannibalisation is asymmetric and segment-aware.** Computed per site, not
  per pair, because the question is not "do they overlap?" but "which of the two
  is redundant?". Tips & Toes Khaleej Al Arabi loses 81% of its catchment to the
  Bedashing branch 1.8 km away; that Bedashing branch loses 51% back.
- **No trained model, on purpose.** There are no ground-truth labels, so a
  classifier would learn this same heuristic with more opacity and overfit on 53
  observations. More to the point, the user has to defend a closure in front of
  a committee, and "the model says so" is not an argument.

## The AI layer

The Analyst tab is a tool-using agent, not a chatbot over the data. The model
never sees free text about the business: it sees a question, picks one of six
tools, and the pipeline runs that tool against the CSVs. The model then writes
the answer using only the JSON the tool returned, so it cannot invent a
recommendation, only narrate one. Every answer ships with a traceability panel
showing the tool, its arguments and its raw output.

```
list_branches(brand?, recommendation?, limit?)   compare(branch_a, branch_b)
get_branch(branch)                               find_whitespace(limit?)
explain(branch)                                  network_summary()
```

Set `GEMINI_API_KEY`, `GROQ_API_KEY` or `OPENAI_API_KEY` (+ `OPENAI_BASE_URL`)
to use a real model; the adapter takes the first one it finds. With no
credentials the tab still works: a deterministic keyword router picks the tool
and templates compose the answer from the same tool output, labelled visibly as
"no model". The routing layer is tested against a stubbed provider for each
failure mode, so fenced JSON, hallucinated tool names, invented argument names
and a provider that dies mid-answer all degrade to the deterministic path
instead of crashing.

## Where to trust it

The weights are arguable, so they are stress-tested: 2,000 simulations perturb
them with Gaussian noise (σ = 0.08) and renormalise, measuring how often each
branch keeps its label. **41 of 53 robust (≥85%), 10 medium, 2 fragile.** Both
fragile branches are Tips & Toes, and every Bedashing recommendation is robust
or medium. Fragile ones are dashed on the map and flagged in the app.

The three limits that matter most, with the full list in
[`docs/03_data_and_sources.md`](docs/03_data_and_sources.md) and in the app's
"Method and limits" tab:

1. **A rating is not revenue.** The whole health axis is a proxy. No closure
   should be executed on this output without crossing it against the POS.
2. **The health proxy punishes new branches**, because review count accumulates
   with age. Bedashing Noya Plaza rates 4.7 on 209 reviews because it opened
   recently, and the model reads that as health percentile 17 and recommends
   SHRINK. That one is an artifact and should not be acted on.
3. **Only Bedashing's coordinates are hand-verified.** Verifying those 24
   changed six recommendations, so assume verifying the other 50 will change
   some of theirs.

That third point is the finding I would carry into a real version. Before
verification the headline was a duel in Mirdif, with Mirdif 35 sharing 49% of
its catchment with Tips & Toes City Centre Mirdif. It was a geocoding artifact:
with the real coordinate the overlap is 19%, and the real overlap was hiding at
Al Barsha, which geocoding had recorded as 0%. The competitor and demand
densities were then still being measured at the old coordinates, which is why
Al Taif Mall read 0 retail POIs when it has 244. A corrected input is worthless
until every derived quantity is recomputed from it, and the failure is silent.

## How AI was used to build this

Claude was used throughout as a working tool: to pull the store locators and
Google Maps place pages (all three locators are JavaScript-rendered), to draft
and refactor the pipeline, and as a sparring partner on the modelling choices.
Two of the decisions above came from arguing with it and losing. Every number in
the deliverable was verified against its source, and the parts I do not trust
are written down rather than smoothed over.

## Reproducing the pipeline

```bash
python src/build_shops.py             # 74 branches           -> data/group_shops.csv
python src/build_features.py          # isochrones + overlap  -> features, pairs, geojson
python src/verify_data.py             # sanity checks         -> console
python src/scoring.py                 # decisions + stability -> data/master.csv
python src/opportunity.py             # GROW/WATCH/SKIP       -> data/opportunity_cells.csv
python src/build_map.py               # exploratory map       -> out/network_map.html
python src/build_decision_outputs.py  # decision map + chart  -> out/
python tests/test_pipeline.py         # 50 checks
```

Only `src/fetch_competitors.py` needs the network (Overpass API), and you never
have to run it: the extraction it produced is committed, embedded in
`src/competitor_points.py` and `data/demand_density.csv`.
`tests/test_pipeline.py` is not a happy-path suite: each check asserts an
invariant a silent failure would break, or feeds a component something hostile.

## Layout

```
app.py                         Streamlit application, 6 tabs
src/build_shops.py             74 branches from the three official store locators
src/verified_locations.py      24 hand-verified Bedashing coordinates
src/isochrones.py              6-minute drive-time catchments (OSRM)
src/build_features.py          catchment geometry + asymmetric cannibalisation
src/fetch_competitors.py       OpenStreetMap competitor extraction (needs network)
src/competitor_points.py       872 competitor locations within 3 km of the network
src/ratings.py                 Google Maps ratings and review volumes
src/review_themes.py           Google review topic chips, 23 branches
src/prices.py                  price-tier test: does the cannibalisation premise hold?
src/scoring.py                 decision engine + Monte Carlo sensitivity
src/opportunity.py             GROW / WATCH / SKIP by named zone
src/ai_layer.py                tool-using analyst + no-model fallback
src/verify_data.py             sanity checks on the geocoding
src/build_map.py               exploratory map
src/build_decision_outputs.py  decision map + quadrant chart
tests/test_pipeline.py         invariants + hostile input, no framework

data/       master.csv (one row per scored branch), overlap_pairs.csv,
            opportunity_cells.csv, geojson for points, catchments and cells
docs/       01 business framing · 02 decision model · 03 data and sources
out/        decision_map.html, network_map.html, quadrant.png
```

## With four more weeks and POS access

Verify the remaining 50 coordinates and recompute every signal from them
(highest return per hour on this list, and not modelling work); fit a demand
model on actual revenue and apply it to the 21 GROW zones to turn "this zone
looks good" into an estimated payback; replace the health proxy with margin per
m²; add opening dates so health stops punishing new sites; run sentiment
analysis over the review text rather than Google's topic chips; correct the
catchment for mall footfall using the `in_mall` flag already in the data; and
add lease cost and floor area, which turns SHRINK from a binary into the
decision it really is.

---

Aitor Hernández Zabala · September 2026
