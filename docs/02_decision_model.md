# The decision model

## 1. Who decides, and what

**Decision-maker:** the Head of Operations of Omorfia Group, who approves lease
renewals and terminations across the salon portfolio.

**Concrete decision:** for each branch, at lease renewal — invest, hold, or
reduce the footprint and not renew?

**Metric that moves:** margin per square metre of the network. We do not have
it, so we work with the three factors that determine it and that are
observable: how well the branch executes, how good its market is, and how much
it overlaps another site owned by the same group.

---

## 2. The four signals

All normalised to a 0–100 percentile within the scored universe, so they are
comparable with each other.

| Signal | How it is built | Why that way |
|---|---|---|
| **Health** | `rating × log₁₀(reviews)` | The log because a review's information value decays: 100 → 200 says a lot, 2,000 → 2,100 says nothing. Without it, old and large sites win on volume alone. |
| **Demand** | Retail and service POIs within 2 km | Proxy for urban intensity. From OpenStreetMap. |
| **Competitive pressure** | External competitors within 2 km | Salons, hairdressers, spas and massage centres from OSM. |
| **Cannibalisation** | % of the catchment shared with a group site **in the same customer segment** | The central metric of the brief. |

**Market attractiveness** = `log₁₀(demand + 1) − 0.5 · log₁₀(competitors + 1)`,
then percentiled.

That coefficient matters and it is worth stating why. The first version of this
model used `percentile(demand) − percentile(pressure)`, which puts demand and
competition on equal footing. The data showed that to be wrong: **Bedashing Ras
Al Khaimah has 32 retail POIs within 2 km and zero competitors, and the old
formula ranked its market in the 92nd percentile.** An empty region is not an
attractive market just because nobody else is there either — there is nobody to
serve.

So demand leads and competition discounts it, on raw magnitudes rather than
ranks, with a coefficient below 1 so demand always dominates. At 0.5, a market
has to quadruple its competitor count to lose the ground it gains by doubling
its demand.

**Score** = `0.40 × health + 0.35 × attractiveness − 0.25 × cannibalisation`

The weights are a business decision, not a result of the data. They are exposed
as constants — and as sliders in the app — so they can be argued with.

---

## 3. The rule, and its guardrail

```
PROTECT   score ≥ 66th percentile
SHRINK    score < 33rd percentile  AND  (cannibalisation ≥ 30%  OR  health < p40)
HOLD      everything else
```

The second SHRINK condition is deliberate. **A percentile cut on its own forces
a third of the network into SHRINK even when the network is healthy.** A
percentile says which site is relatively worst, not which is unviable. To drop
a branch to SHRINK we demand a concrete, nameable cause.

---

## 4. Catchments by drive time, not by radius

The brief asks explicitly for travel-time logic, and rightly so: a 2 km circle
treats an address on a motorway and one cut off by the sea, a creek or a mall
wall as identical. In Abu Dhabi and Dubai that matters a great deal.

For each site, 16 radials are cast with six sampling points each, and the OSRM
`table` service returns the real driving time to every point. The furthest
reachable point within the threshold on each radial forms a 16-vertex isochrone.

**Threshold: 6 minutes.** That is a decision, not a fact. 12 minutes was also
tested and practically every salon saturated the sampling: at that threshold the
model stopped discriminating and everything overlapped everything. Six minutes
keeps the area comparable to a 2 km circle but with the real shape of the road
network — median catchment 7.2 km², range 0.9 to 25.2 km².

**61 of 64 sites** in the isochrone set produce a usable polygon. The rest, plus
the 10 sites never queried, fall back to a 2 km circle and are flagged per site
in `catchment_source`.

---

## 5. Why there is no trained model

**There are no ground-truth labels.** There is no history of closures marked as
right or wrong. Any supervised classifier would have to be trained on labels
derived from a rule — meaning it would learn this same heuristic while adding
opacity. With 53 observations and four variables it would also overfit
immediately.

And there is a product reason above the statistics: **the end user has to defend
a closure in front of a committee.** In that meeting, "the model says so" is not
an argument. A weighted score is auditable, adjustable by the business, and
holds up.

Where machine learning *would* fit, and cannot here:

- **A demand model on revenue.** With POS data for part of the estate, fit
  revenue ≈ f(location) and apply it to empty zones. That is the classic
  site-selection model and the first thing to build with POS access.
- **Unsupervised clustering** to discover store archetypes. Needs no labels. The
  natural next addition.

---

## 6. Sensitivity analysis: where to trust this and where not

