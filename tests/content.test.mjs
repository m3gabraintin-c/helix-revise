// Glossary matching. The helpers live in index.html between /* <content-helpers> */ and /* </content-helpers> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <content-helpers> */"), end = html.indexOf("/* </content-helpers> */");
assert.ok(start > 0 && end > start, "content helper markers not found in index.html");
const { glossBuild, glossFind } = new Function(html.slice(start, end) + "\nreturn { glossBuild, glossFind };")();

const terms = [
  { term: "acid", aliases: ["acids"], def: "A" },
  { term: "strong acid", aliases: [], def: "SA" },
  { term: "pH", aliases: [], def: "P" },
];
const find = (text, max = 6) => glossFind(text, glossBuild(terms), new Set(), max).map(h => [text.slice(h.start, h.end), h.def]);

test("longest term wins, whole words only, case-insensitive", () => {
  assert.deepEqual(find("A Strong Acid is not a base"), [["Strong Acid", "SA"]]);
  assert.deepEqual(find("a pharmacy of acidic things"), []);
});

test("only the first occurrence of each term (aliases count as the same term)", () => {
  assert.deepEqual(find("acid, acids and acid again"), [["acid", "A"]]);
});

test("capped at max terms", () => {
  assert.equal(find("acid pH", 1).length, 1);
});
