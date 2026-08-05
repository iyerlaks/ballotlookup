"""Merge researched position JSON into data/issues.json.

Usage: python scripts/merge_positions.py <file1.json> [file2.json ...]

Each input file: {"<candidateId>": {"name": "...", "website": "...",
                  "positions": {"<issueKey>": {"summary","short","source","date"}}}}

A position value may be either a single {summary, short, source, date} object
(the original schema, still the norm for State House/Senate) or a LIST of such
entries (multi-statement expansion for statewide + congressional races,
2026-08). Lists are sorted date-desc and capped at 3; the newest entry is
primary by mechanical rule — never hand-pick which statement leads. An
optional per-candidate "ballotpedia" field (verified Ballotpedia page URL) is
also accepted.

Validates candidate ids against data/candidates_raw.json, issue keys against
the fixed taxonomy, and required fields. Refuses to overwrite an existing
candidate entry unless --force is passed (protects already-reviewed data).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALID_KEYS = {"economy", "taxes", "abortion", "education", "healthcare", "energy", "guns"}
MAX_ENTRIES = 3


def clean_entry(p: dict) -> dict | None:
    """Validate one statement object; None if unusable."""
    if not isinstance(p, dict) or not p.get("summary") or not p.get("source"):
        return None
    return {k: p[k] for k in ("summary", "short", "source", "date") if p.get(k)}


def clean_position(p) -> tuple[object | None, int, str | None]:
    """Accept object or list. Return (value, n_entries, problem_or_None).

    Single object in -> single object out (back-compat). List in -> list out,
    date-desc, capped at MAX_ENTRIES; a one-entry list collapses to an object.
    """
    if isinstance(p, list):
        cleaned = [c for c in (clean_entry(e) for e in p) if c]
        dropped = len(p) - len(cleaned)
        if not cleaned:
            return None, 0, "no usable entries in list"
        cleaned.sort(key=lambda e: e.get("date", ""), reverse=True)
        over = len(cleaned) - MAX_ENTRIES
        note = None
        if dropped:
            note = f"{dropped} list entr{'y' if dropped == 1 else 'ies'} missing summary/source — dropped"
        if over > 0:
            cleaned = cleaned[:MAX_ENTRIES]
            note = (note + "; " if note else "") + f"capped at {MAX_ENTRIES} (dropped {over} oldest)"
        if len(cleaned) == 1:
            return cleaned[0], 1, note
        return cleaned, len(cleaned), note
    c = clean_entry(p)
    if not c:
        return None, 0, "missing summary/source — dropped"
    return c, 1, None


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    if not args:
        sys.exit("usage: merge_positions.py [--force] file1.json ...")

    raw = json.loads((ROOT / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    known_ids = {str(r[6]): r[0] for r in raw["rows"]}

    issues_path = ROOT / "data" / "issues.json"
    db = json.loads(issues_path.read_text(encoding="utf-8"))

    added = skipped = entries = 0
    problems: list[str] = []
    for f in args:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        for cid, entry in data.items():
            cid = str(cid)
            if cid not in known_ids:
                problems.append(f"{f}: unknown candidateId {cid} ({entry.get('name')})")
                continue
            if cid in db["positions"] and not force:
                problems.append(f"{f}: {cid} ({entry.get('name')}) already present; use --force")
                skipped += 1
                continue
            clean_pos = {}
            for key, p in (entry.get("positions") or {}).items():
                if key not in VALID_KEYS:
                    problems.append(f"{f}: {cid} bad issue key {key!r} — dropped")
                    continue
                value, n, note = clean_position(p)
                if note:
                    problems.append(f"{f}: {cid}/{key} {note}")
                if value is None:
                    continue
                clean_pos[key] = value
                entries += n - 1  # per-candidate count added below via len()
            out = {}
            if entry.get("website"):
                out["website"] = entry["website"]
            if entry.get("ballotpedia"):
                out["ballotpedia"] = entry["ballotpedia"]
            if clean_pos:
                out["positions"] = clean_pos
            if not out:
                problems.append(f"{f}: {cid} ({entry.get('name')}) had nothing usable")
                continue
            db["positions"][cid] = out
            added += 1
            entries += len(clean_pos)

    issues_path.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"merged {added} candidates ({entries} issue entries), skipped {skipped}")
    for p in problems:
        print("  !!", p)


if __name__ == "__main__":
    main()
