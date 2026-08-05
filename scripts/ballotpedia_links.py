"""Find + strictly verify Ballotpedia pages for every kept candidate.

Produces {candidateId: url} JSON for scripts/merge_ballotpedia.py. Used for
the 2026-08-04 refresh (319 verified of 424); re-run at each refresh so new
filers pick up pages as Ballotpedia adds them.

Ballotpedia serves HTTP 202 bot-challenges to plain HTTP, so all fetches go
through the Bright Data CLI (`bdata scrape` / `bdata search`, needs
BRIGHTDATA_API_KEY). For each candidate:

  1. Guess URL variants from the SoS name (First_Last first — most page
     titles use the common short form).
  2. If guesses fail, Google `site:ballotpedia.org <name> Pennsylvania
     <office words>` (us-geo) and try the ballotpedia hits.
  3. STRICT verification, all three required:
       a. page is not a disambiguation page and not a soft-404 ("page you're
          looking for does not exist" is served with HTTP 200);
       b. the URL slug contains the candidate's last name (blocks district-
          overview and election-overview pages, which pass string checks);
       c. the page body names the exact district ("Pennsylvania House of
          Representatives District N", "Pennsylvania's Nth Congressional
          District", "Pennsylvania State Senate District N") or, for
          statewide, the office ("Governor of Pennsylvania" / "Lieutenant
          Governor of Pennsylvania").
     Candidates with no strictly-verified page keep the site's uniform
     search-link fallback — same chip either way, per the nonpartisan rule.

Usage: python scripts/ballotpedia_links.py <out.json>
Runs ~6 parallel bdata calls; a full 424-candidate sweep takes ~30-45 min.
"""
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BDATA = shutil.which("bdata") or "bdata"
MAX_PARALLEL = 6
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
ORDINAL = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

OFFICES = {
    "GOVERNOR", "LIEUTENANT GOVERNOR", "REPRESENTATIVE IN CONGRESS",
    "SENATOR IN THE GENERAL ASSEMBLY", "REPRESENTATIVE IN THE GENERAL ASSEMBLY",
}


def split_name(raw):
    raw = re.sub(r"\s+", " ", raw.strip())
    last, first = ([p.strip() for p in raw.split(",", 1)] if "," in raw else (raw, ""))
    def fix(w):
        parts = re.split(r"([-'])", w.lower())
        word = "".join(p.capitalize() if p not in "-'" else p for p in parts)
        if word.lower().startswith("mc") and len(word) > 2:
            word = "Mc" + word[2:].capitalize()
        return word
    first_w = [fix(w) for w in first.split()]
    last_w = [fix(w) for w in last.split() if w.upper().rstrip(".") not in SUFFIXES]
    return first_w, last_w


def url_variants(raw):
    first_w, last_w = split_name(raw)
    non_init = [w for w in first_w if len(w.rstrip(".")) > 1]
    seen, out = set(), []
    for words in ([non_init[:1] + last_w] if non_init else []) + [non_init + last_w, first_w + last_w]:
        slug = "_".join(words)
        if slug and slug not in seen:
            seen.add(slug)
            out.append("https://ballotpedia.org/" + slug)
    return out


def strict_strings(office, district):
    if office == "GOVERNOR":
        return ["Governor of Pennsylvania"]
    if office == "LIEUTENANT GOVERNOR":
        return ["Lieutenant Governor of Pennsylvania", "lieutenant governor of Pennsylvania"]
    n = int(re.match(r"(\d+)", district).group(1))
    if office == "REPRESENTATIVE IN CONGRESS":
        return [f"Pennsylvania's {ORDINAL(n)} Congressional District"]
    if office == "SENATOR IN THE GENERAL ASSEMBLY":
        return [f"Pennsylvania State Senate District {n}"]
    return [f"Pennsylvania House of Representatives District {n}"]


def run_cmd(args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout or "", p.stderr or ""


def scrape(url):
    rc, out, _ = run_cmd([BDATA, "scrape", url, "--format", "markdown"])
    return out if rc == 0 else None


def serp_urls(query):
    rc, out, _ = run_cmd([BDATA, "search", query, "--json", "--country", "us"])
    if rc != 0:
        return []
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    urls = []
    for item in (data.get("organic") or []):
        link = (item.get("link") or "").split("?")[0].split("#")[0]
        if link.startswith("https://ballotpedia.org/") and link not in urls:
            urls.append(link)
    return urls[:3]


def slug_has_lastname(url, raw_name):
    slug = re.sub(r"[^a-z]", "", url.rsplit("/", 1)[-1].lower())
    _, last_w = split_name(raw_name)
    return any(re.sub(r"[^a-z]", "", w.lower()) in slug for w in last_w)


def verified(url, raw_name, office, district):
    if not slug_has_lastname(url, raw_name):
        return False
    body = scrape(url)
    if not body:
        return False
    low = body[:5000].lower()
    if "may refer to" in low or "disambiguation" in low or "does not exist" in low:
        return False
    return any(s in body for s in strict_strings(office, district))


def resolve(cid, name, office, district):
    for url in url_variants(name):
        if verified(url, name, office, district):
            return cid, url
    distword = {"REPRESENTATIVE IN CONGRESS": "congressional district",
                "SENATOR IN THE GENERAL ASSEMBLY": "state senate",
                "REPRESENTATIVE IN THE GENERAL ASSEMBLY": "house of representatives"}.get(office, "")
    first_w, last_w = split_name(name)
    short = " ".join(([w for w in first_w if len(w.rstrip('.')) > 1][:1] or first_w[:1]) + last_w)
    for url in serp_urls(f"site:ballotpedia.org {short} Pennsylvania {distword}"):
        if verified(url, name, office, district):
            return cid, url
    return cid, None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: ballotpedia_links.py <out.json>")
    raw = json.loads((ROOT / "data" / "candidates_raw.json").read_text(encoding="utf-8"))
    kept = {}
    for name, office, district, party, county, pw, cid, cf in raw["rows"]:
        office = office.strip()
        if office not in OFFICES:
            continue
        if party in ("Democratic", "Republican") and pw != "true":
            continue
        kept[str(cid)] = (name, office, district)

    links = {}
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        futs = {ex.submit(resolve, cid, *v): cid for cid, v in kept.items()}
        for fut in as_completed(futs):
            cid, url = fut.result()
            done += 1
            if url:
                links[cid] = url
            print(f"[{done}/{len(kept)}] {'OK ' + url if url else 'none'}  {kept[cid][0][:40]}", flush=True)

    Path(sys.argv[1]).write_text(json.dumps(links, indent=1) + "\n", encoding="utf-8")
    print(f"done: {len(links)} strictly verified of {len(kept)}")


if __name__ == "__main__":
    main()
