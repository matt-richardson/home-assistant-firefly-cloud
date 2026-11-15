// Tests for the upcoming classes card's pure logic and rendering. Run: ./dev.sh test-js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  CARD_STYLE,
  DEFAULT_KIT_SUBJECTS,
  dueCountByDate,
  isHidden,
  isKit,
  nextSchoolDay,
  renderClassesCard,
  shortName,
  stripDays,
  visibleDays,
} from "../../custom_components/firefly_cloud/www/classes-logic.js";

const OVERVIEW = JSON.parse(readFileSync(new URL("./fixtures/overview-2026-11-14.json", import.meta.url)));
const DAYS = OVERVIEW.lesson_days;
const HIDE = { hide_subjects: ["Middle School Pastoral Program"] };

test("default kit subjects", () => {
  assert.deepEqual(DEFAULT_KIT_SUBJECTS, ["PE", "Physical Education", "Sport", "Games", "Swimming"]);
});

test("isKit", () => {
  assert.ok(isKit("Year 8 Physical Education", DEFAULT_KIT_SUBJECTS));
  assert.ok(isKit("Year 8 Sport", DEFAULT_KIT_SUBJECTS));
  assert.ok(isKit("Year 9 PE", DEFAULT_KIT_SUBJECTS));
  assert.ok(isKit("games", DEFAULT_KIT_SUBJECTS));
  assert.ok(!isKit("Speech and Drama", DEFAULT_KIT_SUBJECTS));
  assert.ok(!isKit("Year 8 Mathematics", DEFAULT_KIT_SUBJECTS));
  assert.ok(!isKit("Year 8 Mathematics", []));
});

test("isHidden", () => {
  assert.ok(isHidden("Middle School Pastoral Program", HIDE.hide_subjects));
  assert.ok(isHidden("middle school pastoral program", HIDE.hide_subjects));
  assert.ok(!isHidden("Middle School Pastoral Program", []));
});

test("shortName", () => {
  assert.equal(shortName("Year 8 Mathematics"), "Mathematics");
  assert.equal(shortName("Link Year 8"), "Link Year 8");
  assert.equal(shortName("Maths"), "Maths");
});

test("hide list removes lessons from the list and strip; empty list keeps them", () => {
  assert.equal(visibleDays(OVERVIEW, HIDE)[0].lessons.length, 5);
  assert.equal(visibleDays(OVERVIEW, {})[0].lessons.length, 6);
  const html = renderClassesCard(OVERVIEW, HIDE, null, "2026-11-14", "10:00");
  assert.doesNotMatch(html, /Pastoral/);
  assert.match(renderClassesCard(OVERVIEW, {}, null, "2026-11-14", "10:00"), /Pastoral/);
});

test("days left empty by hiding are dropped", () => {
  const overview = { ...OVERVIEW, lesson_days: [{ date: "2026-11-16", lessons: [DAYS[0].lessons[0]] }] };
  assert.deepEqual(visibleDays(overview, HIDE), []);
});

test("nextSchoolDay Saturday → Monday", () => {
  assert.deepEqual(nextSchoolDay(DAYS, "2026-11-14", "10:00"), { date: "2026-11-16", reason: "weekend_or_break" });
});

test("nextSchoolDay at 3:30pm on a school day → next day", () => {
  assert.deepEqual(nextSchoolDay(DAYS, "2026-11-16", "15:30"), { date: "2026-11-17", reason: "after_school" });
});

test("nextSchoolDay at 10am → today", () => {
  assert.deepEqual(nextSchoolDay(DAYS, "2026-11-16", "10:00"), { date: "2026-11-16", reason: "today" });
});

test("nextSchoolDay with nothing ahead", () => {
  assert.equal(nextSchoolDay(DAYS, "2026-11-23", "16:00"), null);
});

test("strip of 5 from Monday", () => {
  const strip = stripDays(visibleDays(OVERVIEW, HIDE), "2026-11-16");
  assert.deepEqual(
    strip.map((d) => d.date),
    ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"],
  );
});

test("due counts use the effective date and skip overdue tasks", () => {
  assert.deepEqual(dueCountByDate(OVERVIEW.tasks), { "2026-11-18": 1, "2026-11-20": 1, "2026-11-24": 1 });
});

