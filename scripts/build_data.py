"""Build site/data.js from the raw PA DoS candidate extract.

Input:  data/candidates_raw.json
        {"fields": [name, office, district, party, county, primaryWin, candidateId, cfUrl],
         "rows": [[...], ...]}
        Raw rows come from the PA Department of State Official Candidate Listing
        (pavoterservices.pa.gov > Election Information > 2026 General Election).
        See scripts/refresh_data.md for how to re-capture after the Aug 3 2026
        third-party filing deadline.

Output: site/data.js  -> window.BALLOT_DATA = {...}
        Races keyed by district code: STATEWIDE-GOV, STATEWIDE-LTGOV,
        CD-06, SD-19, HD-167, etc.

Rules:
  - Democratic/Republican candidates are kept only if they won their primary.
  - All other parties are kept if status was Approved (they have no primary;
    third-party/independent candidates file by Aug 3, 2026).
  - Duplicate rows (same candidate id + district) are collapsed.

Issue positions:
  data/issues.json (optional) is merged in by candidate id. See
  data/ISSUES_GUIDE.md for the volunteer data-entry format. Candidates
  without entries simply render without a comparison column filled in.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OFFICE_MAP = {
    "GOVERNOR": ("STATEWIDE-GOV", "Governor"),
    "LIEUTENANT GOVERNOR": ("STATEWIDE-LTGOV", "Lieutenant Governor"),
    "REPRESENTATIVE IN CONGRESS": ("CD", "U.S. House of Representatives"),
    "SENATOR IN THE GENERAL ASSEMBLY": ("SD", "Pennsylvania State Senate"),
    "REPRESENTATIVE IN THE GENERAL ASSEMBLY": ("HD", "Pennsylvania State House"),
}

PARTY_MAP = {
    "Democratic": "DEM", "Republican": "REP", "Libertarian": "LIB",
    "Green": "GRN", "Constitution": "CST", "Forward": "FWD",
    "American Solidarity": "ASP",
    # Post-Aug-3 filing labels seen in the 2026 extract. PA treats
    # "Independent", "Independent Party", and "The Independent Party" as
    # distinct ballot labels; keep the codes distinct too.
    "Independent": "IND", "Independent Party": "INDP",
    "The Independent Party": "TIP", "Forward Independent": "FWDI",
}

SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def district_num(district_name: str) -> int | None:
    m = re.match(r"(\d+)(st|nd|rd|th)\b", district_name.strip())
    return int(m.group(1)) if m else None


def title_case_name(raw: str) -> str:
    """'HOULAHAN, CHRISSY' -> 'Chrissy Houlahan'; handles Jr/III, Mc, O', hyphens."""
    raw = re.sub(r"\s+", " ", raw.strip())
    if "," in raw:
        last, first = [p.strip() for p in raw.split(",", 1)]
    else:
        last, first = raw, ""

    def fix_word(w: str) -> str:
        up = w.upper().rstrip(".")
        if up in SUFFIXES:
            return {"JR": "Jr.", "SR": "Sr."}.get(up, up)
        if len(w) <= 2 and w.upper() == w and "." not in w and up not in {"ED", "AL", "BO", "CY", "TY", "JD", "PJ", "TJ", "CJ", "JJ", "RJ", "AJ", "DJ"}:
            # bare initial like 'F' or 'GT'
            return ".".join(w.upper()) + "."
        parts = re.split(r"([-'])", w.lower())
        parts = [p.capitalize() if p not in "-'" else p for p in parts]
        word = "".join(parts)
        if word.lower().startswith("mc") and len(word) > 2:
            word = "Mc" + word[2:].capitalize()
        return word

    fixed_first = " ".join(fix_word(w) for w in first.split())
    fixed_last = " ".join(fix_word(w) for w in last.split())
    return f"{fixed_first} {fixed_last}".strip()


