# Adding candidate issue positions — volunteer guide

Issue positions live in `data/issues.json` and are merged into the site by
`python scripts/build_data.py`. Statewide races ship with positions; any
volunteer can extend coverage race by race. **The credibility of the whole tool
rests on these entries being neutral and sourced — read the rules first.**

## The rules (non-negotiable)

1. **Only what the candidate has said or done.** Summarize their own campaign
   site, their own statements, their own votes/actions. Never infer a position
   from party, endorsements, or donors.
2. **Neutral wording.** No loaded adjectives ("extreme", "commonsense",
   "so-called"). A reader should not be able to tell which candidate the
   writer prefers. Test: would the candidate's own staff accept the sentence
   as accurate? Would their opponent's staff accept it as fair?
3. **Every entry needs a source URL and date.** Prefer the candidate's campaign
   site, then official records, then reputable outlets (AP, Spotlight PA,
   Inquirer, WHYY, PennLive, TribLive).
4. **If you can't verify, leave it out.** The site renders missing entries as
   "No public position on file" — that is the honest state, not a gap to fill.
5. **Both/all candidates in a race, same effort.** Never publish positions for
   one candidate in a race and skip their opponent without trying equally hard.
   Sparse-record candidates (common in State House races) simply get fewer
   verified entries — that's fine, it's symmetric effort that matters.
6. 1–2 sentences per issue, roughly equal length across candidates in a race.
7. **`short` is a condensation, not a new claim.** The printed handout uses the
   `short` field (falling back to the full summary if absent). It must contain
   nothing that isn't in the summary, keep the candidate's own verbs
   ("supports", "opposes", "proposes"), and stay roughly equal length across
   candidates in a race. All the neutrality rules above apply at 10 words too —
   compression is where slant sneaks in, so reread it against rule 2.

## Format

Find the candidate's id: it's the `candidateId` column in
`data/candidates_raw.json` (search by last name).

```json
{
  "issues": [ {"key": "economy", "label": "Economy & cost of living"}, ... ],
  "positions": {
    "23048": {
      "website": "https://joshshapiro.org/",
      "positions": {
        "economy": {
          "summary": "1-2 neutral sentences of what the candidate says/has done.",
          "short": "Optional ~10-word version for the printed handout.",
          "source": "https://...",
          "date": "2026-02"
        }
      }
    }
  }
}
```

After editing: `python scripts/build_data.py`, spot-check the race in a
browser, redeploy `site/`.

## Multiple statements per issue (statewide + congressional only)

Since 2026-08, a position value may be a LIST of up to 3 statement objects
instead of a single object, sorted newest-first by date:

```json
"economy": [
  {"summary": "...", "short": "...", "source": "https://...", "date": "2026-07"},
  {"summary": "...", "short": "...", "source": "https://...", "date": "2026-02"}
]
```

Rules: each entry is a DISTINCT statement, vote, or proposal from a separate
occasion (not a second source for the same statement); every entry is
individually verified under all the rules above; the NEWEST entry is primary
by mechanical rule — the comparison table and print handout show only
`entries[0].short`, the evidence panel shows all of them. Scope is statewide
and congressional races only; State House/Senate stay single-statement so
sparse coverage stays honestly sparse.

## Issue keys

| key | label |
|-----|-------|
| economy | Economy & cost of living |
| taxes | Taxes & state budget |
| abortion | Abortion & reproductive health |
| education | Education & schools |
| healthcare | Healthcare |
| energy | Energy & environment |
| guns | Guns & public safety |

Keep this set fixed across all races so comparisons stay consistent. Adding an
issue is a project-level decision, not a per-race one.
