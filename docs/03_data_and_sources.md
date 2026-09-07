# Data and sources

Status: **complete and verified**. 74 branches, 0 blocking errors, 6 coordinates
still flagged low-confidence (all Tips & Toes or Jazz, none in the case brand).

---

## 1. What is here and where it comes from

| File | Rows | What it is |
|---|---|---|
| `data/group_shops.csv` | 74 | Group branches with address and raw geocoded coordinate |
| `data/group_shops_features.csv` | 74 | The above + verified coordinates, catchment, competition, cannibalisation |
| `data/group_shops.geojson` | 74 | The same in GIS format |
| `data/catchments.geojson` | 74 | The drive-time isochrone polygons |
| `data/overlap_pairs.csv` | 110 | Branch pairs whose catchments intersect, artifacts flagged |
| `data/master.csv` | 53 | One row per scored branch: signals, score, label, stability, reason |
| `data/opportunity_cells.csv` | 192 | Grid cells with demand, saturation, coverage, GROW/WATCH/SKIP |
| `data/demand_density.csv` | 74 | Retail POI counts at 1 / 2 / 3 km |

### Primary sources

| What | Source | Date | Coverage |
|---|---|---|---|
| Bedashing branches | `bedashingbeauty.com/lounges/` | 2026-09-03 | 24 |
| Tips & Toes branches | `tipsandtoes.com/store-locator/` | 2026-09-03 | 42 rows → 40 in the UAE |
| Jazz Lounge Spa branches | `jazzloungespa.com/locations/` | 2026-09-03 | 10 |
| Ratings and review volume | Google Maps place pages | 2026-09-03 | 24/24 BD, 28/40 T&T |
| Review topics | Google Maps topic chips | 2026-09-07 | 23/24 BD |
| Verified coordinates | Google Maps place-page canonical URL | 2026-09-07 | 24/24 BD |
| Competition (density + points) | OpenStreetMap via Overpass API | 2026-09-07 | 2,606 POIs UAE-wide, 872 within 3 km of a group site |
| Retail demand | OpenStreetMap via Overpass API | 2026-09-07 | 41,957 POIs UAE-wide |
| Drive times | OSRM public server | 2026-09-07 | 64 sites × 16 radials × 6 samples |
| Prices | Zenoti booking stores (both brands) | 2026-09-07 | Matched manicure basket |

All three store locators are JavaScript-rendered, so none of them is reachable
with a plain HTTP fetch. The Google Places API is deliberately not used: it is
paid, and the brief asks for something that runs without external dependencies.

---

## 2. Coordinate quality

| Confidence | Sites | Meaning |
|---|---|---|
| `verified` | 24 | Taken from the business's own Google Maps place page. All Bedashing. |
| `high` | 21 | Geocoder returned the exact point or the specific mall |
| `medium` | 23 | Correct street or neighbourhood, not the exact number |
| `low` | 6 | Only a city or broad-area centroid could be resolved |

**This is not a footnote, it is the most consequential data-quality issue in the
project.** The cannibalisation model rests entirely on the distance between
sites over a catchment of a few kilometres, so a 1 km error changes the overlap
completely and a 34 km error changes which emirate is being analysed.

Largest shifts found on verification:

| Branch | Geocoded | Verified | Shift |
|---|---|---|---|
| Al Taif Mall (Fujairah) | 25.41474, 56.23137 | 25.12026, 56.32535 | **34.4 km** |
| Khalifa City A | 24.42013, 54.57495 | 24.43998, 54.59891 | 2.8 km |
| Khaleej Al Arabi | 24.45138, 54.33797 | 24.45887, 54.35378 | 1.7 km |
| Mirdif 35 | 25.22184, 55.42315 | 25.23230, 55.43296 | 1.4 km |

**Six recommendations changed** on recomputation. Both the raw geocode
(`src/build_shops.py`) and the verified coordinate
(`src/verified_locations.py`) are kept in the repository, because the delta
between them is part of the evidence.

### 2.1 The provenance defect

