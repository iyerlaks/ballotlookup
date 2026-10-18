// Regression checks for site/ballot_logic.js. No dependencies:
//   node --test tests/
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const BL = require(path.join(__dirname, '..', 'site', 'ballot_logic.js')).BallotLogic;

// A geocoder "geographies" block shaped like the Census response.
function geos({state = '42', stateName = 'Pennsylvania', county = 'Chester', cd = '06', sd = '019', hd = '167', drop = []} = {}) {
  const g = {
    'States': [{GEOID: state, NAME: stateName}],
    'Counties': [{GEOID: state + '029', NAME: county}],
    '119th Congressional Districts': [{GEOID: state + cd}],
    '2024 State Legislative Districts - Upper': [{GEOID: state + sd}],
    '2024 State Legislative Districts - Lower': [{GEOID: state + hd}],
  };
  for (const k of drop) delete g[k];
  return g;
}

const RACES = {
  'STATEWIDE-GOV': {candidates: [{name: 'G-Dem', partyCode: 'DEM'}, {name: 'G-Rep', partyCode: 'REP'}, {name: 'G-Lib', partyCode: 'LIB'}]},
  'STATEWIDE-LTGOV': {candidates: [{name: 'L-Dem', partyCode: 'DEM'}, {name: 'L-Rep', partyCode: 'REP'}]},
  'CD-06': {candidates: [{name: 'A'}]},
  'SD-20': {candidates: [{name: 'B'}]},
  'HD-167': {candidates: [{name: 'C'}]},
};

test('resolveDistricts: complete Exton-style result', () => {
  const d = BL.resolveDistricts(geos());
  assert.deepEqual(d, {stateGeoid: '42', stateName: 'Pennsylvania', county: 'Chester', cd: 6, sd: 19, hd: 167, missing: []});
  assert.equal(BL.isPennsylvania(d), true);
  assert.equal(BL.districtLine(d), 'Chester · 6th Congressional District · Senate District 19 · House District 167');
});

test('resolveDistricts: out-of-state address is detected, never shown as a PA ballot', () => {
  const d = BL.resolveDistricts(geos({state: '11', stateName: 'District of Columbia'}));
  assert.equal(BL.isPennsylvania(d), false);
  assert.equal(d.stateName, 'District of Columbia');
});

test('resolveDistricts: each missing district layer is named', () => {
  const noHouse = BL.resolveDistricts(geos({drop: ['2024 State Legislative Districts - Lower']}));
  assert.deepEqual(noHouse.missing, ['state house district']);
  const nothing = BL.resolveDistricts(geos({drop: ['119th Congressional Districts', '2024 State Legislative Districts - Upper', '2024 State Legislative Districts - Lower']}));
  assert.deepEqual(nothing.missing, ['congressional district', 'state senate district', 'state house district']);
  assert.deepEqual(BL.resolveDistricts({}).missing.length, 3);
});

test('districtNum: malformed GEOIDs count as missing, not as district 0 or NaN', () => {
  assert.equal(BL.districtNum({GEOID: '42'}), null);
  assert.equal(BL.districtNum({GEOID: '42ZZ'}), null);
  assert.equal(BL.districtNum({GEOID: '4200'}), null);
  assert.equal(BL.districtNum({GEOID: '42006'}), 6);
  assert.equal(BL.districtNum(null), null);
});

test('planBallot refuses incomplete districts', () => {
  const d = BL.resolveDistricts(geos({drop: ['119th Congressional Districts']}));
  assert.throws(() => BL.planBallot(d, RACES, 2026), /complete districts/);
});

test('planBallot: full ballot, odd senate district is notUp with the next year', () => {
  const plan = BL.planBallot(BL.resolveDistricts(geos()), RACES, 2026);
  assert.deepEqual(plan.map(e => [e.key, e.status]), [
    ['TICKET', 'ticket'], ['CD-06', 'race'], ['SD-19', 'notUp'], ['HD-167', 'race']]);
  assert.equal(plan[2].nextYear, 2028);
  assert.equal(plan[0].ticket.gov, RACES['STATEWIDE-GOV']);
});

test('planBallot: a missing race for an office that IS up is a gap, not "not up"', () => {
  const plan = BL.planBallot(BL.resolveDistricts(geos({cd: '07', sd: '022', hd: '001'})), RACES, 2026);
  assert.deepEqual(plan.map(e => [e.key, e.status]), [
    ['TICKET', 'ticket'], ['CD-07', 'gap'], ['SD-22', 'gap'], ['HD-1', 'gap']]);
});

