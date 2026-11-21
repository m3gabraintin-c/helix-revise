// Tests for the exam calendar file. The builder lives in index.html between /* <ics> */ and /* </ics> */.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const start = html.indexOf("/* <ics> */"), end = html.indexOf("/* </ics> */");
assert.ok(start > 0 && end > start, "ics markers not found in index.html");
const buildIcs = new Function(html.slice(start, end) + "\nreturn buildIcs;")();

const now = new Date(2026, 4, 10, 9, 30); // Sunday 10 May 2026, local time
const unfold = s => s.replace(/\r\n /g, "");

test("CRLF endings, version, prodid, UTC stamp", () => {
  const s = buildIcs([{ id: "methods", name: "Methods", date: "2026-06-12" }], now);
  assert.ok(s.startsWith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:") && s.endsWith("END:VCALENDAR\r\n"));
  assert.equal(s.replace(/\r\n/g, "").includes("\n"), false);
  assert.match(s, /DTSTAMP:\d{8}T\d{6}Z\r\n/);
  assert.ok(s.includes("UID:exam-methods-2026-06-12@helix-revise\r\n"));
});

test("all-day exam event ends the next day, even across a month end", () => {
  const s = buildIcs([{ id: "a", name: "A", date: "2026-06-30" }], now);
  assert.ok(s.includes("DTSTART;VALUE=DATE:20260630\r\nDTEND;VALUE=DATE:20260701\r\n"));
  assert.ok(s.includes("SUMMARY:A exam\r\n"));
});

test("weekly reminder starts tomorrow and stops the day before the exam", () => {
  const s = buildIcs([{ id: "m", name: "Methods", date: "2026-06-12" }], now);
  assert.ok(s.includes("DTSTART;VALUE=DATE:20260511\r\n"));
  assert.ok(s.includes("RRULE:FREQ=WEEKLY;UNTIL=20260611\r\n"));
  assert.ok(s.includes("SUMMARY:Revise Methods: this week's sprints\r\n"));
});

test("an exam tomorrow gets no reminder; one today still gets its event", () => {
  assert.equal(buildIcs([{ id: "m", name: "M", date: "2026-05-11" }], now).includes("RRULE"), false);
  assert.ok(buildIcs([{ id: "m", name: "M", date: "2026-05-10" }], now).includes("DTSTART;VALUE=DATE:20260510"));
});

test("TEXT is escaped", () => {
  const s = buildIcs([{ id: "x", name: "A, B; C\\D\nE", date: "2026-06-12" }], now);
  assert.ok(s.includes("SUMMARY:A\\, B\\; C\\\\D\\nE exam\r\n"));
});

test("long lines fold at 75 octets without splitting a multi-byte character", () => {
  const s = buildIcs([{ id: "x", name: "é€".repeat(60), date: "2026-06-12" }], now);
  const lines = s.split("\r\n");
  for (const l of lines) assert.ok(Buffer.byteLength(l) <= 75, l);
  assert.ok(lines.some(l => l.startsWith(" ")));
  assert.ok(unfold(s).includes("SUMMARY:" + "é€".repeat(60) + " exam"));
  assert.equal(s.includes("�"), false);
});

test("past exams are skipped", () => {
  const s = buildIcs([{ id: "old", name: "Old", date: "2026-05-09" }, { id: "new", name: "New", date: "2026-06-12" }], now);
  assert.equal(s.includes("exam-old"), false);
  assert.ok(s.includes("exam-new"));
});

test("an empty list gives a valid empty calendar (the page hides the button instead)", () => {
  const s = buildIcs([], now);
  assert.equal(s, "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Helix Revise//Exam dates//EN\r\nCALSCALE:GREGORIAN\r\nEND:VCALENDAR\r\n");
});
