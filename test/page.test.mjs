// Regression tests for the public page: the TAI calculation window, the honest
// device-clock labels and the freshness line (audit T7). Run with `node --test`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { clockReadings } from "../public/clock.mjs";

const html = readFileSync(new URL("../public/index.html", import.meta.url), "utf8");
const script = readFileSync(new URL("../public/clock.mjs", import.meta.url), "utf8");

function offsetData() {
  const tag = html.match(/<p[^>]*id="tai-offset"[^>]*>/s);
  assert.ok(tag, "index.html has the #tai-offset element");
  const attr = (name) => tag[0].match(new RegExp(`data-${name}="([^"]+)"`))?.[1];
  return { seconds: Number(attr("seconds")), start: attr("start"), end: attr("end") };
}

test("TAI is UTC plus the offset inside the window and absent outside it", () => {
  const { seconds, start, end } = offsetData();
  const from = Date.parse(start);
  const until = Date.parse(end);
  const inside = until - 1000;
  assert.equal(clockReadings(inside, seconds, from, until).tai,
    new Date(inside + seconds * 1000).toISOString());
  assert.equal(clockReadings(until, seconds, from, until).tai, null);
  assert.equal(clockReadings(from - 1, seconds, from, until).tai, null);
  assert.equal(clockReadings(inside, seconds, from, until).utc, new Date(inside).toISOString());
});

test("the page's offset matches the stated TAI − UTC and the leap-second comment", () => {
  const { seconds, start, end } = offsetData();
  assert.equal(seconds, 37);
  assert.match(html, /\+37 <span>s<\/span>/);
  assert.equal(start, "2017-01-01T00:00:00Z");
  assert.ok(script.includes(end.slice(0, 10)), `clock.mjs comment names the window end ${end.slice(0, 10)}`);
});

test("the script reads the offset and writes only the four clock fields, never the device-clock notes", () => {
  const written = [...script.matchAll(/querySelector\("#([a-z-]+)"\)/g)].map((m) => m[1]).sort();
  assert.deepEqual(written, ["tai-date", "tai-offset", "tai-time", "utc-date", "utc-time"]);
  const notes = [...html.matchAll(/<p class="clock-note"[^>]*>([^<]*)</g)].map((m) => m[1]);
  assert.ok(notes.some((n) => n.startsWith("Your device clock, not a UTC realization")), "UTC device-clock note");
  assert.ok(notes.some((n) => n.startsWith("Device clock + 37 s")), "TAI device-clock note");
  assert.doesNotMatch(html, /<p class="clock-note"[^>]*id=/, "no note carries an id the script could target");
});

test("the freshness line names the checked date and the next Circular T", () => {
  const checked = html.match(/Latest issue as checked on <time datetime="(\d{4}-\d{2}-\d{2})">/);
  assert.ok(checked, "checked date present");
  assert.match(html, /the next Circular T \(issue \d+\) is expected/);
  const { end } = offsetData();
  assert.ok(Date.parse(checked[1]) < Date.parse(end), "the TAI window ends after the checked date");
});