Verifying the coordinates was only half the job, and I initially did only that
half.

The competitor and demand densities were computed once, early, at the
**geocoded** coordinates — and never recomputed after the coordinates were
verified. So the catchment geometry described the real positions while the
demand and competition signals still described the old ones. Half the model was
measuring a different set of places from the other half.

The clearest symptom, once looked for: **Bedashing Al Taif Mall was reading 0
retail POIs within 2 km.** Its demand was being counted 34 km away, at the
geocode, in an area OSM barely maps. At the verified coordinate it has 244.

A second, smaller defect surfaced in the same pass: the original competitor
query asked for nodes only, so it missed the 61 competitors mapped as building
polygons rather than points.

Both were fixed by re-extracting once, UAE-wide, with `nwr` instead of `node`,
and recomputing every per-branch count from the verified coordinates.
**A further six recommendations changed.**

Two things are worth saying about this rather than quietly shipping the fix:

- The failure was **completely silent**. Nothing errored. Every number was a
  plausible number. Al Taif Mall having no shops near it in Fujairah is not
  absurd enough to notice unaided — it only stood out once the same figure was
  recomputed from a different starting point and disagreed.
- The generalisable lesson is that **a corrected input is worthless until every
  quantity derived from it is recomputed**. The pipeline now regenerates end to
  end from one sequence of commands, which is not tidiness — it is the control
  that catches this class of bug.

### Geocoding artifacts

Two sites geocoded to the same neighbourhood centroid produce a distance of ~0
and a total overlap, which is false. Those pairs are flagged `geocode_artifact`
and **excluded** from the cannibalisation calculation: **16 of 110 pairs**.
Without that filter the cannibalisation ranking would be led by false positives.

The filter is conservative by design — it only fires when at least one of the
two coordinates is *not* high-confidence or verified, so two genuinely
co-located verified sites are still counted.

---

## 3. Decisions taken, and why

### 3.1 The perimeter is Omorfia, not Bedashing

Covered in `01_business_framing.md`. Short version: the brief asks where "we"
overlap with ourselves, and the "we" is the group. 74 sites across three brands,
not 24 across one. Bedashing and Tips & Toes share an exact registered address.

### 3.2 Jazz Lounge Spa does not cannibalise the other two

Jazz Lounge Spa is a **men's spa**; Bedashing and Tips & Toes are women's
salons. They share a street but not a customer.

The dataset therefore carries a `segment` column (`women` / `men`) and the
calculation splits two metrics:

- `cannibalisation` → overlap **within the same segment**. This is the one that
  hurts.
- `cross_segment_overlap` → overlap across segments. This is deliberate
  co-location, not a problem: Bedashing Mirdif 35 with Jazz Mirdif, and Tips &
  Toes Yas Mall with Jazz Yas Mall, both sit at 100% — that is couple coverage,
  not a network error.

Treating the 74 sites as one undifferentiated block would have inflated
cannibalisation and flagged for closure sites that do not compete with each
other.

### 3.3 Price tier: testing the premise instead of assuming it

The cannibalisation model assumes Bedashing and Tips & Toes compete for the same
customer. If one were premium and the other budget, that assumption would be
false and the whole cannibalisation axis would be inflated.

A matched basket of three standard manicure services was pulled from both
brands' Zenoti booking stores:

| Service | Bedashing | Tips & Toes |
|---|---|---|
| Basic manicure | AED 85 | AED 90 |
| Express / file manicure | AED 105 | AED 100 |
| Russian manicure | AED 152 | AED 120 |
| **Basket** | **AED 342** | **AED 310** |

Index 1.103 — a 10% gap. **Same price tier, so the premise holds** and the
cannibalisation metric is valid.

A second finding fell out of the check: **prices do not vary by branch.** The
same services were compared at Khalifa City A (Abu Dhabi) and City Walk (Dubai)
and matched to the fils. Price is a brand decision, not a site decision, so this
variable sits at brand level and correctly does not enter the per-branch score.

### 3.4 Competition as density in the model, as points on the map

