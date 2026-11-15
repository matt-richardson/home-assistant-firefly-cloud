// Tests for the tasks card element and its change dialog, with a fake DOM. Run: ./dev.sh test-js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { defined, installFakeDom, opened, tick } from "./fake-dom.mjs";

installFakeDom();
await import("../../custom_components/firefly_cloud/www/firefly-tasks-card.js");
const { historyText } = await import("../../custom_components/firefly_cloud/www/tasks-logic.js");
const Card = defined["firefly-tasks-card"];
const OVERVIEW = JSON.parse(readFileSync(new URL("./fixtures/overview-2026-11-14.json", import.meta.url)));
const ENTITY = "todo.example_school_tasks_alex";

function makeHass({ callWS, lastUpdated = "t1" } = {}) {
  const hass = {
    states: { [ENTITY]: { entity_id: ENTITY, last_updated: lastUpdated } },
    wsCalls: [],
    serviceCalls: [],
    callWS: callWS || (async (msg) => (hass.wsCalls.push(msg), OVERVIEW)),
    callService: async (...args) => hass.serviceCalls.push(args),
  };
  return hass;
}

async function makeCard(config = {}, hass = makeHass()) {
  const card = new Card();
  card.setConfig({ entity: ENTITY, ...config });
  card.hass = hass;
  await tick();
  return { card, hass };
}

function openDialog(card, taskId) {
  opened.length = 0;
  card.openTask(taskId);
  return opened.at(-1);
}

test("registers the element and a card picker entry", () => {
  assert.ok(Card);
  assert.ok(window.customCards.find((c) => c.type === "firefly-tasks-card"));
});

test("getConfigForm filters to firefly todo", () => {
  const [entity] = Card.getConfigForm().schema;
  assert.equal(entity.name, "entity");
  assert.deepEqual(entity.selector.entity.filter, [{ integration: "firefly_cloud", domain: "todo" }]);
  assert.ok(Card.getConfigForm().schema.some((f) => f.name === "changed_by_label"));
});

test("setConfig requires an entity", () => {
  assert.throws(() => new Card().setConfig({}), /entity/);
});

test("renders rows from callWS", async () => {
  const { card, hass } = await makeCard({ changed_by_label: "Alex" });
  assert.deepEqual(hass.wsCalls, [{ type: "firefly_cloud/child_overview", entity_id: ENTITY }]);
  assert.match(card.shadowRoot.innerHTML, /data-task-id="69040"/);
  assert.match(card.shadowRoot.innerHTML, /Alex moved from/);
});

test("doesn't refetch on every hass update", async () => {
  const { card, hass } = await makeCard();
  card.hass = hass;
  await tick();
  assert.equal(hass.wsCalls.length, 1);
});

test("shows error state on callWS not_found", async () => {
  const hass = makeHass({
    callWS: async () => {
      throw { code: "not_found", message: "Not a Firefly Cloud tasks list with data" };
    },
  });
  const { card } = await makeCard({}, hass);
  assert.match(card.shadowRoot.innerHTML, /class="error"/);
  assert.match(card.shadowRoot.innerHTML, /isn&#39;t a Firefly tasks list/);
});

test("save with new date calls set_task_due_date with date and reason", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69041");
  dialog.setDueDate("2026-11-18");
  dialog.setReason("Extended in class");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls, [
    ["firefly_cloud", "set_task_due_date", { entity_id: ENTITY, task_id: "69041", due_date: "2026-11-18", reason: "Extended in class" }],
  ]);
  assert.equal(opened.length, 0);
});

test("save with reason only omits due_date", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69041");
  dialog.setReason("  Doing it in class today ");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls[0][2], { entity_id: ENTITY, task_id: "69041", reason: "Doing it in class today" });
});

test("chip fills reason and leaves date unchanged", async () => {
  const { card } = await makeCard();
  const dialog = openDialog(card, "69041");
  dialog.chooseReason("Doing it in class today");
  assert.equal(dialog.reason, "Doing it in class today");
  assert.equal(dialog.dueDate, "2026-11-09");
});

test("save with nothing shows message and no service call", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69041");
  assert.equal(await dialog.save(), false);
  assert.equal(hass.serviceCalls.length, 0);
  assert.match(dialog.shadowRoot.innerHTML, /Nothing to save/);
});

