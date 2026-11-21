// The data files: data/index.json (catalogue) and data/<subjectId>.json must agree with each other.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = f => JSON.parse(readFileSync(new URL("../data/" + f, import.meta.url), "utf8"));
const cat = read("index.json");
const files = Object.fromEntries(cat.S.map(s => [s[0], read(s[0] + ".json")]));
const qid = q => Array.isArray(q) ? q[0] : q.id;
const marks = q => Array.isArray(q) ? 1 : q.pieces.filter(p => p.kind === "part").reduce((a, p) => a + p.marks, 0);

test("every subtopic in the catalogue has a question list in its own subject file, and counts and marks match", () => {
  for (const s of cat.S) for (const t of s[4]) for (const [slug] of t[2]) {
    const list = files[s[0]].Q[slug];
    assert.ok(Array.isArray(list), `${slug} missing from ${s[0]}.json`);
    assert.deepEqual(cat.N[slug], [list.length, list.reduce((a, q) => a + marks(q), 0)], `N for ${slug}`);
  }
});

test("a subject file holds no subtopic from another subject, and every slug is listed once", () => {
  const seen = new Set();
  for (const s of cat.S) {
    const own = new Set(s[4].flatMap(t => t[2].map(x => x[0])));
    for (const slug of Object.keys(files[s[0]].Q)) { assert.ok(own.has(slug), `${slug} is in ${s[0]}.json but not in its catalogue entry`); assert.ok(!seen.has(slug)); seen.add(slug); }
  }
  assert.equal(seen.size, Object.keys(cat.N).length);
});

test("every T and DIFF id is a question (or exam-style question) in the same file; question ids are unique", () => {
  const all = new Set();
  for (const [sid, f] of Object.entries(files)) {
    const ids = new Set([...Object.values(f.Q).flat().map(qid), ...(f.X || []).map(q => q.id)]);
    for (const i of ids) { assert.ok(!all.has(i), `duplicate id ${i}`); all.add(i); }
    for (const i of Object.keys(f.T)) assert.ok(ids.has(i), `T ${i} not in ${sid}.json`);
    for (const i of Object.keys(f.DIFF || {})) assert.ok(ids.has(i), `DIFF ${i} not in ${sid}.json`);
  }
  for (const i of cat.C) assert.ok(all.has(i), `challenge id ${i} has no question`);
});

test("exam-style stubs in the catalogue match the exam-style questions", () => {
  for (const [sid, f] of Object.entries(files)) {
    const stubs = cat.X[sid] || [];
    assert.equal(stubs.length, (f.X || []).length, sid);
    (f.X || []).forEach((q, k) => {
      const parts = q.pieces.filter(p => p.kind === "part");
      assert.deepEqual(stubs[k], [q.id, q.title || "Multi-part question", q.tech || "", marks(q), parts.length, [...new Set(parts.map(p => p.topic))]]);
    });
  }
});

test("the id-stem map sends every question id to the subject file that holds it", () => {
  cat.S.forEach((s, idx) => {
    const f = files[s[0]];
    for (const i of [...Object.values(f.Q).flat().map(qid), ...(f.X || []).map(q => q.id)]) assert.equal(cat.P[i.replace(/\d+$/, "")], idx, i);
  });
});

test("the catalogue's rating count matches the ratings in the files", () => {
  assert.equal(cat.D, Object.values(files).reduce((a, f) => a + Object.keys(f.DIFF || {}).length, 0));
});