def load_issues() -> dict:
    path = ROOT / "data" / "issues.json"
    if not path.exists():
        return {"issues": [], "positions": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    raw = json.loads((ROOT / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    rows = raw["rows"]
    issues_db = load_issues()
    positions_by_id = issues_db.get("positions", {})

    seen: set[tuple[int, str]] = set()
    races: dict[str, dict] = {}
    skipped_lost_primary = 0

    for name, office, district, party, county, primary_win, cand_id, cf_url in rows:
        office = office.strip()
        if office not in OFFICE_MAP:
            continue
        key_prefix, office_label = OFFICE_MAP[office]

        if key_prefix in ("CD", "SD", "HD"):
            num = district_num(district)
            if num is None:
                print(f"  !! could not parse district: {district!r} ({name})", file=sys.stderr)
                continue
            key = f"{key_prefix}-{num:02d}" if key_prefix == "CD" else f"{key_prefix}-{num}"
            district_label = district.strip()
        else:
            key = key_prefix
            district_label = "Statewide"

        dedupe_key = (cand_id, key)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        is_major = party in ("Democratic", "Republican")
        if is_major and primary_win != "true":
            skipped_lost_primary += 1
            continue

        race = races.setdefault(key, {
            "office": office_label,
            "district": district_label,
            "candidates": [],
        })
        cand = {
            "name": title_case_name(name),
            "party": party,
            "partyCode": PARTY_MAP.get(party, party[:3].upper()),
            "county": county.title() if county else "",
            "cfUrl": ("https://" + cf_url) if cf_url and not cf_url.startswith("http") else cf_url,
        }
        entry = positions_by_id.get(str(cand_id))
        if entry:
            if entry.get("website"):
                cand["website"] = entry["website"]
            if entry.get("ballotpedia"):
                cand["ballotpedia"] = entry["ballotpedia"]
            if entry.get("positions"):
                cand["positions"] = entry["positions"]
        race["candidates"].append(cand)

    # stable order: DEM/REP alphabetical by ballot convention is complex; use
    # party name then candidate name so ordering is deterministic and neutral
    party_order = {"Democratic": 0, "Republican": 1}
    for race in races.values():
        race["candidates"].sort(key=lambda c: (party_order.get(c["party"], 2), c["party"], c["name"]))

    out = {
        "election": "2026 Pennsylvania General Election",
        "electionDate": "2026-11-03",
        "dataSource": "Pennsylvania Department of State — Official Candidate Listing (pavoterservices.pa.gov)",
        "lastUpdated": date.today().isoformat(),
        "notes": "Minor-party and independent candidates file by Aug 3, 2026 and may not appear yet.",
        "issues": issues_db.get("issues", []),
        "issuesNote": issues_db.get("note", ""),
        "voting": issues_db.get("voting", {}),
        "siteUrl": issues_db.get("siteUrl", ""),
        "contactEmail": issues_db.get("contactEmail", ""),
        "races": races,
    }

    dest = ROOT / "site" / "data.js"
    dest.write_text(
        "// Generated by scripts/build_data.py — do not edit by hand.\n"
        "window.BALLOT_DATA = " + json.dumps(out, indent=1) + ";\n",
        encoding="utf-8",
    )

    n_cand = sum(len(r["candidates"]) for r in races.values())
    cds = sorted(k for k in races if k.startswith("CD"))
    sds = sorted(int(k.split("-")[1]) for k in races if k.startswith("SD"))
    hds = sorted(int(k.split("-")[1]) for k in races if k.startswith("HD"))
    print(f"races: {len(races)}  candidates kept: {n_cand}  (dropped {skipped_lost_primary} primary losers)")
    print(f"congressional districts: {len(cds)}")
    print(f"senate districts ({len(sds)}): {sds}")
    print(f"house districts: {len(hds)} of 203; missing: {sorted(set(range(1,204)) - set(hds))}")
    print(f"wrote {dest} ({dest.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
