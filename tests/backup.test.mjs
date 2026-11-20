// Unit tests for the backup file check. Run: node --test tests/*.test.mjs
// The check lives in index.html between /* <backup-check> */ and /* </backup-check> */, so the site stays one file;
// these tests load that block on its own.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <backup-check> */"), end = html.indexOf("/* </backup-check> */");
assert.ok(start > 0 && end > start, "backup-check markers not found in index.html");
const backupCheck = new Function(html.slice(start, end) + "\nreturn backupCheck;")();

const good = { app: "helix-revise", version: 1, exported: "2026-11-20T01:02:03.000Z", data: { "helix-progress-v2": "{}", "helix-theme": "dark" } };
const text = o => typeof o === "string" ? o : JSON.stringify(o);

test("a backup written by the download button is accepted, with its data unchanged", () => {
  const r = backupCheck(100, text(good));
  assert.equal(r.error, undefined);
  assert.deepEqual(r.data, good.data);
  assert.equal(r.exported, good.exported);
});

test("an empty data object is accepted", () => {
  assert.equal(backupCheck(10, text({ ...good, data: {} })).error, undefined);
});

test("files that are not JSON are rejected", () => {
  assert.match(backupCheck(10, "not json {").error, /not a Helix Revise backup/);
  assert.match(backupCheck(0, "").error, /not a Helix Revise backup/);
});

test("JSON of the wrong shape is rejected", () => {
  for (const o of [null, 5, "x", [], { ...good, app: "other" }, { app: "helix-revise" }, { ...good, data: null }, { ...good, data: [] }, { ...good, data: "x" }]) {
    assert.match(backupCheck(10, text(o)).error, /not a Helix Revise backup/, text(o));
  }
});

test("keys without the helix- prefix are rejected", () => {
  assert.match(backupCheck(10, text({ ...good, data: { "other-key": "1" } })).error, /does not recognise/);
  assert.match(backupCheck(10, text({ ...good, data: { "helix-ok": "1", "x": "2" } })).error, /does not recognise/);
});

test("non-string values are rejected", () => {
  for (const v of [1, null, {}, [], true]) assert.match(backupCheck(10, text({ ...good, data: { "helix-a": v } })).error, /does not recognise/, String(v));
});

test("files of 5 MB or more are rejected before the content is looked at", () => {
  assert.match(backupCheck(5 * 1024 * 1024, text(good)).error, /too big/);
  assert.equal(backupCheck(5 * 1024 * 1024 - 1, text(good)).error, undefined);
});

test("a missing exported date gives an empty string, not a failure", () => {
  assert.equal(backupCheck(10, text({ ...good, exported: undefined })).exported, "");
});
