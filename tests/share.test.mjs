// Round-trip tests for shared quiz links. The codec lives in index.html between /* <share-codec> */ and /* </share-codec> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <share-codec> */"), end = html.indexOf("/* </share-codec> */");
assert.ok(start > 0 && end > start, "share codec markers not found in index.html");
const { shareEncode, shareDecode, SHARE_MAX } = new Function(html.slice(start, end) + "\nreturn { shareEncode, shareDecode, SHARE_MAX };")();

test("ids and name round-trip exactly", () => {
  const ids = ["apc-1", "methods-1-1-12", "a_b-3"];
  assert.deepEqual(shareDecode(shareEncode(ids, "Fish & chips")), { ids, name: "Fish & chips" });
  assert.deepEqual(shareDecode(shareEncode(ids)), { ids, name: "" });
});

test("capped at 30, deduplicated, long names trimmed", () => {
  const ids = Array.from({ length: 40 }, (_, i) => "methods-1-1-" + i);
  assert.equal(shareDecode(shareEncode(ids)).ids.length, SHARE_MAX);
  assert.ok(shareEncode(ids).length < 1500);
  assert.equal(shareDecode(shareEncode(["a-1", "a-1"])).ids.length, 1);
  assert.equal(shareDecode(shareEncode(["a-1"], "x".repeat(100))).name.length, 40);
});

test("invalid links decode to null", () => {
  for (const bad of ["share=", "share=a..b", "share=<script>", "nope", "share=" + Array(31).fill("a-1").join(".")])
    assert.equal(shareDecode(bad), null, bad);
});