For the model, the 872 competitors within 3 km of a group site are reduced to
**density per branch** (count within 1, 2 and 3 km). To decide whether a zone is
saturated, the count inside the catchment is the signal; 872 individual pins are
visual noise at network scale.

The points themselves are kept in `src/competitor_points.py` and available as an
optional map layer, off by default, because a director looking at one specific
branch does want to see who is actually on that street. The split is deliberate:
density decides, points inform.

Breakdown: 541 hairdressers, 299 beauty salons, 25 massage, 7 spa. The full
UAE-wide list regenerates with `src/fetch_competitors.py`.

Both come from one extraction, which was not true of an earlier version. See
§2.1 below — that inconsistency turned out to be the second-largest data defect
in the project.

### 3.5 Review topics enrich, they do not score

Google's topic chips ("pedicure, mentioned in 62 reviews") turn a number into a
diagnosis: customers talking about "cleanliness" is a different problem from
customers talking about "receptionist". They feed the branch narrative and the
AI layer.

They deliberately do **not** enter the score. The chips carry no polarity —
heavy mention of "technician" is neither good nor bad — and giving them a sign
would require sentiment analysis over the full review text, which is the natural
next step rather than something to fake now.

Google's extraction is also unsupervised and noisy: it picks up staff names
("faouzia", "asmahan") and plain mis-parses ("cherry", "poetry", "rage"). Those
are left in the file rather than quietly cleaned, because removing them would
overstate how clean the signal is. Only the topics in `OPERATIONAL_FLAGS` are
acted on.

---

## 4. Where NOT to trust this data

1. **Six coordinates are approximate** (`geo_confidence = low`) — all Tips &
   Toes or Jazz. They resolved to an area centroid because the address was not
   resolvable. Highlighted on a separate map layer.

2. **50 of 74 coordinates are still geocoded, not verified.** Verifying the 24
   Bedashing ones changed six recommendations. There is no reason to think Tips
   & Toes would behave differently. This is the top item on the next-steps list.

3. **Three Dubai sites show 0 competitors within 3 km** (Mira Town Centre, The
   Valley, The Villa). In urban Dubai that is implausible: either the coordinate
   is wrong, or OSM coverage in those new developments is poor. Probably both.

4. **OpenStreetMap coverage in the UAE is uneven.** Some areas are well mapped
   (Marina, Al Nahyan) and others nearly empty. Competitive density partly
   measures *how well an area is mapped*, not only its real saturation. Do not
   compare densities across emirates without allowing for it.

5. **Branch-count discrepancy.** The 2PointZero corporate page states 21
   Bedashing branches in 4 emirates; the brand's own store locator lists 24 in 6
   (adding Sharjah and Fujairah). The brand's figure is used as the more recent
   one, but the difference would need clarifying with the client.

6. **11 Tips & Toes ratings are missing** (Ruwais, Al Furjan, Al Hamra, Al Ain
   Hili Mall, Jimi, Makani, Marina Vista, The Valley and others), plus all 10
   Jazz sites, which are out of scope by segment. None of the 11 overlaps a
   Bedashing branch, so no recommendation about the case brand is affected — but
   the Tips & Toes ranking is incomplete.

7. **OSRM is a public free service.** The isochrones were computed once and the
   radii are committed in `src/isochrones.py`, so the project reproduces without
   network access. Recomputing them against a live OSRM may give slightly
   different results as OSM road data changes.

---

## 5. How to reproduce it

```bash
python src/build_shops.py            # branches            -> data/group_shops.csv
python src/fetch_competitors.py      # OSM competition     (needs network; output committed)
python src/build_features.py         # isochrones, overlap -> features, pairs, geojson
python src/verify_data.py            # sanity checks       -> console
python src/scoring.py                # decisions           -> data/master.csv
python src/opportunity.py            # zones               -> data/opportunity_cells.csv
python src/build_map.py              # map                 -> out/network_map.html
python src/build_decision_outputs.py # map + quadrant      -> out/
```

Every step except `fetch_competitors.py` runs offline.
