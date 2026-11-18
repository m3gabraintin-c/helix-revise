// Unit tests for the topic mastery engine. Run: node --test tests/
// The engine lives in index.html between /* <mastery-engine> */ and /* </mastery-engine> */, so the site stays one file;
// these tests load that block on its own.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <mastery-engine> */"), end = html.indexOf("/* </mastery-engine> */");
assert.ok(start > 0 && end > start, "engine block markers not found in index.html");
const E = new Function(html.slice(start, end) + "\nreturn MasteryEngine;")();

const DAY = 86400, NOW = 1_800_000_000;
// One attempt. d = days ago; defaults: a 1-mark question, right, 60 s against a 60 s estimate, no rating.
const at = (q, got, d = 0, extra = {}) => ({ t: NOW - d * DAY, day: Math.floor((NOW - d * DAY) / DAY), q, part: -1, got, of: 1, secs: 60, est: 60, p: null, type: "recall", conf: null, ...extra });
const run = (atts, over) => E.subtopic(atts, NOW, over);

test("no attempts: not enough data, no level", () => {
  const r = run([]);
  assert.equal(r.sufficient, false);
  assert.equal(r.level, null);
  assert.equal(E.show(r), null);
  assert.equal(r.P, 50); // the prior, not a claim about the student
});

test("one correct answer is not proof of mastery", () => {
  const r = run([at("a", 1)]);
  assert.equal(r.sufficient, false);
  assert.equal(r.level, null);
  assert.ok(r.P < 70, `P should stay near the prior, got ${r.P}`);
});

test("Bayesian smoothing pulls small samples towards 50%", () => {
  const r3 = run([at("a", 1), at("b", 1), at("c", 1)]);
  // (3 + 0.5 x 5) / (3 + 5) = 68.75%
  assert.ok(Math.abs(r3.P - 68.75) < 0.01, `got ${r3.P}`);
  const r20 = run(Array.from({ length: 20 }, (_, i) => at("q" + i, 1)));
  assert.ok(r20.P > 85 && r20.P < 100, `more evidence should move it further, got ${r20.P}`);
});

test("repeating the same question cannot inflate mastery", () => {
  const once = run([at("a", 1), at("b", 1), at("c", 0)]);
  const drilled = run([at("a", 1), at("b", 1), at("c", 0), ...Array.from({ length: 30 }, () => at("a", 1))]);
  assert.equal(drilled.nQuestions, 3);
  assert.ok(drilled.P - once.P < 6, `30 repeats moved P by ${drilled.P - once.P}`);
  // Still only three different questions, so it is not rated more reliably either.
  assert.equal(drilled.reliability, once.reliability);
});

test("recent and historical accuracy are reported separately; recent work weighs more in P", () => {
  const old = Array.from({ length: 6 }, (_, i) => at("o" + i, 0, 120));
  const fresh = Array.from({ length: 6 }, (_, i) => at("n" + i, 1, 1));
  const r = run([...old, ...fresh]);
  assert.equal(r.historical, 0.5);
  assert.equal(r.recent, 1);
  assert.ok(r.P > 60, `recent success should outweigh old failures, got ${r.P}`);
});

test("difficulty: the same accuracy on harder questions gives a higher D", () => {
  const mk = p => Array.from({ length: 8 }, (_, i) => at("q" + i, i < 4 ? 1 : 0, 0, { p }));
  const hard = run(mk(0.3)), easy = run(mk(0.9));
  assert.ok(Math.abs(hard.P - easy.P) < 1e-9);
  assert.ok(hard.D > hard.P && easy.D < easy.P, `hard D ${hard.D}, easy D ${easy.D}`);
  assert.equal(run([at("a", 1), at("b", 1), at("c", 1)]).D, null); // no ratings: no D (M uses P in its place)
});

test("delayed retention is tracked apart from immediate accuracy", () => {
  // Learned on day 10 (all right), then mostly forgotten when tested a week later.
  const r = run([at("a", 1, 10), at("b", 1, 10), at("c", 1, 10), at("d", 0, 3), at("e", 0, 3), at("f", 1, 3)]);
  assert.equal(r.nDelayed, 1); // only the first attempt after the gap counts as a delayed attempt
  assert.ok(r.R != null);
  const same = run([at("a", 1, 0), at("b", 1, 0), at("c", 1, 0)]);
  assert.equal(same.R, null); // no gap, no retention evidence
  assert.equal(same.nDelayed, 0);
});

test("retention gap is configurable", () => {
  const atts = [at("a", 1, 2), at("b", 1, 2), at("c", 1, 0)];
  assert.equal(run(atts).nDelayed, 0);
  assert.equal(run(atts, { retentionGapDays: 1 }).nDelayed, 1);
});

test("consistency counts good practice days, and needs at least two days", () => {
  const steady = run([0, 1, 2, 3].flatMap(d => [at("a" + d, 1, d * 4), at("b" + d, 1, d * 4)]));
  const patchy = run([0, 1, 2, 3].flatMap(d => [at("a" + d, d % 2, d * 4), at("b" + d, d % 2, d * 4)]));
  assert.ok(steady.K > patchy.K, `steady ${steady.K} vs patchy ${patchy.K}`);
  assert.equal(run([at("a", 1), at("b", 1), at("c", 1)]).K, null);
});

test("a guessed correct answer counts as half right", () => {
  const sure = run([at("a", 1, 0, { conf: 2 }), at("b", 1, 0, { conf: 2 }), at("c", 1, 0, { conf: 2 })]);
  const guessed = run([at("a", 1, 0, { conf: 0 }), at("b", 1, 0, { conf: 0 }), at("c", 1, 0, { conf: 0 })]);
  assert.ok(guessed.P < sure.P);
  assert.ok(Math.abs(guessed.historical - 0.5) < 1e-9);
});