test("renders the next school day with kit lessons highlighted and the strip, without subject chips", () => {
  const html = renderClassesCard(OVERVIEW, HIDE, null, "2026-11-14", "10:00");
  assert.match(html, /Monday/);
  assert.match(html, /school&#39;s out for the weekend/);
  assert.doesNotMatch(html, /class="chips"/);
  assert.doesNotMatch(html, /class="chip/);
  assert.match(html, /class="lesson kit"><span class="t">12:35<\/span><span class="n">Physical Education/);
  assert.match(html, /08:55.*German.*M7/s);
  assert.doesNotMatch(html, /Year 8 /);
  assert.equal((html.match(/data-date=/g) || []).length, 5);
  assert.match(html, /aria-label="Tuesday 17 November, kit day"/);
  assert.match(html, /aria-label="Wednesday 18 November, 1 task due"/);
  assert.match(html, /data-date="2026-11-16"[^>]*aria-current="true"/);
});

test("context note after school and on a weekday with no lessons", () => {
  assert.match(renderClassesCard(OVERVIEW, HIDE, null, "2026-11-16", "15:30"), /today&#39;s lessons have finished/);
  assert.match(renderClassesCard(OVERVIEW, HIDE, null, "2026-11-13", "10:00"), /there are no lessons today/);
  assert.doesNotMatch(renderClassesCard(OVERVIEW, HIDE, null, "2026-11-16", "10:00"), /Showing/);
});

test("a selected day replaces the main panel", () => {
  const html = renderClassesCard(OVERVIEW, HIDE, "2026-11-18", "2026-11-14", "10:00");
  assert.match(html, /Wednesday/);
  assert.match(html, /Systems Engineering/);
  assert.doesNotMatch(html, /Showing/);
});

test("custom kit_subjects applied", () => {
  const html = renderClassesCard(OVERVIEW, { ...HIDE, kit_subjects: ["German"] }, null, "2026-11-14", "10:00");
  assert.match(html, /class="lesson kit"><span class="t">08:55<\/span><span class="n">German/);
  assert.doesNotMatch(html, /class="lesson kit"><span class="t">12:35/);
});

test("no timetable message", () => {
  const html = renderClassesCard({ ...OVERVIEW, lesson_days: [] }, {}, null, "2026-11-14", "10:00");
  assert.match(html, /No timetable from your school for the next two weeks/);
});

test("escapes subject and room", () => {
  const evil = "<img src=x onerror=alert(1)>";
  const overview = { ...OVERVIEW, lesson_days: [{ date: "2026-11-16", lessons: [{ start: "09:00", end: "10:00", subject: evil, location: evil }] }] };
  const html = renderClassesCard(overview, {}, null, "2026-11-14", "10:00");
  assert.ok(!html.includes("<img"));
});

test("nextSchoolDay keeps today while a late lesson running to midnight is on", () => {
  const days = [
    { date: "2026-11-16", lessons: [{ start: "23:00", end: "24:00", subject: "Overnight Camp", location: "" }] },
    { date: "2026-11-17", lessons: [{ start: "08:40", end: "08:50", subject: "Homegroup", location: "" }] },
  ];
  assert.deepEqual(nextSchoolDay(days, "2026-11-16", "23:30"), { date: "2026-11-16", reason: "today" });
});

test("kit days in the strip use a white t-shirt icon, not the emoji", () => {
  const html = renderClassesCard(OVERVIEW, HIDE, null, "2026-11-14", "10:00");
  assert.equal((html.match(/<ha-icon class="kit-icon" icon="mdi:tshirt-crew"><\/ha-icon>/g) || []).length, 2);
  assert.doesNotMatch(html, /👕/);
  assert.match(CARD_STYLE, /\.kit-icon \{[^}]*color: #fff/);
});

test("each strip day has one marks line under its name, holding the t-shirt and/or the due count", () => {
  const html = renderClassesCard(OVERVIEW, HIDE, null, "2026-11-14", "10:00");
  assert.equal((html.match(/<span class="marks">/g) || []).length, 5);
  assert.match(html, /<b>Wed<\/b><span class="marks"><span class="due">1 due<\/span><\/span>/);
  assert.match(html, /<b>Mon<\/b><span class="marks"><ha-icon class="kit-icon" icon="mdi:tshirt-crew"><\/ha-icon><\/span>/);
  assert.doesNotMatch(html, /&nbsp;|kit-slot/);
  assert.match(CARD_STYLE, /\.marks \{[^}]*min-height: 18px;/);
});

test("a kit day with tasks due shows both on the marks line", () => {
  const tasks = [{ due: "2026-11-16", bucket: "this_week" }];
  const html = renderClassesCard({ ...OVERVIEW, tasks }, HIDE, null, "2026-11-14", "10:00");
  assert.match(html, /<b>Mon<\/b><span class="marks"><ha-icon class="kit-icon" icon="mdi:tshirt-crew"><\/ha-icon><span class="due">1 due<\/span><\/span>/);
});
