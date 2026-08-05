# Contributing

## Corrections (fastest path)

Spot an error: a wrong candidate, a mischaracterized position, a dead link?
Email **ballotlookup@gmail.com** with the race, the candidate, and what's
wrong. Corrections are checked against the cited source and fixed promptly.

Candidates and campaign staff: to add or update a position, email a link to
a public statement. It will be summarized under the same rules as everyone
else's (see METHODOLOGY.md), never pasted verbatim from talking points.

## Extending issue coverage

State House and Senate races are covered race by race. To research a race:

1. Read `data/ISSUES_GUIDE.md` first. The neutrality rules there are
   non-negotiable; a slanted entry hurts the tool more than a missing one.
2. Write your entries as a JSON file in the `data/research/` format
   (`sd<NN>.json` / `hd<NNN>.json`, keyed by candidateId from
   `data/candidates_raw.json`).
3. Validate: `python scripts/validate_research.py data/research/<file>.json`
4. Open a pull request with the district covered, the candidate count, the
   entry count, and which sources you checked.

Every entry needs a real source URL and a date. If you can't verify a
position, leave it out; "No public position on file" is the honest state.

## Code changes

The site is a single dependency-free HTML file plus a generated `data.js`.
Keep it that way: no build step, no framework, no analytics, no tracking.
Pull requests that add a dependency need a very good reason.

## Replicating for another state

See REPLICATION.md. Forks for other states are welcome and encouraged;
the license is MIT.