The weights are arguable, so rather than defend them we stress-test them:
**2,000 simulations** perturbing the three weights with Gaussian noise
(σ = 0.08) and renormalising. For each branch we measure the share of
simulations in which it keeps its recommendation.

- **Robust** (≥ 85%): the recommendation does not depend on how the business
  weights the signals.
- **Medium** (60–85%).
- **Fragile** (< 60%): **do not take irreversible decisions here without more
  data.**

Result: **41 of 53 robust, 10 medium, 2 fragile.**

| Branch | Label | Stability | What it means |
|---|---|---|---|
| Tips & Toes Business Bay | PROTECT | 58% | A strong market with middling execution and 29% overlap with The Dubai Mall. Whether it protects depends entirely on how hard cannibalisation is penalised. |
| Tips & Toes Al Barsha | HOLD | 56% | Cedes 66% of its catchment to Bedashing Al Barsha and sits right on the SHRINK boundary. A small shift in the cannibalisation weight tips it over. |

Neither fragile branch is in Bedashing. Every Bedashing recommendation is robust
or medium, the weakest being Shakhbout City (HOLD, 68%) and Al Barsha
(PROTECT, 82%).

---

## 7. Results

### Bedashing, 24 branches

| | Count |
|---|---|
| PROTECT | 12 |
| HOLD | 10 |
| SHRINK | 2 |

**Bedashing is the strong brand in the group.** Its ratings run 4.4 to 4.9;
Tips & Toes runs 4.0 to 4.7. In a joint ranking Bedashing occupies the top. That
is not an artifact of the model: it is the finding.

### The two Bedashing SHRINKs, and why one of them is wrong

**Al Dhafra (Zayed City).** Health at percentile 27 (4.5 from 358 reviews) and a
weak market (demand p6, competitive pressure p11). A site in a remote region
with almost no commercial activity around it. **It cannibalises nobody**: the
market simply does not carry it. Stability 100%. This is the least uncomfortable
recommendation possible — it does not force a choice between two group sites,
and it does not depend on the weighting.

**Noya Plaza (Yas Island) — do not act on this one.** The model flags it because
health sits at percentile 17. But it rates **4.7**, among the best in the
network, on only 209 reviews *because it opened recently*. Review count
accumulates with age, so the health proxy punishes new branches by construction.
This is the model being wrong in a way the model cannot see, and the honest thing
is to name it rather than let a reviewer find it. The fix is branch opening date
as a feature — data the brand has and the public web does not.

That distinction is the whole point of writing the reason out per branch: Al
Dhafra's reason names a market that does not exist, Noya Plaza's names only a
low review count, and a reader can tell the two apart.

### What the data corrections changed

Two corrections moved the answer more than any modelling decision did.

**Coordinates.** Before the 24 Bedashing place pages were checked by hand, the
headline of this analysis was a duel in Mirdif: Bedashing Mirdif 35 overlapping
49% with Tips & Toes City Centre Mirdif. **It was a geocoding artifact.** With
the real coordinate (1.4 km away) the overlap drops to 19%. The real overlap was
hiding at **Al Barsha**, which geocoding had recorded as 0%. Six recommendations
changed.

**Provenance.** The competitor and demand densities were originally computed at
the *geocoded* coordinates and never recomputed once the coordinates were
verified — so half the model described the new positions and half described the
old ones. Bedashing Al Taif Mall was reading 0 retail POIs within 2 km because
its demand was measured 34 km away; it actually has 244. Recomputing both
signals at the verified coordinates, from a single re-extraction, moved a further
six recommendations.

Neither was modelling work. **A corrected input is worthless until every derived
quantity is recomputed from it, and the failure is silent** — nothing errors, the
numbers simply describe the wrong place.

### The duels: which of the two is redundant

When two group sites cannibalise each other, the question is not "do we close
one?" but **"which one?"**. And because overlap is measured per site rather than
per pair, the damage is **asymmetric** — you can see exactly who loses territory.

| Loses the most | Cedes | Against | Which cedes back |
|---|---|---|---|
| **Tips & Toes Khaleej Al Arabi** (health p36) | **81%** | Bedashing Khaleej Al Arabi (p96), 1.8 km | 51% |
| **Tips & Toes Al Barsha** (p48) | **66%** | Bedashing Al Barsha (p75), 1.2 km | 57% |
| **Tips & Toes Nation Towers** (p31) | 63% | Bedashing Khaleej Al Arabi (p96), 2.8 km | 43% |
| **Tips & Toes Meadows Mall** (p50) | 43% | Tips & Toes Dubai Marina Mall (p35), 2.0 km | 8% |
| **Tips & Toes Reem Mall** (p14) | 34% | Bedashing Delma (p65), 2.8 km | 10% |