test("M is the weighted sum of the available components", () => {
  const atts = [0, 1, 2, 3].flatMap(d => [at("a" + d, 1, d * 5, { p: 0.5 }), at("b" + d, d ? 1 : 0, d * 5, { p: 0.5 })]);
  const r = run(atts);
  const w = E.config().weights;
  const expect = w.P * r.P + w.R * r.R + w.D * r.D + w.K * r.K;
  assert.ok(Math.abs(r.M - expect) < 1e-9);
  assert.deepEqual(r.used.sort(), ["D", "K", "P", "R"]);
});

test("weights are configurable and rescaled to add up to 1", () => {
  const c = E.config({ weights: { P: 2, R: 1, D: 1, K: 0 } });
  assert.ok(Math.abs(Object.values(c.weights).reduce((a, b) => a + b, 0) - 1) < 1e-12);
  assert.equal(c.weights.P, 0.5);
  const atts = [0, 1, 2, 3].flatMap(d => [at("a" + d, 1, d * 5), at("b" + d, 0, d * 5)]);
  const onlyP = run(atts, { weights: { P: 1, R: 0, D: 0, K: 0 } });
  assert.ok(Math.abs(onlyP.M - onlyP.P) < 1e-9);
  assert.equal(E.DEFAULTS.weights.P, 0.45); // the defaults are not changed by overrides
});

test("missing components are left out, not counted as zero", () => {
  const r = run([at("a", 1), at("b", 1), at("c", 1), at("d", 1)]); // no gap, one day, no ratings: only P
  assert.deepEqual(r.used, ["P"]);
  assert.ok(Math.abs(r.M - r.P) < 1e-9);
});

test("Mastered needs retention and reliability; otherwise it is capped at Secure", () => {
  const sameDay = run(Array.from({ length: 30 }, (_, i) => at("q" + i, 1)));
  assert.ok(sameDay.M >= 80);
  assert.equal(sameDay.level, "Secure");
  assert.equal(sameDay.capped, true);
  const spaced = run([0, 1, 2, 3, 4, 5].flatMap(d => [0, 1, 2].map(i => at(`q${d}-${i}`, 1, d * 5))));
  assert.equal(spaced.level, "Mastered");
  assert.ok(["moderate", "good"].includes(spaced.reliability));
});

test("scores are shown rounded to 5 with a range, never as precise numbers", () => {
  const r = run(Array.from({ length: 8 }, (_, i) => at("q" + i, i % 3 ? 1 : 0)));
  const s = E.show(r);
  assert.equal(s.value % 5, 0);
  assert.ok(s.lo <= s.value && s.value <= s.hi && s.hi > s.lo);
});

test("recalculation: a new attempt changes the result, and inputs are not modified", () => {
  const atts = [at("a", 1), at("b", 0), at("c", 1)];
  const copy = JSON.stringify(atts);
  const before = run(atts), after = run([...atts, at("d", 0)]);
  assert.notEqual(before.P, after.P);
  assert.equal(JSON.stringify(atts), copy);
});

test("multi-mark parts count by marks, capped so one long question cannot dominate", () => {
  const big = { ...at("big", 0), of: 10 }, smalls = [at("a", 1), at("b", 1), at("c", 1)];
  const r = run([big, ...smalls]);
  // The 10-mark part counts as 3 marks of evidence: (3 + 2.5) / (6 + 5) = 50%.
  assert.ok(Math.abs(r.P - 50) < 0.01, `got ${r.P}`);
});

test("question types and pace are tracked", () => {
  const r = run([at("a", 1, 0, { type: "calc", secs: 50 }), at("b", 0, 0, { type: "calc", secs: 200 }), at("c", 1, 0, { type: "concept", secs: 0 })]);
  assert.deepEqual(r.types.calc, { got: 1, of: 2, n: 2 });
  assert.equal(r.types.concept.n, 1);
  assert.equal(r.timed, 2);
  assert.equal(r.pace, 0.5);
});

test("group mastery uses rated subtopics only, weighted by evidence", () => {
  const a = run(Array.from({ length: 6 }, (_, i) => at("a" + i, 1))), b = run([at("x", 0)]);
  const g = E.group([a, b]);
  assert.equal(g.rated, 1);
  assert.equal(g.total, 2);
  assert.ok(Math.abs(g.M - a.M) < 1e-9);
  assert.equal(E.group([b]).M, null);
});

test("exam readiness is separate from mastery: unrated examinable subtopics count as 0", () => {
  const good = run(Array.from({ length: 8 }, (_, i) => at("g" + i, 1, 0, { secs: 30 })));
  const rd = E.readiness([{ weight: 3, result: good }, { weight: 1, result: null }]);
  assert.ok(Math.abs(rd.base - good.M * 0.75) < 1e-9);
  assert.equal(rd.coveredWeight, 0.75);
  assert.equal(rd.pace, 1);
  assert.ok(rd.score < good.M);
  assert.equal(E.readiness([]), null);
});

test("snapshots: one per day, replaced on the same day, oldest dropped", () => {
  let s = [];
  s = E.snapshot(s, "2026-11-01", { a: 1 });
  s = E.snapshot(s, "2026-11-02", { a: 2 });
  s = E.snapshot(s, "2026-11-02", { a: 3 });
  assert.deepEqual(s, [["2026-11-01", { a: 1 }], ["2026-11-02", { a: 3 }]]);
  for (let d = 3; d <= 9; d++) s = E.snapshot(s, `2026-11-0${d}`, { a: d }, 5);
  assert.equal(s.length, 5);
  assert.equal(s[0][0], "2026-11-05");
});
