// Unit tests for auto-marking of single-number answers. Run: node --test tests/*.test.mjs
// The functions live in index.html between /* <automark> */ and /* </automark> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <automark> */"), end = html.indexOf("/* </automark> */");
assert.ok(start > 0 && end > start, "automark markers not found in index.html");
const { parseAnswer, checkAnswer } = new Function(html.slice(start, end) + "\nreturn { parseAnswer, checkAnswer };")();
const x = s => parseAnswer(s)?.x;

test("parses plain, signed and unicode-minus numbers", () => {
  assert.equal(x("2.4"), 2.4); assert.equal(x("-3"), -3); assert.equal(x("−3"), -3); assert.equal(x("  7  "), 7); assert.equal(x(".5"), 0.5);
});
test("parses fractions", () => {
  assert.equal(x("2/3"), 2 / 3); assert.equal(x("-1 / 4"), -0.25); assert.equal(x("1/0"), undefined);
});
test("parses scientific notation", () => {
  for (const s of ["3.2e-4", "3.2×10^-4", "3.2 x 10^-4", "3.2*10^-4", "3.2 × 10^−4", "3.2×10^(-4)"]) assert.ok(Math.abs(x(s) - 3.2e-4) < 1e-15, s);
  assert.equal(x("5×10^3"), 5000);
});
test("parses money and percentages", () => {
  assert.equal(x("$9,751.89"), 9751.89); assert.equal(x("9751.89"), 9751.89); assert.equal(x("93.3%"), 93.3); assert.equal(x("-$5"), -5);
});
test("rejects things that are not one number", () => {
  for (const s of ["", "abc", "two", "2.4 3", "1,2", "2..4", "--3", "1e999", "m/s"]) assert.equal(parseAnswer(s), null, s);
});
test("keeps trailing text as the unit", () => {
  assert.equal(parseAnswer("2.4 m s^-2").unit, "m s^-2"); assert.equal(parseAnswer("2.4").unit, "");
});

const e = { v: 2.4, tol: 0.05, unit: "m s^-2", units: ["m s^-2", "m s⁻²", "m/s^2"] };
test("tolerance edges are inclusive", () => {
  for (const s of ["2.35", "2.45", "2.4"]) assert.equal(checkAnswer(s, e).ok, true, s);
  for (const s of ["2.34", "2.46", "-2.4"]) assert.equal(checkAnswer(s, e).ok, false, s);
  assert.equal(checkAnswer("0.7251", { v: 0.7251, tol: 5e-5 }).ok, true); assert.equal(checkAnswer("0.725", { v: 0.7251, tol: 5e-5 }).ok, false);
  assert.equal(checkAnswer("93.3%", { v: 93.3, tol: 0.05, unit: "%" }).ok, true);
  assert.equal(checkAnswer("$9,751.89", { v: 9751.89, tol: 0.005, unit: "$" }).ok, true);
});
test("unit notes never change the mark", () => {
  assert.equal(checkAnswer("2.4 m/s^2", e).note, ""); assert.equal(checkAnswer("2.4 m s⁻²", e).note, ""); assert.equal(checkAnswer("2.4", e).note, "");
  const r = checkAnswer("2.4 kg", e); assert.equal(r.ok, true); assert.equal(r.note, "Check your units: expected m s⁻²");
  assert.equal(checkAnswer("2.4 dollars", { v: 2.4, tol: 0.05, unit: "$" }).note, "");
  assert.equal(checkAnswer("abc", e), null);
});