**Bedashing wins every cross-brand duel.** Khaleej Al Arabi is the clearest case
in the network: the Tips & Toes site loses four fifths of its catchment to a
Bedashing branch sitting at health percentile 96, 1.8 km away. With geocoded
coordinates that pair was masked as an artifact; with verified coordinates it is
finding number one.

That is the headline of the case: **Omorfia's right-sizing problem is not inside
Bedashing, it is in the overlap Tips & Toes has with Bedashing and with itself.**
Of the 17 SHRINK recommendations in the women's segment, **15 are Tips & Toes**.

### Where to grow

192 cells of roughly 2 km across the Dubai, Sharjah, Ajman and Abu Dhabi
metropolitan areas: **21 GROW, 54 WATCH, 117 SKIP**, and **152 cells with
commercial activity that no group site reaches within a 6-minute drive**.

| Zone | Retail POIs | Competitors | Nearest group site |
|---|---|---|---|
| Al Shindagha, Dubai | 798 | 7 | 5.1 km |
| Khalid Port, Sharjah | 350 | 18 | 5.9 km |
| Port Saeed, Dubai | 272 | 19 | 3.9 km |
| Al Markaziyah West, Abu Dhabi | 217 | 10 | 3.3 km |
| Zabeel, Dubai | 183 | 9 | 4.4 km |
| Al Jerf, Ajman | 169 | 20 | 10.5 km |

#### The residential test, and why it exists

The first version of this layer had no such test, and its GROW list included
**Musaffah, the Sharjah Industrial Area, Al Qusais Industrial Area and Dubai
International Airport**. That is not a list of places to open a salon; it is a
list of places with a lot of OpenStreetMap points.

The flaw was invisible while the output was grid ids. "Cell 18_25" reads as a
plausible recommendation; "Musaffah Industrial Area" does not. **Naming the
output is what exposed the defect**, which is itself an argument for naming
outputs rather than shipping coordinates.

A beauty salon serves residents, not warehouses. So a GROW zone now has to show
a residential catchment: at least one `landuse=residential` parcel within 2 km,
and more residential than industrial. Musaffah has 0 residential against 26
industrial and is correctly disqualified; Al Shindagha has 7 against 0 and
survives. **21 zones were rejected on this test**, and they drop to WATCH rather
than SKIP, because their demand is real — it is the resident customer base that
is unproven.

The test inherits OSM's own gaps: Al Majaz in Sharjah is a dense residential
corniche district with 964 retail POIs, and it is rejected because OSM maps only
2 residential parcels there. That is a mapping artifact, not a market fact, and
it is the first thing to check with local knowledge.

---

## 8. Where NOT to trust this

1. **A rating is not revenue.** A neighbourhood salon with a twenty-year client
   base can have 150 reviews and the best margin in the estate. The whole health
   axis is a proxy and must be crossed against the POS before anything closes.
2. **The health proxy punishes new branches**, because review count accumulates
   with age. Noya Plaza above is the worked example. Until opening date is a
   feature, treat a low-health recommendation on a young site as unreliable.
3. **Review volume favours the urban and the old.** Khalifa City A has 2,453
   reviews and health percentile 100. Part of that is quality and part is simply
   age and footfall.
4. **Tips & Toes and Jazz coordinates are still geocoded.** All 24 Bedashing
   coordinates were verified one by one; the other 50 were not. Since verifying
   changed six Bedashing recommendations, assume verifying Tips & Toes will
   change some of theirs. 16 pairs remain flagged as artifacts and excluded.
5. **OpenStreetMap coverage in the UAE is uneven**, and it shows. Bedashing Al
   Ain returns just 1 retail POI within 2 km, which says more about mapping
   density in Al Markaniyah than about the neighbourhood. Do not compare demand
   across emirates without allowing for it.
6. **13 sites use a fallback circle instead of an isochrone**, because OSRM
   cannot route from their coordinate (island, unmapped road network, airport).
   Flagged per site in `catchment_source`.
7. **A mall site breaks the catchment model.** It draws on mall footfall, not on
   the neighbourhood. There is an `in_mall` flag the model does not yet use.
8. **11 Tips & Toes ratings are missing** in peripheral markets. None overlaps a
   Bedashing branch, so no recommendation about the case brand moves, but the
   Tips & Toes ranking is incomplete.
9. **The thresholds are relative.** The model says who is worst inside this
   network, not who loses money. With P&L data the classification should move
   from percentiles to absolute thresholds.
