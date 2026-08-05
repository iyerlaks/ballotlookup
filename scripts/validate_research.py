"""Validate a research JSON file WITHOUT merging into data/issues.json.

Usage: python scripts/validate_research.py <file1.json> [file2.json ...]

Read-only twin of merge_positions.py's validation: checks candidate ids
against data/candidates_raw.json, issue keys against the fixed taxonomy,
and required summary/source fields. A position value may be a single
object or a LIST of up to 3 {summary, short, source, date} entries
(multi-statement expansion for statewide + congressional races, 2026-08);
list entries are checked individually and lists longer than 3 are flagged.
An optional per-candidate "ballotpedia" URL field is accepted. Safe to run
from many parallel sessions (merge_positions.py is not — it rewrites
issues.json). Exits nonzero if any problem is found.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALID_KEYS = {"economy", "taxes", "abortion", "education", "healthcare", "energy", "guns"}
MAX_ENTRIES = 3


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: validate_research.py file1.json ...")

    raw = json.loads((ROOT / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    known_ids = {str(r[6]): r[0] for r in raw["rows"]}

    entries = candidates = 0
    problems: list[str] = []
    for f in args:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            problems.append(f"{f}: unreadable ({e})")
            continue
        for cid, entry in data.items():
            cid = str(cid)
            if cid not in known_ids:
                problems.append(f"{f}: unknown candidateId {cid} ({entry.get('name')})")
                continue
            candidates += 1
            for key, p in (entry.get("positions") or {}).items():
                if key not in VALID_KEYS:
                    problems.append(f"{f}: {cid} bad issue key {key!r}")
                    continue
                plist = p if isinstance(p, list) else [p]
                if len(plist) > MAX_ENTRIES:
                    problems.append(f"{f}: {cid}/{key} has {len(plist)} entries (max {MAX_ENTRIES})")
                for i, e in enumerate(plist):
                    if not isinstance(e, dict) or not e.get("summary") or not e.get("source"):
                        where = f"[{i}]" if isinstance(p, list) else ""
                        problems.append(f"{f}: {cid}/{key}{where} missing summary/source")
                        continue
                    entries += 1

    print(f"validated {candidates} candidates ({entries} issue entries) in {len(args)} file(s)")
    for p in problems:
        print("  !!", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
