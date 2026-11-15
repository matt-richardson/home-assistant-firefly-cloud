// Tests for the tasks card's pure logic and rendering. Run: ./dev.sh test-js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  QUICK_REASONS,
  changeTag,
  counts,
  escapeHtml,
  formatDay,
  relativeDue,
  renderError,
  renderTasksCard,
  schoolTag,
} from "../../custom_components/firefly_cloud/www/tasks-logic.js";

const OVERVIEW = JSON.parse(readFileSync(new URL("./fixtures/overview-2026-11-14.json", import.meta.url)));
const byId = (id) => OVERVIEW.tasks.find((t) => t.id === id);
const TODAY = OVERVIEW.today;

test("counts from fixture", () => {
  assert.deepEqual(counts(OVERVIEW.tasks), { overdue: 2, this_week: 2, later: 1 });
});

test("formatDay", () => {
  assert.equal(formatDay("2026-11-11"), "Wed 11 Nov");
  assert.equal(formatDay(null), "");
});

test("relativeDue texts", () => {
  assert.deepEqual(relativeDue(byId("69041"), TODAY), { text: "5 days late", tone: "late" });
  assert.deepEqual(relativeDue({ due: "2026-11-13", bucket: "overdue" }, TODAY), { text: "1 day late", tone: "late" });
  assert.deepEqual(relativeDue({ due: "2026-11-14", bucket: "this_week" }, TODAY), { text: "due today", tone: "soon" });
  assert.deepEqual(relativeDue({ due: "2026-11-15", bucket: "this_week" }, TODAY), { text: "tomorrow", tone: "soon" });
  assert.deepEqual(relativeDue(byId("69040"), TODAY), { text: "in 4 days", tone: "soon" });
  assert.deepEqual(relativeDue(byId("69200"), TODAY), { text: "in 10 days", tone: "later" });
  assert.deepEqual(relativeDue({ due: null, bucket: "no_date" }, TODAY), { text: "no due date", tone: "later" });
});

test("changeTag default wording", () => {
  assert.equal(
    changeTag(byId("69040"), ""),
    '✎ Changed on dashboard from <s>Wed 11 Nov</s> · "Ms Rivera gave us another week in class" · Thu 12 Nov',
  );
});

test("changeTag with label", () => {
  assert.match(changeTag(byId("69040"), "Alex"), /^✎ Alex moved from <s>Wed 11 Nov<\/s>/);
});

test("changeTag confirmed and without reason", () => {
  const task = { change: { ...byId("69040").change, reason: null, confirmed: true } };
  assert.equal(changeTag(task, ""), "✎ Changed on dashboard from <s>Wed 11 Nov</s> · Thu 12 Nov · confirmed by school");
});

test("note-only tag", () => {
  assert.equal(changeTag(byId("69045"), "Alex"), "✎ Note: Doing it in class today");
});

test("no change, no tag", () => {
  assert.equal(changeTag(byId("69041"), ""), null);
  assert.equal(schoolTag(byId("69041")), null);
});

test("schoolTag", () => {
  assert.equal(schoolTag(byId("69136")), "↻ School moved from <s>Fri 13 Nov</s> · seen Tue 10 Nov");
  assert.equal(
    schoolTag({ school_change: { from: null, to: "2026-11-20", seen_at: "2026-11-10T15:00:00+11:00" } }),
    "↻ School set the due date · seen Tue 10 Nov",
  );
  assert.equal(
    schoolTag({ school_change: { from: "2026-11-20", to: null, seen_at: "2026-11-10T15:00:00+11:00" } }),
    "↻ School removed the due date · seen Tue 10 Nov",
  );
});

test("quick reasons", () => {
  assert.deepEqual(QUICK_REASONS, ["Doing it in class today", "Extended in class", "Teacher emailed", "Firefly is wrong"]);
});

test("renders card with counts, rows and tags", () => {
  const html = renderTasksCard(OVERVIEW, { title: "Alex's tasks", changed_by_label: "Alex" });
  assert.match(html, /Alex&#39;s tasks/);
  assert.match(html, /data-task-id="69040"/);
  assert.match(html, /Systems Engineering · Ms Rivera/);
  assert.match(html, /Alex moved from/);
  assert.match(html, /School moved from/);
  assert.match(html, /5 days late/);
  assert.equal((html.match(/data-task-id=/g) || []).length, 5);
});

test("renders empty state", () => {
  assert.match(renderTasksCard({ ...OVERVIEW, tasks: [] }, {}), /No open tasks/);
});

test("escapes user and Firefly text", () => {
  const evil = "<img src=x onerror=alert(1)>";
  const task = {
    ...byId("69040"),
    title: evil,
    subject: evil,
    setter: evil,
    change: { ...byId("69040").change, reason: evil },
  };
  const html = renderTasksCard({ ...OVERVIEW, tasks: [task] }, { title: evil, changed_by_label: evil });
  assert.ok(!html.includes("<img"));
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.equal(escapeHtml(`"'&<>`), "&quot;&#39;&amp;&lt;&gt;");
});

test("shows error state", () => {
  const html = renderError("Not a <b>Firefly</b> list");
  assert.match(html, /Not a &lt;b&gt;Firefly&lt;\/b&gt; list/);
  assert.match(html, /class="error"/);
});

test("subjects drop a leading Year N, and a missing subject shows just the teacher", () => {
  const tasks = [
    { ...byId("69041"), subject: "Year 8 Discovery" },
    { ...byId("69045"), subject: null },
  ];
  const html = renderTasksCard({ ...OVERVIEW, tasks }, {});
  assert.match(html, /<div class="meta">Discovery · Mr Okafor<\/div>/);
  assert.match(html, /<div class="meta">Dr Patel<\/div>/);
});
