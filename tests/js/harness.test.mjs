// Checks the fake DOM used by the card tests. Run: ./dev.sh test-js
import assert from "node:assert/strict";
import { test } from "node:test";

import { installFakeDom } from "./fake-dom.mjs";

test("fake DOM provides custom elements", () => {
  installFakeDom();
  assert.equal(typeof customElements.define, "function");
  assert.equal(typeof new HTMLElement().attachShadow, "function");
});
