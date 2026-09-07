# Business framing

*This document was written before a single line of code, and it is the one that
orders everything else.*

---

## 1. The decision-maker

**The Head of Operations of Omorfia Group**: the person who approves lease
renewals and terminations across the group's salon portfolio.

Not "leadership", not "the business". A specific person, with a P&L, who signs
their name to the decision to close a site and then has to defend it in front of
a committee. The whole product design falls into place the moment you accept
that this person is the user.

## 2. The decision they have to make

For each branch, at lease renewal:

| Decision | What it means in practice |
|---|---|
| **PROTECT** | Renew and invest: refit, headcount, local marketing |
| **HOLD** | Renew on the same terms, look at it again next quarter |
| **SHRINK** | Renegotiate the footprint down, do not renew, or relocate |

And, in parallel, the expansion decision:

| Decision | What it means |
|---|---|
| **GROW** | Candidate zone for an opening, move to site search |
| **WATCH** | Interesting but with a caveat; monitor |
| **SKIP** | Discard for now |

## 3. The context that changes the analysis

Bedashing does not operate alone. It belongs to **Omorfia Group**, which also
owns **Tips & Toes**, **Jazz Lounge Spa** and Creative Beauty Source, and which
was formed by merging chains that used to compete with each other.

The brief asks *"where are we overlapping with ourselves"*. That **"we" is the
group**, not the brand. Analysing Bedashing against Bedashing answers the
literal question and fails the real one, which is the classic residue of a
roll-up: two sites with the same owner, under different brands, splitting the
same customer in the same neighbourhood.

Evidence that they operate as a single company: **Bedashing and Tips & Toes
share an exact registered address** (3rd Floor, Al Faris Building, Arjan,
Barsha South, Dubai).

That is why the analysis perimeter is **74 sites across three brands**, not 24
across one. And it is why Jazz is included — so that it can be **excluded with
evidence**: it is a men's spa, it shares a building with Tips & Toes in several
locations, and without a customer-segment distinction that looks like brutal
cannibalisation when it is in fact a deliberate couple-coverage strategy.

## 4. The metric that matters, and the one we have

The metric that moves this decision is **margin per square metre of the
network**. It is not public and we do not have it.

We work with the three factors that determine it and that *are* observable:

| Factor | Observable signal | Proxy quality |
|---|---|---|
| How well the site executes | Rating × review volume | Weak but directional |
| How good its market is | Retail density minus competition, inside its catchment | Reasonable |
| How much it eats itself | % of catchment shared with a same-segment group site | Strong — it is geometry |

**The first is the weakest and it needs saying out loud.** A neighbourhood salon
with a twenty-year client base can have 150 reviews and be the best margin in
the estate. No closure recommendation should be executed without crossing it
against actual takings.

## 5. How the system supports the decision

1. **A map** where the director sees the estate, the real drive-time catchments,
   and red lines between the sites that eat each other.
2. **A label per site** with a reason written in business language, generated
   from the signals rather than by hand.
3. **The score decomposition**: how much each signal contributed to each
   decision, so it can be argued component by component.
4. **A confidence measure**: which recommendations survive a change of weights
   and which do not. The fragile ones are flagged so nobody acts on them without
   more data.
5. **The weights as controls**, not as hidden constants: the most arguable
   assumption in the model is exposed in the interface.
6. **A natural-language analyst** that queries the data through tools and cites
   what it used, for the questions that do not fit in a filter.

## 6. Scope, and what is deliberately left out

**In scope:** the 24 Bedashing branches as the object of recommendation, and the
40 Tips & Toes branches as internal competitive context, across the five
emirates where the brand operates.

**Out of scope, with a reason:**

- **Jazz Lounge Spa** gets no recommendation: different customer segment.
- **11 Tips & Toes branches** in peripheral markets go unscored for want of a
  rating. None of them overlaps a Bedashing branch, so none of the case's
  recommendations moves.
- **Supervised models**: there are no ground-truth labels. See the README.
- **Seasonality, mall footfall and neighbourhood income**: outside this
  iteration, documented as known limits.

## 7. The test the product has to pass

A reviewer in a hurry, in ten minutes, should be able to say:

1. I understand who this is for and what it decides.
2. I understand why this site is SHRINK and that one is PROTECT.
3. I know which data it used and what it simplified, because it says so.
4. He knows where his own work is weak.
5. I could run this for the group's other brands by swapping the CSV.
