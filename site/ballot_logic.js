// Pure ballot logic: geocoder result -> districts -> list of races to show.
// No DOM, no network. Loaded by index.html before the UI script, and by
// tests/test_ballot_logic.js under node. Keep it that way: everything that
// decides WHAT is on a ballot lives here; index.html only decides how it looks.
(function (root) {
  'use strict';

  var PA_STATE_GEOID = '42';

  // Pennsylvania senators serve four-year terms. Even-numbered districts are
  // elected in years congruent to 2 mod 4 (2026, 2030, ...), odd-numbered in
  // years congruent to 0 mod 4 (2028, 2032, ...).
  function senateUpThisCycle(sdNum, electionYear) {
    var y = electionYear % 4;
    if (y === 2) return sdNum % 2 === 0;
    if (y === 0) return sdNum % 2 === 1;
    return false;  // odd election years: no state senate seats on the ballot
  }

  function nextSenateYear(sdNum, electionYear) {
    var y = electionYear + 1;
    while (!senateUpThisCycle(sdNum, y)) y++;
    return y;
  }

  // First geography object whose layer name contains the given word
  // (Census layer names are like "119th Congressional Districts",
  // "2024 State Legislative Districts - Upper").
  function layer(geos, nameContains) {
    var keys = Object.keys(geos || {});
    for (var i = 0; i < keys.length; i++) {
      if (keys[i].indexOf(nameContains) !== -1) return (geos[keys[i]] && geos[keys[i]][0]) || null;
    }
    return null;
  }

  // District number from a Census GEOID (state FIPS + district code).
  // Anything that is not a positive integer is treated as missing.
  function districtNum(geo) {
    if (!geo || typeof geo.GEOID !== 'string' || geo.GEOID.length <= 2) return null;
    var n = parseInt(geo.GEOID.slice(2), 10);
    return Number.isInteger(n) && n > 0 ? n : null;
  }

  // One geocoder match -> {stateGeoid, stateName, county, cd, sd, hd, missing[]}
  function resolveDistricts(geographies) {
    var g = geographies || {};
    var state = layer(g, 'States');
    var county = layer(g, 'Counties');
    var out = {
      stateGeoid: state ? state.GEOID : null,
      stateName: state ? state.NAME : null,
      county: county ? county.NAME : '',
      cd: districtNum(layer(g, 'Congressional')),
      sd: districtNum(layer(g, 'Upper')),
      hd: districtNum(layer(g, 'Lower')),
      missing: []
    };
    if (!out.cd) out.missing.push('congressional district');
    if (!out.sd) out.missing.push('state senate district');
    if (!out.hd) out.missing.push('state house district');
    return out;
  }

  function isPennsylvania(d) { return d.stateGeoid === PA_STATE_GEOID; }

  function ordinal(n) {
    var s = ['th', 'st', 'nd', 'rd'], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  function raceKey(prefix, n) {
    return prefix === 'CD' ? 'CD-' + String(n).padStart(2, '0') : prefix + '-' + n;
  }

  // Pair the Governor and Lt. Governor races into tickets by party (one vote
  // elects both). Anyone without a running mate in the data still gets a
  // row, with the other half null, rather than being dropped.
  function ticketPairs(gov, ltg) {
    var gs = (gov && gov.candidates) || [], ls = (ltg && ltg.candidates) || [];
    var used = {};
    var pairs = gs.map(function (g) {
      var idx = -1;
      for (var i = 0; i < ls.length; i++) {
        if (!used[i] && ls[i].partyCode === g.partyCode) { idx = i; break; }
      }
      if (idx >= 0) used[idx] = true;
      return {gov: g, ltg: idx >= 0 ? ls[idx] : null};
    });
    ls.forEach(function (l, i) { if (!used[i]) pairs.push({gov: null, ltg: l}); });
    return pairs;
  }

  // Districts + race database -> ordered list of ballot entries.
  //   status 'ticket' : statewide Gov/LtGov ticket (entry.ticket = {gov, ltg})
  //   status 'race'   : a race with candidates (entry.race)
  //   status 'notUp'  : office exists but is not elected this cycle (entry.nextYear)
  //   status 'gap'    : the office IS up but our data has no race -- our problem
  // Throws if any district is missing: callers must check resolveDistricts().missing first.
  function planBallot(d, races, electionYear) {
    if (!d || d.missing.length) throw new Error('planBallot needs complete districts');
    var r = races || {};
    var plan = [{
      key: 'TICKET', status: 'ticket', title: 'Governor and Lieutenant Governor', dist: 'Statewide',
      ticket: {gov: r['STATEWIDE-GOV'] || null, ltg: r['STATEWIDE-LTGOV'] || null}
    }];
    var cdKey = raceKey('CD', d.cd);
    plan.push({key: cdKey, status: r[cdKey] ? 'race' : 'gap', title: 'U.S. House of Representatives',
      office: 'U.S. House', dist: ordinal(d.cd) + ' Congressional District', race: r[cdKey] || null});
    var sdKey = raceKey('SD', d.sd);
    var sdEntry = {key: sdKey, title: 'Pennsylvania State Senate', office: 'State Senate',
      dist: ordinal(d.sd) + ' Senatorial District', race: r[sdKey] || null};
    if (r[sdKey]) sdEntry.status = 'race';
    else if (senateUpThisCycle(d.sd, electionYear)) sdEntry.status = 'gap';
    else { sdEntry.status = 'notUp'; sdEntry.nextYear = nextSenateYear(d.sd, electionYear); }
    plan.push(sdEntry);
    var hdKey = raceKey('HD', d.hd);
    plan.push({key: hdKey, status: r[hdKey] ? 'race' : 'gap', title: 'Pennsylvania State House',
      office: 'State House', dist: ordinal(d.hd) + ' Legislative District', race: r[hdKey] || null});
    return plan;
  }

  function districtLine(d) {
    return (d.county || '') +
      ' · ' + ordinal(d.cd) + ' Congressional District' +
      ' · Senate District ' + d.sd +
      ' · House District ' + d.hd;
  }

  root.BallotLogic = {
    PA_STATE_GEOID: PA_STATE_GEOID,
    senateUpThisCycle: senateUpThisCycle,
    nextSenateYear: nextSenateYear,
    layer: layer,
    districtNum: districtNum,
    resolveDistricts: resolveDistricts,
    isPennsylvania: isPennsylvania,
    ordinal: ordinal,
    raceKey: raceKey,
    ticketPairs: ticketPairs,
    planBallot: planBallot,
    districtLine: districtLine
  };
})(typeof module !== 'undefined' && module.exports ? module.exports : window);
