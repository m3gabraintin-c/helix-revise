// Tests for the read-aloud maths converter (the Listen buttons). The converter lives in index.html between /* <read-aloud> */ and /* </read-aloud> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <read-aloud> */"), end = html.indexOf("/* </read-aloud> */");
assert.ok(start > 0 && end > start, "read-aloud markers not found in index.html");
const texToSpeech = new Function(html.slice(start, end) + "\nreturn texToSpeech;")();

test("fractions read as 'over', including nested roots", () => {
  assert.equal(texToSpeech("\\frac{a}{b}"), "a over b");
  assert.equal(texToSpeech("\\frac{\\sqrt{x}}{2}"), "square root of x over 2");
});

test("powers: squared, cubed, and 'to the power' for anything else", () => {
  assert.equal(texToSpeech("x^2"), "x squared");
  assert.equal(texToSpeech("x^{3}"), "x cubed");
  assert.equal(texToSpeech("x^{n}"), "x to the power n");
  assert.equal(texToSpeech("e^{2x+1}"), "e to the power 2x+1");
});

test("roots, times, divided by and pi", () => {
  assert.equal(texToSpeech("\\sqrt{x}"), "square root of x");
  assert.equal(texToSpeech("2 \\times 3 \\div 6 = \\pi"), "2 times 3 divided by 6 = pi");
});

test("inequalities", () => {
  assert.equal(texToSpeech("x \\le 2"), "x less than or equal to 2");
  assert.equal(texToSpeech("x \\ge 1"), "x greater than or equal to 1");
  assert.equal(texToSpeech("x \\ne 0"), "x not equal to 0");
});

test("probability and trig words", () => {
  assert.equal(texToSpeech("\\Pr(X \\le 2)"), "probability (X less than or equal to 2)");
  assert.equal(texToSpeech("\\sin x + \\cos x + \\tan x"), "sine x + cosine x + tangent x");
});

test("integrals with limits", () => {
  assert.equal(texToSpeech("\\int_a^b f(x)\\,dx"), "the integral from a to b of f(x) dx");
});

test("subscripts and \\text", () => {
  assert.equal(texToSpeech("x_{n} = \\text{m/s}"), "x sub n = m/s");
  assert.equal(texToSpeech("V_{RMS}"), "V sub RMS");
});

test("unknown commands lose their backslashes and braces", () => {
  assert.equal(texToSpeech("\\left( \\alpha \\right)"), "( alpha )");
  assert.equal(texToSpeech("{a}{b}"), "ab");
});