test('election-cycle handling: senate seats by year', () => {
  assert.equal(BL.senateUpThisCycle(20, 2026), true);
  assert.equal(BL.senateUpThisCycle(19, 2026), false);
  assert.equal(BL.senateUpThisCycle(19, 2028), true);
  assert.equal(BL.senateUpThisCycle(20, 2028), false);
  assert.equal(BL.senateUpThisCycle(20, 2027), false);
  assert.equal(BL.nextSenateYear(19, 2026), 2028);
  assert.equal(BL.nextSenateYear(20, 2026), 2030);
  // In 2028 an even district present in the data still renders as a race
  const plan = BL.planBallot(BL.resolveDistricts(geos({sd: '020'})), RACES, 2028);
  assert.equal(plan[2].status, 'race');
  // ...and an odd district missing from the data in 2028 is a gap
  const plan2 = BL.planBallot(BL.resolveDistricts(geos({sd: '019'})), RACES, 2028);
  assert.equal(plan2[2].status, 'gap');
});

test('ticketPairs: pairs by party, keeps unmatched halves visible', () => {
  const pairs = BL.ticketPairs(RACES['STATEWIDE-GOV'], RACES['STATEWIDE-LTGOV']);
  assert.deepEqual(pairs.map(p => [(p.gov || {}).name || null, (p.ltg || {}).name || null]),
    [['G-Dem', 'L-Dem'], ['G-Rep', 'L-Rep'], ['G-Lib', null]]);
  const extra = BL.ticketPairs(RACES['STATEWIDE-GOV'], {candidates: [{name: 'L-Grn', partyCode: 'GRN'}]});
  assert.deepEqual(extra[extra.length - 1], {gov: null, ltg: {name: 'L-Grn', partyCode: 'GRN'}});
  assert.deepEqual(BL.ticketPairs(null, null), []);
});

test('raceKey and ordinal match the data.js key scheme', () => {
  assert.equal(BL.raceKey('CD', 6), 'CD-06');
  assert.equal(BL.raceKey('SD', 6), 'SD-6');
  assert.equal(BL.raceKey('HD', 167), 'HD-167');
  assert.deepEqual([1, 2, 3, 4, 11, 12, 13, 21, 22, 103].map(BL.ordinal),
    ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '103rd']);
});

test('electionOver: freezes at midnight Eastern after election day, never before', () => {
  const at = iso => Date.parse(iso);
  assert.equal(BL.electionOver('2026-11-03', at('2026-11-03T12:00:00-05:00')), false);  // polls open
  assert.equal(BL.electionOver('2026-11-03', at('2026-11-03T23:59:59-05:00')), false);  // after polls close, still Nov 3
  assert.equal(BL.electionOver('2026-11-03', at('2026-11-04T00:00:00-05:00')), true);
  assert.equal(BL.electionOver('2026-11-03', at('2026-10-18T09:00:00-04:00')), false);
  // month rollover
  assert.equal(BL.electionOver('2026-10-31', at('2026-11-01T05:00:00Z')), true);
  // bad or missing dates never freeze the tool
  for (const bad of ['', null, undefined, '2026-11', 'Nov 3 2026']) {
    assert.equal(BL.electionOver(bad, at('2030-01-01T00:00:00Z')), false);
  }
});

test('generated data.js: every key the planner can ask for resolves consistently', () => {
  const fs = require('fs');
  const src = fs.readFileSync(path.join(__dirname, '..', 'site', 'data.js'), 'utf8');
  const D = JSON.parse(src.slice(src.indexOf('=') + 1).trim().replace(/;\s*$/, ''));
  assert.ok(D.races['STATEWIDE-GOV'] && D.races['STATEWIDE-LTGOV'], 'statewide ticket present');
  assert.match(D.freshness.rosterChecked, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(D.freshness.positionsReviewed, /^\d{4}-\d{2}-\d{2}$/);
  for (let n = 1; n <= 17; n++) assert.ok(D.races[BL.raceKey('CD', n)], 'CD ' + n);
  for (let n = 1; n <= 203; n++) assert.ok(D.races[BL.raceKey('HD', n)], 'HD ' + n);
  const year = parseInt(D.electionDate.slice(0, 4), 10);
  for (let n = 1; n <= 50; n++) {
    const present = !!D.races[BL.raceKey('SD', n)];
    assert.equal(present, BL.senateUpThisCycle(n, year), 'SD ' + n + ' presence matches the cycle');
  }
  // Every ticket half has a running mate in the data.
  for (const p of BL.ticketPairs(D.races['STATEWIDE-GOV'], D.races['STATEWIDE-LTGOV'])) {
    assert.ok(p.gov && p.ltg, 'ticket complete: ' + ((p.gov || p.ltg).name));
  }
});
