# Demo video script

Target: **6 minutes**. Screen recording of the app, voice-over.

The temptation is to narrate the interface. Do not. The reviewer can see the
interface. Narrate the *decisions* — every screen exists to make one point, and
the point is what gets scored.

Rule for the whole recording: **never say "as you can see"**. Say what it means.

---

## 0:00 – 0:40 · Who this is for

> "This is a decision-support tool for one specific person: the Head of
> Operations at Omorfia Group, the person who signs lease renewals. For each
> branch it answers one question — at renewal, do we invest, hold, or reduce?
>
> Before I show anything, one framing decision, because everything else follows
> from it. The brief asks *where are we overlapping with ourselves*. Bedashing
> doesn't operate alone: it belongs to Omorfia Group, alongside Tips & Toes and
> Jazz Lounge Spa, and the group was formed by merging chains that used to
> compete. So 'ourselves' is the group, not the brand. Analysing Bedashing
> against Bedashing answers the literal question and misses the real one.
>
> That's why this covers 74 sites across three brands, not 24 across one."

**On screen:** the app open on the Map tab, whole-UAE view, all brands visible.

---

## 0:40 – 1:40 · The map, and what the shapes mean

> "Three things on this map.
>
> The dots are branches, coloured by recommendation — green protect, amber hold,
> red shrink. Size is review volume.
>
> The shaded areas are catchments, and they're not circles. The brief asked for
> travel-time logic and it matters here: Abu Dhabi is islands and creeks, so a
> two-kilometre circle treats a motorway and a stretch of sea as the same thing.
> These are six-minute drive-time isochrones from OSRM. That's why the shapes
> are lopsided — they follow the road network.
>
> Six minutes is a decision, not a fact. I tried twelve, and almost every salon
> saturated: everything overlapped everything and the model stopped
> discriminating.
>
> And the red lines are the point of the whole exercise: two sites owned by the
> same company splitting the same customer."

**On screen:** zoom into Abu Dhabi. Show an irregular isochrone. Hover a red
line to show the overlap tooltip.

---

## 1:40 – 2:50 · The finding, and the asymmetry

> "Zoom in on Khaleej Al Arabi. Bedashing and Tips & Toes, 1.8 kilometres apart,
> same customer, same price tier — I checked the price tier, because if one were
> premium and the other budget the whole cannibalisation metric would be
> inflated. Matched manicure basket: 342 dirhams against 310. Same tier. The
> premise holds.
>
> Now the part I think matters most. Overlap here is computed per site, not per
> pair, because the damage is asymmetric. The Tips & Toes site loses
> **eighty-one percent** of its catchment to Bedashing. Bedashing loses
> fifty-one percent back. Same pair of shops, and the answer is completely
> different depending on which one you ask about.
>
> That's what makes it actionable. The business question is never 'do these two
> overlap' — it's 'which of the two is redundant'. And here it's not close:
> Bedashing sits at health percentile 96, Tips & Toes at 37."

**On screen:** Branch record tab → Bedashing Khaleej Al Arabi, then Tips & Toes
Khaleej Al Arabi. Show the two cannibalisation figures side by side.

---

## 2:50 – 3:40 · How a recommendation is built, and how it can be argued with

> "Every recommendation decomposes. Health, market attractiveness,
> cannibalisation — you can see how much each one contributed, so the decision
> can be argued component by component rather than accepted whole.
>
> The weights are in the sidebar, not buried in the code. They're the most
> arguable assumption in the model, so they're the thing the user can touch.
> Move them and the whole network re-scores live.
>
> There's no trained model here, and that's deliberate. There are no ground-truth
> labels — no history of closures marked right or wrong — so a supervised
> classifier would be trained on labels derived from a rule. It would learn this
> same heuristic and add opacity. With 53 observations it would also overfit.
>
> But the real reason is a product reason. This person has to defend a closure in
> front of a committee, and 'the model says so' is not an argument."

**On screen:** the score decomposition bar chart, then drag the
cannibalisation-weight slider and let the reviewer watch labels change.

---

## 3:40 – 4:30 · Where to trust it and where not

