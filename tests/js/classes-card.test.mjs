// Tests for the upcoming classes card element, with a fake DOM. Run: ./dev.sh test-js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { defined, installFakeDom, tick } from "./fake-dom.mjs";

installFakeDom();
await import("../../custom_components/firefly_cloud/www/firefly-classes-card.js");
const Card = defined["firefly-classes-card"];
const OVERVIEW = JSON.parse(readFileSync(new URL("./fixtures/overview-2026-11-14.json", import.meta.url)));
const ENTITY = "todo.example_school_tasks_alex";
// Saturday 14 Nov 2026, 10:00 in Melbourne
const SATURDAY_10AM = new Date("2026-11-13T23:00:00Z");

function makeHass(callWS) {
  const hass = {
    states: { [ENTITY]: { entity_id: ENTITY, last_updated: "t1" } },
    config: { time_zone: "Australia/Melbourne" },
    wsCalls: [],
    callWS: callWS || (async (msg) => (hass.wsCalls.push(msg), OVERVIEW)),
  };
  return hass;
}

async function makeCard(config = {}, hass = makeHass()) {
  const card = new Card();
  card.now = () => SATURDAY_10AM;
  card.setConfig({ entity: ENTITY, hide_subjects: ["Middle School Pastoral Program"], ...config });
  card.hass = hass;
  await tick();
  return { card, hass };
}

test("registers the element and a card picker entry", () => {
  assert.ok(Card);
  assert.ok(window.customCards.find((c) => c.type === "firefly-classes-card"));
});

test("renders next school day from callWS", async () => {
  const { card, hass } = await makeCard();
  assert.deepEqual(hass.wsCalls, [{ type: "firefly_cloud/child_overview", entity_id: ENTITY }]);
  const html = card.shadowRoot.innerHTML;
  assert.match(html, /Monday/);
  assert.match(html, /school&#39;s out for the weekend/);
  assert.doesNotMatch(html, /Pastoral/);
});

test("strip tap changes main panel without callWS", async () => {
  const { card, hass } = await makeCard();
  card.selectDay("2026-11-18");
  assert.match(card.shadowRoot.innerHTML, /Wednesday/);
  assert.equal(hass.wsCalls.length, 1);
});

test("config defaults", async () => {
  const names = Card.getConfigForm().schema.map((f) => f.name);
  assert.deepEqual(names, ["entity", "title", "kit_subjects", "hide_subjects"]);
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  assert.deepEqual(card.config.kit_subjects, ["PE", "Physical Education", "Sport", "Games", "Swimming"]);
  assert.deepEqual(card.config.hide_subjects, []);
});

test("custom kit_subjects applied", async () => {
  const { card } = await makeCard({ kit_subjects: ["German"] });
  assert.match(card.shadowRoot.innerHTML, /class="lesson kit"><span class="t">08:55<\/span><span class="n">German/);
});

test("shows error state on not_found", async () => {
  const hass = makeHass(async () => {
    throw { code: "not_found" };
  });
  const { card } = await makeCard({}, hass);
  assert.match(card.shadowRoot.innerHTML, /class="error"/);
});

test("a tapped day is forgotten once the next school day moves on", async () => {
  const { card } = await makeCard();
  card.selectDay("2026-11-20");
  assert.match(card.shadowRoot.innerHTML, /Friday/);
  card.now = () => new Date("2026-11-16T04:30:00Z"); // Monday 3:30pm: school's finished, next day is Tuesday
  card.render();
  assert.match(card.shadowRoot.innerHTML, /<h2>Tuesday/);
});

test("tapping the automatic day clears the selection", async () => {
  const { card } = await makeCard();
  card.selectDay("2026-11-18");
  card.selectDay("2026-11-16");
  assert.equal(card.selectedDate, null);
  card.now = () => new Date("2026-11-16T04:30:00Z");
  card.render();
  assert.match(card.shadowRoot.innerHTML, /<h2>Tuesday/);
});

test("re-rendering puts focus back on the same strip day", async () => {
  const { card } = await makeCard();
  let focusedSelector = null;
  card.shadowRoot.activeElement = { dataset: { date: "2026-11-18" } };
  card.shadowRoot.querySelector = (selector) => ({ focus: () => (focusedSelector = selector) });
  card.selectDay("2026-11-18");
  assert.equal(focusedSelector, '[data-date="2026-11-18"]');
});
