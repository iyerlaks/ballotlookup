"""Merge verified Ballotpedia page URLs into data/issues.json.

Usage: python scripts/merge_ballotpedia.py <file1.json> [file2.json ...]

Each input file: {"<candidateId>": "https://ballotpedia.org/Page_Name", ...}
(null / empty string = verified that NO page exists; recorded as absent.)

Unlike merge_positions.py this only sets the per-candidate "ballotpedia"
field — existing website/positions data is never touched, and an entry is
created for candidates that have no positions yet. Overwriting an existing
ballotpedia value requires --force. NOT parallel-safe (rewrites issues.json);
run serially.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    if not args:
        sys.exit("usage: merge_ballotpedia.py [--force] file1.json ...")

    raw = json.loads((ROOT / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    known_ids = {str(r[6]): r[0] for r in raw["rows"]}

    issues_path = ROOT / "data" / "issues.json"
    db = json.loads(issues_path.read_text(encoding="utf-8"))

    set_n = skipped = none_n = 0
    problems: list[str] = []
    for f in args:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        for cid, url in data.items():
            cid = str(cid)
            if cid not in known_ids:
                problems.append(f"{f}: unknown candidateId {cid}")
                continue
            if not url:
                none_n += 1
                continue
            if not url.startswith("https://ballotpedia.org/"):
                problems.append(f"{f}: {cid} not a ballotpedia.org URL: {url}")
                continue
            entry = db["positions"].setdefault(cid, {})
            if entry.get("ballotpedia") and entry["ballotpedia"] != url and not force:
                problems.append(f"{f}: {cid} already has {entry['ballotpedia']}; use --force")
                skipped += 1
                continue
            entry["ballotpedia"] = url
            set_n += 1

    issues_path.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"set {set_n} ballotpedia links ({none_n} verified-absent, {skipped} skipped)")
    for p in problems:
        print("  !!", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
