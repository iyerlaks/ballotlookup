# Methodology

How the data in this tool is gathered, written, and checked. The short
version: candidate lists come from official state records; issue positions
are AI-researched under strict neutrality rules, every entry links to its
source with a date so you can check it yourself, and a sample of every
research batch is independently re-verified by a human-supervised audit.

## Candidate data

- **Source:** the Pennsylvania Department of State's Official Candidate
  Listing (pavoterservices.pa.gov), the same certified list counties build
  ballots from. Every approved candidate appears; no one is added or removed
  editorially. See `scripts/refresh_data.md` for the capture procedure.
- **Filtering:** Democratic and Republican primary losers are dropped
  (they are not on the November ballot). All other approved candidates are
  kept, including minor-party and independent filers after the August 3
  filing deadline.
- **District lookup:** the U.S. Census Bureau's public geocoder resolves a
  street address to its congressional, state-senate, and state-house
  districts. The address is sent only to the Census Bureau and is never
  stored or logged by this site.

## Issue positions: how they are researched

Positions are researched with AI assistance (Claude research agents using
web search), one agent per race, under a fixed prompt that enforces the
neutrality rules below. This is stated plainly because "who wrote this" is
a fair question for a voter tool. What makes the entries trustworthy is not
who typed them but that every claim is checkable:

1. **Every entry carries a source URL and a date.** The source is the
   candidate's own campaign site, official records (votes, sponsored bills,
   official statements), or a reputable news outlet. Readers can open any
   source and compare it to the summary.
2. **Only what the candidate has said or done.** Positions are never
   inferred from party, endorsements, or donors. If nothing verifiable
   exists, the table says "No public position on file": that means
   unverified, not that the candidate has no view. Sparse entries for
   low-profile candidates are correct output, not a gap to fill.
3. **Neutral wording.** Summaries paraphrase the candidate's own words with
   no loaded adjectives and no evaluation. The working test: would the
   candidate's staff accept the sentence as accurate, and their opponent's
   staff accept it as fair?
4. **Equal effort per race.** Every candidate in a covered race gets the
   same research effort. Some candidates simply have thinner public records.
5. **Fixed issue set.** Seven issues (economy, taxes, abortion, education,
   healthcare, energy, guns) apply identically to every race.

The full rules, including the format for contributing new entries, are in
`data/ISSUES_GUIDE.md`.

## How the research is checked

- **Sampled audits:** roughly 10% of new entries in every research batch and
  every data refresh are independently re-verified against their cited
  sources. Entries that fail the audit are rewritten to the candidate's
  verbatim statements or dropped.
- **Human review of judgment calls:** borderline entries (endorsement-based
  positions, adjacent-topic content, single-source claims from opinion
  pieces) are flagged and decided by the maintainer, and the precedents are
  recorded so they are applied consistently.
- **Corrections inbox:** errors reported by readers, candidates, or campaign
  staff are checked against the cited source and fixed promptly. Candidates
  who want a position added or updated can email a link to a public
  statement; it is summarized under the same rules as everyone else's.

To be precise about what is NOT claimed: entries are not individually
hand-verified by a human. The corpus is AI-researched and source-linked on
every line, with sampled human-reviewed audits per refresh. That is the
honest description, and the source links exist so no one has to take the
summaries on faith.

## Multi-statement coverage

For statewide and congressional races, an issue may carry up to three dated
statements, newest first. The comparison table and print handout always show
the newest statement, by mechanical rule, never by hand-picking. The number
of statements reflects available coverage, not endorsement. State House and
Senate races stay single-statement so sparse coverage stays honestly sparse.

## Ballotpedia links

Where a candidate card links to a Ballotpedia profile, the link was verified
strictly: the linked page must name the candidate's exact district. Candidates
without a verified page get an identical search-link fallback, so every
candidate carries the same chip either way. The tool links out and never
curates roll-call votes itself, because choosing which votes to display is
editorializing.

## Ordering and presentation

Candidates are listed by ballot-qualified party, ordered Democratic,
Republican, then others alphabetically. The ordering is disclosed and
identical for every race. No endorsements, ratings, or characterizations
appear anywhere in the tool.

## Refresh cadence

Election data goes stale on a schedule set by election law: after the
third-party filing deadline, after ballot-position lotteries and nomination
objections, and before mail ballots drop. The maintenance calendar in
README.md tracks these. After election day the tool is frozen or taken down;
a stale election tool damages trust.