> "The brief asks where to trust the model and where to be careful, so instead of
> hedging in prose I measured it.
>
> Two thousand simulations, perturbing the weights and re-classifying every time.
> For each branch: what share of the time does it keep its recommendation?
>
> Forty-one of fifty-three are robust. Two are fragile, both in Tips & Toes, and
> they're drawn with a dashed outline so nobody acts on them by accident. Every
> Bedashing recommendation holds up.
>
> Two honest caveats. First, a rating is not revenue. The whole health axis is a
> proxy — a neighbourhood salon with a twenty-year client base can have 150
> reviews and be the best margin in the estate. Nothing here should close without
> crossing it against the POS.
>
> Second, and this one I'd point at specifically: the model flags Noya Plaza for
> shrink, and **it's wrong**. Noya rates 4.7, among the best in the network, on
> 209 reviews — because it opened recently. Review count accumulates with age, so
> the health proxy punishes new sites by construction. I've left that in and
> labelled it rather than quietly patching around it, because that's the failure
> mode a reviewer should know the model has."

**On screen:** the fragile-count metric in the header, then the two dashed
markers on the map.

---

## 4:30 – 5:15 · Where to grow, and the AI layer

> "The second half of the brief is whitespace. Same signals, different unit —
> not per site, per zone. 192 grid cells across four emirates: 21 grow, 54 watch,
> and 152 cells with real commercial activity that no group site reaches within a
> six-minute drive. Top of the list is Al Shindagha in Dubai — 798 retail points,
> seven competitors, nearest site of ours five kilometres away.
>
> And a confession that belongs here. The first version of this layer recommended
> Musaffah, the Sharjah Industrial Area and Dubai International Airport. Places thick with map
> points and with nobody living in them. I only caught it when I replaced the grid
> ids with real neighbourhood names — 'cell 18_25' looks like a recommendation,
> 'Musaffah Industrial Area' looks like a mistake. So a zone now has to prove it
> has residents before it can qualify.
>
> And the AI layer. This is a tool-using agent, not a chatbot over the data. The
> model never sees free text about the business: it picks one of six tools, the
> pipeline runs that tool against the CSVs, and the model writes the answer using
> only what the tool returned. So it can't invent a recommendation — it can only
> narrate one.
>
> Every answer ships with this traceability panel: the tool, its arguments, and
> its raw output. You can see exactly what the model was allowed to know.
>
> It also runs with no API key at all — deterministic router, templated answers,
> clearly labelled as no-model, so nobody is misled about what they're reading."

**On screen:** Opportunity tab, then Analyst tab — ask *"where should we open a
new site?"* and expand the traceability panel.

---

## 5:15 – 6:00 · The thing I'd want you to remember

> "One last thing, and it's the part I'd actually want you to take away, because
> it's the part that changed the answer most.
>
> Twice in this project the data was wrong in a way that produced perfectly
> plausible numbers.
>
> First, the coordinates. The headline used to be a duel in Mirdif — Bedashing
> overlapping 49% with Tips & Toes City Centre Mirdif. It was a geocoding
> artifact: the address had resolved to a neighbourhood centroid. With the real
> coordinate the overlap is 19%, and the real overlap was hiding at Al Barsha,
> which geocoding had recorded as zero.
>
> Second — and this is the one I'd want a reviewer to hear — I fixed the
> coordinates and did not recompute everything downstream. The demand and
> competitor counts were still being measured at the old positions. Al Taif Mall
> was reading zero shops within two kilometres because its demand was being
> counted thirty-four kilometres away. It actually has 244.
>
> Between them, twelve recommendations changed. Neither was modelling. Nothing
> ever errored — the numbers just quietly described the wrong place.
>
> So if there's one thing I took from this: a corrected input is worthless until
> everything derived from it is recomputed, and that failure is silent. Which is
> why the pipeline now rebuilds end to end from one command, and why fifty of the
> seventy-four coordinates are still labelled unverified in the README rather
> than quietly used."

**On screen:** the Method and limits tab, scrolled to the "Where NOT to trust
this" section. Hold on it for the final line.

---

## Recording notes

- **Do a silent dry run first.** Every click you fumble on camera costs
  credibility that the content then has to buy back.
- **One take per section, stitched.** Six clean minutes beats one heroic take.
- Have the app already running and warm. Never record a `pip install`.
- Set the browser zoom so text is readable at 1080p. Reviewers may watch on a
  laptop.
- If you overrun, cut section 4:30–5:15 down to the Analyst tab only. Do not cut
  the last section: the coordinate story is the one that shows judgement rather
  than output.
