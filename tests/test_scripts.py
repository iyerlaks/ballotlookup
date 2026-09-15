"""Regression checks for the data scripts. No dependencies:

    python -m unittest discover -s tests -v

Each test builds a tiny fake repo in a temp dir and points the scripts at it
with BALLOT_ROOT, so nothing here touches the real data/ or site/.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
import research_rules as rr  # noqa: E402

FIELDS = ["name", "office", "district", "party", "county", "primaryWin", "candidateId", "cfUrl"]
ROWS = [
    ["SHAPIRO, JOSH", "GOVERNOR", "", "Democratic", "MONTGOMERY", "true", 1, ""],
    ["LOSER, PRIMARY", "GOVERNOR", "", "Democratic", "MONTGOMERY", "false", 2, ""],
    ["GARRITY, STACY", "GOVERNOR", "", "Republican", "BRADFORD", "true", 3, ""],
    ["KRAWCHUK, KEN", "GOVERNOR", "", "Libertarian", "MONTGOMERY", "", 4, ""],
    ["DAVIS, AUSTIN", "LIEUTENANT GOVERNOR", "", "Democratic", "ALLEGHENY", "true", 5, ""],
    ["HOULAHAN, CHRISSY", "REPRESENTATIVE IN CONGRESS", "6th Congressional District", "Democratic", "CHESTER", "true", 6, "www.example.org/cf"],
    ["HOULAHAN, CHRISSY", "REPRESENTATIVE IN CONGRESS", "6th Congressional District", "Democratic", "CHESTER", "true", 6, "www.example.org/cf"],
    ["HOWARD, KRISTINE", "REPRESENTATIVE IN THE GENERAL ASSEMBLY", "167th Legislative District", "Democratic", "CHESTER", "true", 7, ""],
    ["SOMEONE, ELSE", "SENATOR IN THE GENERAL ASSEMBLY", "20th Senatorial District", "Republican", "CHESTER", "true", 8, ""],
    ["JUDGE, SOME", "JUDGE OF THE COURT OF COMMON PLEAS", "Chester", "Democratic", "CHESTER", "true", 9, ""],
]
GOOD_ENTRY = {"summary": "Says X.", "short": "X.", "source": "https://example.org/x", "date": "2026-02"}


def make_repo(tmp: Path, freshness=True) -> Path:
    (tmp / "data").mkdir()
    (tmp / "site").mkdir()
    (tmp / "data" / "candidates_raw.json").write_text(json.dumps({"fields": FIELDS, "rows": ROWS}), encoding="utf-8")
    issues = {"note": "n", "siteUrl": "s", "contactEmail": "c@example.org",
              "voting": {}, "issues": [{"key": "economy", "label": "Economy"}], "positions": {}}
    if freshness:
        issues["freshness"] = {"rosterChecked": "2026-08-24", "positionsReviewed": "2026-08-24"}
    (tmp / "data" / "issues.json").write_text(json.dumps(issues), encoding="utf-8")
    return tmp


def run(script: str, root: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, BALLOT_ROOT=str(root))
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], env=env,
                          capture_output=True, text=True, encoding="utf-8")


def load_data_js(root: Path) -> dict:
    src = (root / "site" / "data.js").read_text(encoding="utf-8")
    return json.loads(src[src.index("=") + 1:].strip().rstrip(";"))


class Rules(unittest.TestCase):
    def test_good_entry_is_clean(self):
        self.assertEqual(rr.entry_problems(GOOD_ENTRY), [])
        self.assertEqual(rr.entry_problems({**GOOD_ENTRY, "date": "2026-02-14"}), [])

    def test_date_required_and_well_formed(self):
        for bad in (None, "", "Feb 2026", "2026", "2026-13", "2026-02-30", "02-2026", 2026):
            with self.subTest(bad=bad):
                self.assertTrue(any("date" in m for m in rr.entry_problems({**GOOD_ENTRY, "date": bad})))

    def test_source_must_be_safe_absolute_url(self):
        for bad in (None, "", "example.org/x", "javascript:alert(1)", "mailto:a@b.c", "data:text/html,x",
                    "https://example.org/a b", " https://example.org/x", "http://localhost"):
            with self.subTest(bad=bad):
                self.assertTrue(any("source URL" in m for m in rr.entry_problems({**GOOD_ENTRY, "source": bad})))

    def test_summary_required(self):
        self.assertIn("missing summary", rr.entry_problems({**GOOD_ENTRY, "summary": "  "}))

    def test_check_file_covers_ids_keys_lists_and_urls(self):
        known = {"1": "SHAPIRO, JOSH"}
        data = {
            "1": {"name": "x", "website": "notaurl", "positions": {
                "economy": [GOOD_ENTRY] * 4,
                "bogus": GOOD_ENTRY,
            }},
            "99": {"name": "ghost", "positions": {}},
        }
        probs = rr.check_file(data, known)
        self.assertTrue(any("unknown candidateId 99" in p for p in probs))
        self.assertTrue(any("bad website URL" in p for p in probs))
        self.assertTrue(any("has 4 entries (max 3)" in p for p in probs))
        self.assertTrue(any("bad issue key 'bogus'" in p for p in probs))


class Validator(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        make_repo(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, obj):
        p = self.tmp / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return str(p)

    def test_clean_file_passes(self):
        f = self.write("ok.json", {"1": {"name": "x", "positions": {"economy": GOOD_ENTRY}}})
        r = run("validate_research.py", self.tmp, f)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("validated 1 candidates (1 issue entries)", r.stdout)

    def test_missing_date_fails(self):
        f = self.write("nodate.json", {"1": {"name": "x", "positions": {"economy": {k: v for k, v in GOOD_ENTRY.items() if k != "date"}}}})
        r = run("validate_research.py", self.tmp, f)
        self.assertEqual(r.returncode, 1)
        self.assertIn("date must be", r.stdout)

    def test_unsafe_url_fails(self):
        f = self.write("js.json", {"1": {"name": "x", "positions": {"economy": {**GOOD_ENTRY, "source": "javascript:alert(1)"}}}})
        r = run("validate_research.py", self.tmp, f)
        self.assertEqual(r.returncode, 1)
        self.assertIn("bad source URL", r.stdout)


class Merge(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        make_repo(self.tmp)
        self.issues = self.tmp / "data" / "issues.json"
        self.before = self.issues.read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, obj):
        p = self.tmp / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return str(p)

    def test_clean_merge_writes_and_sorts_newest_first(self):
        older = {**GOOD_ENTRY, "date": "2025-11", "summary": "older"}
        newer = {**GOOD_ENTRY, "date": "2026-03", "summary": "newer"}
        f = self.write("ok.json", {"1": {"name": "x", "website": "https://example.org", "positions": {"economy": [older, newer]}}})
        r = run("merge_positions.py", self.tmp, f)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        db = json.loads(self.issues.read_text(encoding="utf-8"))
        self.assertEqual([e["summary"] for e in db["positions"]["1"]["positions"]["economy"]], ["newer", "older"])
        self.assertEqual(db["positions"]["1"]["website"], "https://example.org")

    def test_one_bad_file_blocks_the_whole_merge(self):
        good = self.write("good.json", {"1": {"name": "x", "positions": {"economy": GOOD_ENTRY}}})
        bad = self.write("bad.json", {"3": {"name": "y", "positions": {"economy": {**GOOD_ENTRY, "date": "soon"}}}})
        r = run("merge_positions.py", self.tmp, good, bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSED", r.stdout)
        self.assertEqual(self.issues.read_text(encoding="utf-8"), self.before, "nothing may be written")

    def test_unknown_candidate_blocks_without_writing(self):
        f = self.write("ghost.json", {"99": {"name": "ghost", "positions": {"economy": GOOD_ENTRY}}})
        r = run("merge_positions.py", self.tmp, f)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.issues.read_text(encoding="utf-8"), self.before)

    def test_existing_candidate_needs_force(self):
        f = self.write("a.json", {"1": {"name": "x", "positions": {"economy": GOOD_ENTRY}}})
        self.assertEqual(run("merge_positions.py", self.tmp, f).returncode, 0)
        snapshot = self.issues.read_text(encoding="utf-8")
        again = self.write("b.json", {"1": {"name": "x", "positions": {"economy": {**GOOD_ENTRY, "summary": "replaced"}}}})
        r = run("merge_positions.py", self.tmp, again)
        self.assertEqual(r.returncode, 1)
        self.assertIn("already present", r.stdout)
        self.assertEqual(self.issues.read_text(encoding="utf-8"), snapshot)
        r = run("merge_positions.py", self.tmp, "--force", again)
        self.assertEqual(r.returncode, 0, r.stdout)
        db = json.loads(self.issues.read_text(encoding="utf-8"))
        self.assertEqual(db["positions"]["1"]["positions"]["economy"]["summary"], "replaced")


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_candidate_filtering_and_keys(self):
        make_repo(self.tmp)
        r = run("build_data.py", self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        D = load_data_js(self.tmp)
        gov = [c["name"] for c in D["races"]["STATEWIDE-GOV"]["candidates"]]
        self.assertNotIn("Primary Loser", gov, "major-party primary losers are dropped")
        self.assertEqual(gov, ["Josh Shapiro", "Stacy Garrity", "Ken Krawchuk"], "DEM, REP, then others; minor parties need no primary")
        self.assertEqual(len(D["races"]["CD-06"]["candidates"]), 1, "duplicate rows collapse")
        self.assertIn("HD-167", D["races"])
        self.assertIn("SD-20", D["races"])
        self.assertFalse(any(k.startswith("JUDGE") for k in D["races"]), "offices outside the covered set are ignored")
        self.assertEqual(D["races"]["CD-06"]["candidates"][0]["cfUrl"], "https://www.example.org/cf")

    def test_freshness_comes_from_data_not_build_time(self):
        make_repo(self.tmp)
        self.assertEqual(run("build_data.py", self.tmp).returncode, 0)
        D = load_data_js(self.tmp)
        self.assertEqual(D["freshness"], {"rosterChecked": "2026-08-24", "positionsReviewed": "2026-08-24"})
        self.assertEqual(D["lastUpdated"], "2026-08-24")
        self.assertNotIn("August 3", json.dumps(D))

    def test_build_refuses_without_freshness(self):
        make_repo(self.tmp, freshness=False)
        r = run("build_data.py", self.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("freshness", r.stderr + r.stdout)
        self.assertFalse((self.tmp / "site" / "data.js").exists())


if __name__ == "__main__":
    unittest.main()
