// Unit tests for plain-text maths formatting (powers and subscripts). Run: node --test tests/*.test.mjs
// The formatter lives in index.html between /* <maths-text> */ and /* </maths-text> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <maths-text> */"), end = html.indexOf("/* </maths-text> */");
assert.ok(start > 0 && end > start, "maths-text markers not found in index.html");
const supsub = new Function(html.slice(start, end) + "\nreturn supsub;")();
const shown = s => supsub(s).replace(/<span class="sr-only">[^<]*<\/span>/g, ""); // what is seen, without screen-reader words

test("bracketed powers become superscripts without their brackets", () => {
  assert.equal(shown("Solve 2e^(3x) − 5 = 9 for x"), "Solve 2e<sup>3x</sup> − 5 = 9 for x");
  assert.equal(shown("(x² + 1)^(−1/2) × 2x"), "(x² + 1)<sup>−1/2</sup> × 2x");
  assert.equal(shown("∫₀^(π/2) cos(x) dx"), "∫₀<sup>π/2</sup> cos(x) dx");
});

test("single-token powers: a number, a letter or a symbol", () => {
  assert.equal(shown("y = e^x/2."), "y = e<sup>x</sup>/2.");
  assert.equal(shown("1.6 × 10^-19 C"), "1.6 × 10<sup>−19</sup> C");
  assert.equal(shown("x^2."), "x<sup>2</sup>.");
  assert.equal(shown("e^π and 2^0.5"), "e<sup>π</sup> and 2<sup>0.5</sup>");
});

test("nested powers", () => {
  assert.equal(shown("e^(x^2)"), "e<sup>x<sup>2</sup></sup>");
});

test("explicit subscripts, with 'base' for logarithms", () => {
  assert.equal(shown("y = log_{e}(x)"), "y = log<sub>e</sub>(x)");
  assert.equal(shown("V_{RMS} = V_{peak}/√2"), "V<sub>RMS</sub> = V<sub>peak</sub>/√2");
  assert.match(supsub("log_{e}(x)"), /log<span class="sr-only"> base <\/span><sub>e<\/sub>/);
  assert.match(supsub("e^x"), /e<span class="sr-only"> to the power of <\/span><sup>x<\/sup>/);
});

test("underscores that are not subscripts are left alone", () => {
  assert.equal(shown("phenotype A_bb and A_B_"), "phenotype A_bb and A_B_"); // genetics: any allele
  assert.equal(shown("fragments such as 'ch_ir'"), "fragments such as 'ch_ir'"); // a missing letter
  assert.equal(shown("我想了半天也没想___。"), "我想了半天也没想___。"); // a blank
});

test("a caret with nothing to raise is left alone", () => {
  assert.equal(shown("a ^ b"), "a ^ b");
  assert.equal(shown("^x at the start"), "^x at the start");
});
