// Routing tests for sw.js (the block between /* <sw-routing> */ markers). Run: node --test tests/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const js = readFileSync(new URL("../sw.js", import.meta.url), "utf8");
const a = js.indexOf("/* <sw-routing> */"), b = js.indexOf("/* </sw-routing> */");
assert.ok(a > 0 && b > a, "sw-routing markers not found in sw.js");
const strategyFor = new Function(js.slice(a, b) + "\nreturn strategyFor;")();
const O = "https://x.github.io", S = (p, m = "GET", mode = "cors") => strategyFor(O + p, m, mode, O);

test("pages are network-first, data and content stale-while-revalidate", () => {
  assert.equal(S("/helix-revise/", "GET", "navigate"), "network-first");
  assert.equal(S("/helix-revise/index.html"), "network-first");
  assert.equal(S("/helix-revise/data/methods.json"), "swr");
  assert.equal(S("/helix-revise/content/notes/methods.json"), "swr");
  assert.equal(S("/helix-revise/icons/icon-192.png"), "cache-first");
});

test("fonts and pinned KaTeX are cache-first; other hosts and non-GET are not handled", () => {
  assert.equal(strategyFor("https://fonts.gstatic.com/s/a.woff2", "GET", "cors", O), "cache-first");
  assert.equal(strategyFor("https://fonts.googleapis.com/css2?family=Figtree", "GET", "no-cors", O), "cache-first");
  assert.equal(strategyFor("https://cdn.jsdelivr.net/npm/katex@0.19.1/dist/katex.min.js", "GET", "cors", O), "cache-first");
  assert.equal(strategyFor("https://cdn.jsdelivr.net/npm/other@1/x.js", "GET", "cors", O), null);
  assert.equal(strategyFor("https://example.com/data/a.json", "GET", "cors", O), null);
  assert.equal(S("/helix-revise/data/methods.json", "POST"), null);
  assert.equal(S("/helix-revise/admin/x.json"), null);
});