test("service errors are shown in the dialog", async () => {
  const { card, hass } = await makeCard();
  hass.callService = async () => {
    throw new Error("Task 1 is not one of this child's open tasks.");
  };
  const dialog = openDialog(card, "69041");
  dialog.setReason("x");
  assert.equal(await dialog.save(), false);
  assert.match(dialog.shadowRoot.innerHTML, /not one of this child&#39;s open tasks/);
  assert.equal(opened.length, 1);
});

test("undo calls clear_task_due_date", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69040");
  assert.match(dialog.shadowRoot.innerHTML, /data-action="undo"/);
  await dialog.undo();
  assert.deepEqual(hass.serviceCalls, [["firefly_cloud", "clear_task_due_date", { entity_id: ENTITY, task_id: "69040" }]]);
});

test("undo hidden without change", async () => {
  const { card } = await makeCard();
  const dialog = openDialog(card, "69041");
  assert.doesNotMatch(dialog.shadowRoot.innerHTML, /data-action="undo"/);
});

test("dialog shows Firefly's date, quick reasons and history", async () => {
  const { card } = await makeCard();
  const html = openDialog(card, "69040").shadowRoot.innerHTML;
  assert.match(html, /Wed 11 Nov/);
  assert.match(html, /Doing it in class today/);
  assert.match(html, /Set by Ms Rivera, due Wed 11 Nov/);
  assert.doesNotMatch(html, /Open in Firefly/);
});

test("refetches after task-changed", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69041");
  dialog.setReason("x");
  await dialog.save();
  await tick();
  assert.equal(hass.wsCalls.length, 2);
});

test("historyText", () => {
  const at = "2026-11-12T16:30:00+11:00";
  assert.equal(historyText({ at, kind: "set", text_fields: { setter: "Ms Rivera", due: "2026-11-11" } }), "Thu 12 Nov · Set by Ms Rivera, due Wed 11 Nov");
  assert.equal(historyText({ at: null, kind: "set", text_fields: { setter: null, due: null } }), "Set");
  assert.equal(
    historyText({ at, kind: "dashboard", text_fields: { from: "2026-11-11", new_due_date: "2026-11-18", reason: "Extended", ended_by: "undone" } }),
    'Thu 12 Nov · Moved from Wed 11 Nov to Wed 18 Nov · "Extended"',
  );
  assert.equal(
    historyText({ at, kind: "dashboard", text_fields: { from: "2026-11-11", new_due_date: "2026-11-18", reason: null, confirmed: true } }),
    "Thu 12 Nov · Moved from Wed 11 Nov to Wed 18 Nov · confirmed by school",
  );
  assert.equal(historyText({ at, kind: "note", text_fields: { reason: "<b>" } }), "Thu 12 Nov · Note: &lt;b&gt;");
  assert.equal(historyText({ at, kind: "undone", text_fields: { new_due_date: "2026-11-18" } }), "Thu 12 Nov · Undid the move to Wed 18 Nov");
  assert.equal(historyText({ at, kind: "undone", text_fields: { new_due_date: null } }), "Thu 12 Nov · Undid the note");
  assert.equal(historyText({ at, kind: "school", text_fields: { from: "2026-11-13", to: "2026-11-20" } }), "Thu 12 Nov · School moved from Fri 13 Nov to Fri 20 Nov");
  assert.equal(historyText({ at, kind: "school", text_fields: { from: null, to: null } }), "Thu 12 Nov · School changed the due date");
});

test("editing the reason on a moved task keeps its new date", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69040");
  dialog.setReason("Teacher emailed");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls[0][2], {
    entity_id: ENTITY,
    task_id: "69040",
    due_date: "2026-11-18",
    reason: "Teacher emailed",
  });
});

test("setting the date back to Firefly's on a moved task saves Firefly's date", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69040");
  dialog.setDueDate("2026-11-11");
  dialog.setReason("Firefly was right");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls[0][2], { entity_id: ENTITY, task_id: "69040", reason: "Firefly was right" });
});

test("putting a moved task back on Firefly's date with no reason undoes the change", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69040");
  dialog.setDueDate("2026-11-11");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls, [["firefly_cloud", "clear_task_due_date", { entity_id: ENTITY, task_id: "69040" }]]);
});

