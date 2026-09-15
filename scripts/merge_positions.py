"""Merge researched position JSON into data/issues.json -- all or nothing.

Usage: python scripts/merge_positions.py [--force] <file1.json> [file2.json ...]

Each input file: {"<candidateId>": {"name": "...", "website": "...",
                  "ballotpedia": "...",
                  "positions": {"<issueKey>": entry | [entry, ...]}}}
where entry = {"summary", "short", "source", "date"}.

A position value is a single entry (the norm for State House/Senate) or a
list of up to three (multi-statement expansion for statewide + congressional
races, 2026-08). Lists are stored date-desc; the newest entry is primary by
mechanical rule -- never hand-pick which statement leads.

Every file is validated first with the rules in scripts/research_rules.py
(the same rules validate_research.py applies). If ANY problem is found in
ANY file, nothing is written and the exit code is nonzero: a partial merge
that "reports problems" is how a bad entry reaches voters. Fix the file and
re-run. Refuses to overwrite a candidate already present unless --force is
passed (protects already-reviewed data).

NOT parallel-safe: it rewrites issues.json. Run merges serially.
Set BALLOT_ROOT to merge into another checkout (used by the tests).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_rules import MAX_ENTRIES, check_file, clean_entry, load_known_ids  # noqa: E402

ROOT = Path(os.environ.get("BALLOT_ROOT") or Path(__file__).resolve().parent.parent)


def normalize_position(p):
    """Valid entry-or-list in -> stored shape out. Single object stays an
    object; a list is date-desc and a one-entry list collapses to an object."""
    if not isinstance(p, list):
        return clean_entry(p)
    cleaned = sorted((clean_entry(e) for e in p), key=lambda e: e["date"], reverse=True)
    assert len(cleaned) <= MAX_ENTRIES  # check_file already rejected longer lists
    return cleaned[0] if len(cleaned) == 1 else cleaned


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    if not args:
        sys.exit("usage: merge_positions.py [--force] file1.json ...")

    known_ids = load_known_ids(ROOT)
    issues_path = ROOT / "data" / "issues.json"
    db = json.loads(issues_path.read_text(encoding="utf-8"))
    db.setdefault("positions", {})

    # Pass 1: validate everything. No writes until every file is clean.
    files: list[tuple[str, dict]] = []
    problems: list[str] = []
    for f in args:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            problems.append(f"{f}: unreadable ({e})")
            continue
        problems += check_file(data, known_ids, label=f)
        if not isinstance(data, dict):
            continue
        for cid, entry in data.items():
            cid = str(cid)
            if cid in known_ids and cid in db["positions"] and not force:
                problems.append(f"{f}: {cid} ({entry.get('name')}) already present; use --force to replace")
            if isinstance(entry, dict) and not (entry.get("positions") or entry.get("website") or entry.get("ballotpedia")):
                problems.append(f"{f}: {cid} ({entry.get('name')}) has nothing to merge")
        files.append((f, data))

    if problems:
        print(f"REFUSED: {len(problems)} problem(s); nothing written")
        for p in problems:
            print("  !!", p)
        sys.exit(1)

    # Pass 2: apply.
    added = entries = 0
    for _, data in files:
        for cid, entry in data.items():
            cid = str(cid)
            out = {}
            if entry.get("website"):
                out["website"] = entry["website"]
            if entry.get("ballotpedia"):
                out["ballotpedia"] = entry["ballotpedia"]
            pos = {k: normalize_position(p) for k, p in (entry.get("positions") or {}).items()}
            if pos:
                out["positions"] = pos
            db["positions"][cid] = out
            added += 1
            entries += sum(len(v) if isinstance(v, list) else 1 for v in pos.values())

    issues_path.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"merged {added} candidates ({entries} issue entries) from {len(files)} file(s)")


if __name__ == "__main__":
    main()
