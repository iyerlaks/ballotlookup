# Replicating this tool for another state

This repo is the Pennsylvania instance. Most of it generalizes; the parts
that don't are listed here, learned the hard way so you don't have to.

## What already generalizes (no rework)

- **District lookup:** the U.S. Census Bureau geocoder returns congressional,
  state-senate, and state-house districts for every US state, from the same
  API (layers "119th Congressional Districts", "State Legislative Districts -
  Upper" / "Lower"). Note it has no CORS headers, so the site calls it via
  JSONP; see `site/index.html`.
- **The site itself:** the HTML, comparison UI, evidence panel, and print
  handout are state-agnostic.
- **The pipeline:** `scripts/merge_positions.py`, `scripts/build_data.py`,
  and `scripts/validate_research.py` work on any state's data once the raw
  candidate extract is in the same shape.
- **The methodology:** the neutrality rules in `data/ISSUES_GUIDE.md` and
  METHODOLOGY.md are not PA-specific. They are the load-bearing part; a
  single slanted summary damages the whole tool more than a missing one.

## What needs a per-state adapter

1. **Candidate list source.** Every state's elections site publishes its
   certified candidate list differently (CSV, PDF, HTML app). This is the
   bulk of the per-state work. PA's is a DataTables page behind bot
   protection; `scripts/refresh_data.md` documents the browser-capture
   pattern, which adapts to most JS-rendered sites.
2. **Election calendar.** Registration and mail-ballot deadlines for the
   print handout. Verify from the state's official source, never from
   memory or a national aggregator.
3. **Senate cycle parity.** PA elects even-numbered senate districts in
   2026; other states differ. Encode it as data, not code assumptions.
4. **Ballot-structure traps** that break naive cloning of the PA logic:
   - **Multi-member house districts** (AZ, WA, NH, VT, ND, SD, MD, NJ...):
     a race can elect two or more candidates. UI copy "vote for one" must
     become "vote for up to N", and race cards need N-winner awareness.
   - **Top-two primaries** (CA, WA): the general is not D-vs-R. The
     primary-loser filter in `scripts/build_data.py` does not apply as-is;
     the general-election field is the top two primary finishers regardless
     of party, so the filter must key on advancement, not on major-party
     primary wins.
   - **Fusion voting** (NY, CT): one candidate appears on multiple party
     lines. Dedupe by person, list all their lines.
   - **Odd-year states** (VA, NJ, many municipal cycles): their big races
     may not be in the year you're building for.

## Deployment advice

Run one site per state (its own subdomain or Netlify site). Do not build a
multi-state single app: it couples every state's refresh cadence and doubles
the blast radius of every mistake. Copy the repo per state; cherry-pick
shared improvements.

## Before you launch a state, honestly answer

1. **Who owns the refresh cadence and the corrections inbox?** This is the
   hard requirement. Election data goes stale on a legal calendar (filing
   deadlines, ballot lotteries, objection rulings, mail-ballot drops), and a
   stale ballot tool is worse than none: it damages trust in every instance
   of the tool. If no named person or org owns the calendar, don't launch.
2. Is the state's certified candidate list machine-readable, or at least
   capturable with the browser pattern?
3. Which of the ballot-structure traps above apply to your state? None of
   them is disqualifying; they are documented here precisely so you can
   plan for them instead of discovering them mid-build. A top-two state
   like California mostly means adjusting the candidate filter and the
   race-card copy; budget for it, don't be scared off by it.
4. Are there competitive races people will actually search for?

A note for odd-year states (Virginia, New Jersey, and others): an even-year
build there is smaller, not pointless. Their even-year ballot is federal
races only, which makes a first build a fraction of the work of a full
state, and a good dry run before the odd-year cycle when the statewide and
legislative races arrive. Starting small and proving the refresh cadence on
a dozen races is a legitimate path in.

## Maintenance budget, for planning

The PA instance runs in solo-maintainer mode on roughly this budget: three
data refreshes of about 15 minutes each across the fall, a weekly pass over
the corrections inbox, and a freeze-or-takedown commit after election day.
Research passes to extend issue coverage are batched (10-15 districts at a
time, validated, sampled-audited, committed with counts). If that budget
sounds unsustainable for your situation, launch with candidate listings and
links only; facts plus official links with no position research is still a
coherent, useful product.