test("while Firefly data is loading the card says so, not that the entity is wrong", async () => {
  const hass = makeHass({
    callWS: async () => {
      throw { code: "not_ready", message: "Firefly data isn't loaded yet" };
    },
  });
  const { card } = await makeCard({}, hass);
  assert.match(card.shadowRoot.innerHTML, /Waiting for Firefly data/);
  assert.doesNotMatch(card.shadowRoot.innerHTML, /isn&#39;t a Firefly tasks list/);
});

test("a forced refresh asked for during a fetch runs when that fetch finishes", async () => {
  let release;
  const hass = makeHass();
  const plainCallWS = hass.callWS;
  hass.callWS = (msg) => {
    if (hass.wsCalls.length === 0) {
      hass.wsCalls.push(msg);
      return new Promise((resolve) => {
        release = () => resolve(OVERVIEW);
      });
    }
    return plainCallWS(msg);
  };
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  card.hass = hass; // starts the first fetch, which stays in flight
  await tick();
  const forced = card.fetchOverview(true); // e.g. straight after a save
  release();
  await forced;
  await tick();
  await tick();
  assert.equal(hass.wsCalls.length, 2);
});

test("re-rendering with nothing changed leaves the DOM (and focus) alone", async () => {
  const { card } = await makeCard();
  card.shadowRoot.innerHTML = "untouched";
  card.render();
  assert.equal(card.shadowRoot.innerHTML, "untouched");
});

test("re-rendering puts focus back on the same task", async () => {
  const { card } = await makeCard();
  let focusedSelector = null;
  card.shadowRoot.activeElement = { dataset: { taskId: "69040" } };
  card.shadowRoot.querySelector = (selector) => ({ focus: () => (focusedSelector = selector) });
  card.overview = { ...OVERVIEW, tasks: OVERVIEW.tasks.slice(1) };
  card.render();
  assert.equal(focusedSelector, '[data-task-id="69040"]');
});

test("the dialog shows the subject without a leading Year N", async () => {
  const { card } = await makeCard();
  card.overview = { ...OVERVIEW, tasks: OVERVIEW.tasks.map((t) => (t.id === "69040" ? { ...t, subject: "Year 8 Systems Engineering" } : t)) };
  const html = openDialog(card, "69040").shadowRoot.innerHTML;
  assert.match(html, /<div class="meta">Systems Engineering · Ms Rivera · Not submitted<\/div>/);
});

test("after 'not ready', the card fetches again as soon as the entity changes", async () => {
  let ready = false;
  const hass = makeHass({
    callWS: async (msg) => {
      hass.wsCalls.push(msg);
      if (!ready) throw { code: "not_ready" };
      return OVERVIEW;
    },
  });
  const { card } = await makeCard({}, hass);
  assert.match(card.shadowRoot.innerHTML, /Waiting for Firefly data/);
  ready = true;
  card.hass = { ...hass, states: { [ENTITY]: { entity_id: ENTITY, last_updated: "t2" } } };
  await tick();
  assert.equal(hass.wsCalls.length, 2);
  assert.match(card.shadowRoot.innerHTML, /data-task-id="69040"/);
});

test("while waiting, the card retries every few seconds even without an entity change", async () => {
  const hass = makeHass({
    callWS: async (msg) => {
      hass.wsCalls.push(msg);
      throw { code: "not_ready" };
    },
  });
  const { card } = await makeCard({}, hass);
  card.hass = hass; // straight away: too soon
  await tick();
  assert.equal(hass.wsCalls.length, 1);
  card._fetchedAt -= 6000; // six seconds later
  card.hass = hass;
  await tick();
  assert.equal(hass.wsCalls.length, 2);
});

test("an entity change within a minute of the last fetch still refetches", async () => {
  const { card, hass } = await makeCard();
  card.hass = { ...hass, states: { [ENTITY]: { entity_id: ENTITY, last_updated: "t2" } } };
  await tick();
  assert.equal(hass.wsCalls.length, 2);
});

test("'needs attention' shows Home Assistant's message", async () => {
  const hass = makeHass({
    callWS: async () => {
      throw { code: "needs_attention", message: "Firefly Cloud needs attention. Check Settings → Devices & services." };
    },
  });
  const { card } = await makeCard({}, hass);
  assert.match(card.shadowRoot.innerHTML, /class="error">Firefly Cloud needs attention/);
});

test("clearing the date and giving a reason keeps a moved task's date", async () => {
  const { card, hass } = await makeCard();
  const dialog = openDialog(card, "69040");
  dialog.setDueDate("");
  dialog.setReason("Teacher emailed");
  await dialog.save();
  assert.deepEqual(hass.serviceCalls[0][2], {
    entity_id: ENTITY,
    task_id: "69040",
    due_date: "2026-11-18",
    reason: "Teacher emailed",
  });
});
