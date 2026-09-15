"""Shared validation rules for research files (used by validate_research.py
and merge_positions.py so the two can never disagree).

A research file is {"<candidateId>": {"name", "website"?, "ballotpedia"?,
"positions": {"<issueKey>": entry | [entry, ...]}}} where an entry is
{"summary", "short"?, "source", "date"}.

Rules enforced here:
  - candidateId must exist in data/candidates_raw.json
  - issue keys must be in the fixed seven-issue taxonomy
  - every entry needs a non-empty summary, a source URL and a date
  - date is YYYY-MM or YYYY-MM-DD (the date of the statement or record)
  - source, website and ballotpedia URLs must be absolute http(s) URLs with
    a host and no whitespace (no javascript:, data:, mailto:, bare domains)
  - a list holds at most MAX_ENTRIES entries
"""
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

VALID_KEYS = {"economy", "taxes", "abortion", "education", "healthcare", "energy", "guns"}
MAX_ENTRIES = 3
DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?$")
ENTRY_FIELDS = ("summary", "short", "source", "date")


def load_known_ids(root: Path) -> dict[str, str]:
    raw = json.loads((root / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    return {str(r[6]): r[0] for r in raw["rows"]}


def url_problem(url) -> str | None:
    """None if url is a safe absolute http(s) URL, else a short reason."""
    if not isinstance(url, str) or not url.strip():
        return "empty"
    if url != url.strip() or any(ch.isspace() for ch in url):
        return "contains whitespace"
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return f"scheme must be http/https (got {parts.scheme or 'none'!r})"
    if not parts.netloc or "." not in parts.netloc:
        return "missing host"
    return None


def entry_problems(e) -> list[str]:
    """Problems with one statement object (empty list = valid)."""
    if not isinstance(e, dict):
        return ["entry is not an object"]
    out = []
    if not isinstance(e.get("summary"), str) or not e["summary"].strip():
        out.append("missing summary")
    if "short" in e and e["short"] is not None and not isinstance(e["short"], str):
        out.append("short must be a string")
    up = url_problem(e.get("source"))
    if up:
        out.append(f"bad source URL ({up})")
    d = e.get("date")
    if not isinstance(d, str) or not DATE_RE.match(d) or not _real_date(d):
        out.append(f"date must be a real YYYY-MM or YYYY-MM-DD date (got {d!r})")
    return out


def _real_date(d: str) -> bool:
    """True if a regex-shaped date is also a calendar date (no Feb 30)."""
    try:
        datetime.strptime(d, "%Y-%m-%d" if len(d) == 10 else "%Y-%m")
        return True
    except ValueError:
        return False


def clean_entry(e: dict) -> dict:
    """Keep only the schema fields, in order, dropping empties. Call after
    entry_problems() returned no problems."""
    return {k: e[k] for k in ENTRY_FIELDS if e.get(k)}


def check_file(data, known_ids: dict[str, str], label: str = "") -> list[str]:
    """All problems in one parsed research file. Empty list = clean."""
    pre = f"{label}: " if label else ""
    problems: list[str] = []
    if not isinstance(data, dict):
        return [f"{pre}top level must be an object keyed by candidateId"]
    for cid, entry in data.items():
        cid = str(cid)
        who = entry.get("name") if isinstance(entry, dict) else None
        if cid not in known_ids:
            problems.append(f"{pre}unknown candidateId {cid} ({who})")
            continue
        if not isinstance(entry, dict):
            problems.append(f"{pre}{cid} entry is not an object")
            continue
        for f in ("website", "ballotpedia"):
            if entry.get(f):
                up = url_problem(entry[f])
                if up:
                    problems.append(f"{pre}{cid} bad {f} URL ({up})")
        positions = entry.get("positions") or {}
        if not isinstance(positions, dict):
            problems.append(f"{pre}{cid} positions must be an object")
            continue
        for key, p in positions.items():
            if key not in VALID_KEYS:
                problems.append(f"{pre}{cid} bad issue key {key!r}")
                continue
            plist = p if isinstance(p, list) else [p]
            if len(plist) > MAX_ENTRIES:
                problems.append(f"{pre}{cid}/{key} has {len(plist)} entries (max {MAX_ENTRIES})")
            for i, e in enumerate(plist):
                where = f"[{i}]" if isinstance(p, list) else ""
                for msg in entry_problems(e):
                    problems.append(f"{pre}{cid}/{key}{where} {msg}")
    return problems


def count_entries(data: dict) -> tuple[int, int]:
    """(candidates, issue entries) in a parsed research file."""
    cands = entries = 0
    for entry in data.values():
        if not isinstance(entry, dict):
            continue
        cands += 1
        for p in (entry.get("positions") or {}).values():
            entries += len(p) if isinstance(p, list) else 1
    return cands, entries
