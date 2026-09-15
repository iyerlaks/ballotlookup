# Refreshing the candidate data

The PA Department of State publishes the Official Candidate Listing as a client-side
DataTable at pavoterservices.pa.gov. The site sits behind Incapsula bot protection,
so plain HTTP scripts are blocked — the capture is done through a real browser
(Claude's in-app browser, or your own with DevTools). Takes about five minutes.

## Steps

1. Open https://www.pavoterservices.pa.gov/electioninfo/ElectionInfo.aspx
   in a browser. Confirm the election dropdown shows
   **2026 General Election (11/03/2026)** (it is the default).

2. Open the DevTools console and run:

   ```js
   (() => {
     const dt = jQuery('#ctl00_ContentPlaceHolder1_gvElectionInfo').DataTable();
     const OFFICES = ['GOVERNOR', 'LIEUTENANT GOVERNOR', 'REPRESENTATIVE IN CONGRESS',
       'SENATOR IN THE GENERAL ASSEMBLY', 'REPRESENTATIVE IN THE GENERAL ASSEMBLY'];
     const rows = dt.rows().data().toArray()
       .filter(r => OFFICES.includes((r.OfficeName || '').trim()))
       .filter(r => r.CandidateStatusValue === 'Approved')
       .map(r => [r.CandidateName, (r.OfficeName || '').trim(), r.DistrictName,
                  r.PartyName, r.CountyName, r.PrimaryResult, r.CandidateID,
                  r.CFOnlineURL || '']);
     const out = {fields: ['name','office','district','party','county',
                           'primaryWin','candidateId','cfUrl'], rows};
     copy(JSON.stringify(out));   // puts it on the clipboard
     return rows.length + ' rows copied to clipboard';
   })()
   ```

3. Paste the clipboard contents into `data/candidates_raw.json` (replace the file).

   (Claude in-app browser variant, used for the 2026-08-04 refresh: `copy()`
   only exists in DevTools, so instead stash the rows on `window`, start a
   tiny local HTTP server that writes POST bodies to disk, and
   `fetch('http://127.0.0.1:8899/upload', {method:'POST', mode:'no-cors',
   body: JSON.stringify(out)})` from the page. Kill the server afterward.)

4. Set the two voter-facing freshness dates by hand in `data/issues.json`
   (`freshness.rosterChecked` = the date of this capture;
   `freshness.positionsReviewed` = the date of the last research/review pass,
   which changes only when positions were actually re-researched). The build
   refuses to run without both, and never stamps the build date: a rebuild
   after a script or formatting change must not relabel unchanged data as
   newly checked. Then rebuild and sanity-check the printed summary (17 CDs,
   25 senate districts, 203 house districts):

   ```
   python scripts/build_data.py
   ```

5. Spot-check one known race in the browser, then redeploy the `site/` folder.

## What the build script filters

- Democratic/Republican rows with `primaryWin != "true"` are dropped (primary losers).
- Other parties have no primaries; every `Approved` row is kept. After the
  **Aug 3, 2026** filing deadline this is where Libertarian/Green/independent
  candidates appear.
- Withdrawn/Terminated candidates are excluded at capture time (step 2 filter).
  A post-deadline refresh also picks up any candidates removed by nomination
  objections.
