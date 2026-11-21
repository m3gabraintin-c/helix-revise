// Unit tests for the daily-goal streak. Run: node --test tests/*.test.mjs
// The function lives in index.html between /* <streak> */ and /* </streak> */; these tests load that block on its own.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <streak> */"), end = html.indexOf("/* </streak> */");
assert.ok(start > 0 && end > start, "streak markers not found in index.html");
const streakOf = new Function(html.slice(start, end) + "\nreturn streakOf;")();

const T = 100; // "today" as a day number; counts are { day: questions answered }
const days = (list, n = 10) => Object.fromEntries(list.map(d => [d, n]));

test("no history: no streak, goal not met", () => {
  assert.deepEqual(streakOf({}, 10, T), { streak: 0, met: false, today: 0, free: false });
});

test("goal met 3 days running, including today", () => {
  const r = streakOf(days([T - 2, T - 1, T]), 10, T);
  assert.equal(r.streak, 3); assert.equal(r.met, true); assert.equal(r.free, false);
});

test("today not yet met: the streak still shows up to yesterday", () => {
  const r = streakOf({ ...days([T - 3, T - 2, T - 1]), [T]: 4 }, 10, T);
  assert.equal(r.streak, 3); assert.equal(r.met, false); assert.equal(r.today, 4);
});

test("one missed day is forgiven and the free day is shown as used", () => {
  const r = streakOf(days([T - 4, T - 3, T - 1, T]), 10, T); // missed T - 2
  assert.equal(r.streak, 4); assert.equal(r.free, true);
});

test("answers below the goal count as a miss", () => {
  const r = streakOf({ ...days([T - 3, T - 1, T]), [T - 2]: 9 }, 10, T); // 3 days met; the forgiven day itself is not counted
  assert.equal(r.streak, 3); assert.equal(r.free, true);
});

test("two misses within 7 days end the streak", () => {
  const r = streakOf(days([T - 6, T - 5, T - 3, T]), 10, T); // missed T - 4 and T - 2 and T - 1
  assert.equal(r.streak, 1);
  assert.equal(streakOf(days([T - 7, T - 5, T - 4, T - 2, T - 1]), 10, T).streak, 2); // missed T - 6 (forgiven) and T - 3 (ends it): T - 2, T - 1 rebuild
});

test("a miss a week after the last one is forgiven again", () => {
  const r = streakOf(days([T - 9, T - 7, T - 6, T - 5, T - 4, T - 3, T - 2, T - 1]), 10, T); // missed T - 8 and T - 0 pending
  assert.equal(r.streak, 8); assert.equal(r.free, false);
});

test("a gap longer than the streak can be forgiven restarts from zero", () => {
  const r = streakOf(days([T - 9, T - 1]), 10, T); // missed T - 8 (forgiven), then T - 7 on: second miss
  assert.equal(r.streak, 1);
});
