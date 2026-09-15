"""Validate research JSON files WITHOUT merging into data/issues.json.

Usage: python scripts/validate_research.py <file1.json> [file2.json ...]

Read-only twin of merge_positions.py: both apply the rules in
scripts/research_rules.py (candidate ids against data/candidates_raw.json,
issue keys against the fixed taxonomy, summary + source + date required,
dates as YYYY-MM or YYYY-MM-DD, absolute http(s) URLs only, at most three
statements per issue). Safe to run from many parallel sessions.

Exits nonzero if any problem is found. Set BALLOT_ROOT to validate against
another checkout's candidate list (used by the tests).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_rules import check_file, count_entries, load_known_ids  # noqa: E402

ROOT = Path(os.environ.get("BALLOT_ROOT") or Path(__file__).resolve().parent.parent)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: validate_research.py file1.json ...")

    known_ids = load_known_ids(ROOT)
    entries = candidates = 0
    problems: list[str] = []
    for f in args:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            problems.append(f"{f}: unreadable ({e})")
            continue
        problems += check_file(data, known_ids, label=f)
        if isinstance(data, dict):
            c, n = count_entries(data)
            candidates += c
            entries += n

    print(f"validated {candidates} candidates ({entries} issue entries) in {len(args)} file(s)")
    for p in problems:
        print("  !!", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
