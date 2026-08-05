# PA Ballot Lookup

A free, nonpartisan, static web tool: enter a Pennsylvania street address, see every
candidate on your **November 3, 2026 general election** ballot, compare their stated
positions side by side, and print a one-page canvassing handout.

**Live at [ballotlookup.netlify.app](https://ballotlookup.netlify.app/).**

- **How the data is gathered and checked:** [METHODOLOGY.md](METHODOLOGY.md)
- **Reporting errors / adding coverage:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Building this for another state:** [REPLICATION.md](REPLICATION.md)
- **License:** [MIT](LICENSE)

Live races covered: Governor, Lieutenant Governor, all 17 U.S. House districts,
all 25 State Senate districts on the 2026 cycle (even-numbered), all 203 State House
districts. Ballot questions, special elections, and local/county offices are out of
scope (none of the county row offices are on the 2026 ballot — those run in odd years).

## How it works

1. **Address → districts.** The browser calls the U.S. Census Bureau Geocoder
   (free, no API key, JSONP because the endpoint sends no CORS headers) and reads the
   congressional, state-senate, and state-house district layers. The address goes
   only to the Census Bureau; nothing is stored or logged by the site.
2. **Districts → candidates.** `site/data.js` holds every certified candidate keyed
   by district (`CD-06`, `SD-42`, `HD-167`, `STATEWIDE-GOV`, `STATEWIDE-LTGOV`),
   built from the PA Department of State's Official Candidate Listing.
3. Odd-numbered senate districts get an explainer (4-year terms, next vote 2028)
   instead of an empty race.

Each candidate gets identical treatment: name, party, home county, and links —
campaign website (where on file), Ballotpedia search, a neutral web search, and
their PA campaign-finance reports.

### Side-by-side issue comparison

Races where positions are on file get a "Compare positions" table: 7 fixed issues
(economy, taxes, abortion, education, healthcare, energy, guns) × candidates, each
cell a neutral 1–2 sentence summary of the candidate's own public statements with a
source link and date. Cells without a verified statement say "No public position on
file" — never inferred from party. Positions live in `data/issues.json`; statewide
races ship populated, and volunteers extend coverage race by race using
`data/ISSUES_GUIDE.md` (the neutrality rules live there — read them first).

### Canvassing handout

After a lookup, "Print canvassing handout" produces a single letter page: the
voter's races and candidates in a two-column layout, a dashed fold line, and a
bottom panel with the official 2026 deadlines (register by Oct 19, mail-ballot
applications by Oct 27 5 PM, ballots received by 8 PM Nov 3, polls 7 AM–8 PM —
verified against the PA DoS election calendar) plus vote.pa.gov pointers.
Canvassers in one precinct share districts, so one printout serves a walk list.

## Repo layout

```
data/candidates_raw.json     raw extract from PA DoS (do not edit)
data/issues.json             researched issue positions (see METHODOLOGY.md)
data/ISSUES_GUIDE.md         rules + format for adding positions
data/research/               per-district research files as merged
scripts/build_data.py        raw extract + positions -> site/data.js
scripts/merge_positions.py   validate + merge research files into issues.json
scripts/validate_research.py read-only validator for research files
scripts/ballotpedia_links.py Ballotpedia link verification batch tool
scripts/refresh_data.md      how to re-capture the raw extract
site/index.html              the whole app (no build step, no dependencies)
site/data.js                 generated candidate database
```

## Deploying

The `site/` folder is the entire site. Drag it onto Netlify Drop, or point
GitHub Pages / Cloudflare Pages at it. No server, no build, no keys.

## Maintenance calendar (important)

- **After Aug 3, 2026** (third-party/independent filing deadline): refresh the data
  (see `scripts/refresh_data.md`). Minor-party candidates are absent until then —
  the site says so on every result.
- **Late Aug 2026**: refresh again after ballot-position lotteries and any
  successful nomination objections (candidates can be struck from the ballot).
- **Early Oct 2026**: final refresh before mail ballots drop.
- **Nov 4, 2026**: take the tool down or freeze it with a banner; stale election
  tools damage trust.

## Nonpartisan posture

- Candidates are listed by ballot-qualified party, ordered Democratic, Republican,
  then others alphabetically — the ordering is disclosed and identical for every race.
- No endorsements, ratings, summaries, or issue characterizations anywhere.
- All outbound candidate links are official records or neutral search pages.
- Data source and last-updated date are printed in the footer of every page.
