// Unit tests for the exam plan maths. Run: node --test tests/*.test.mjs
// The maths lives in index.html between /* <exam-plan> */ and /* </exam-plan> */, so the site stays one file;
// these tests load that block on its own.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <exam-plan> */"), end = html.indexOf("/* </exam-plan> */");
assert.ok(start > 0 && end > start, "exam-plan markers not found in index.html");
const planMaths = new Function(html.slice(start, end) + "\nreturn planMaths;")();

test("weeks left round up, with a minimum of 1", () => {
  assert.equal(planMaths(23, 10).weeks, 4);
  assert.equal(planMaths(28, 10).weeks, 4);
  assert.equal(planMaths(29, 10).weeks, 5);
  assert.equal(planMaths(0, 10).weeks, 1);
});

test("the target spreads the gap over the weeks left, rounded up", () => {
  assert.equal(planMaths(23, 10).target, 3); // ceil(10 / 4)
  assert.equal(planMaths(23, 0).target, 0);
});

test("the target is capped at 6 sprints", () => {
  assert.equal(planMaths(14, 100).target, 6); // 100 / 2 = 50, capped
  assert.equal(planMaths(14, 12).target, 6);
});

test("the final 7 days are review, with no sprint target", () => {
  for (const d of [0, 3, 7]) { const p = planMaths(d, 40); assert.equal(p.review, true); assert.equal(p.target, 0); }
  assert.equal(planMaths(8, 40).review, false);
});

test("a past exam is finished and has no plan", () => {
  assert.deepEqual(planMaths(-1, 10), { finished: true });
});
