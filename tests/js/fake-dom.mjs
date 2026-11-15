// A minimal fake DOM for the card tests (no browser): just enough for custom elements that
// render into a shadow root with innerHTML. Interactions are tested through the elements' own
// handler methods rather than real DOM events.
export const defined = {};
export const opened = [];

export function installFakeDom() {
  globalThis.window = globalThis;
  globalThis.HTMLElement = class {
    constructor() {
      this.listeners = {};
      this.events = [];
      this.attributes = {};
    }
    attachShadow() {
      this.shadowRoot = { innerHTML: "", addEventListener: () => {}, querySelector: () => null, querySelectorAll: () => [] };
      return this.shadowRoot;
    }
    addEventListener(type, fn) {
      this.listeners[type] = fn;
    }
    removeEventListener(type) {
      delete this.listeners[type];
    }
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    }
    hasAttribute(name) {
      return name in this.attributes;
    }
    get tabIndex() {
      return Number(this.attributes.tabindex ?? -1);
    }
    set tabIndex(value) {
      this.attributes.tabindex = String(value);
    }
    remove() {
      const i = opened.indexOf(this);
      if (i >= 0) opened.splice(i, 1);
    }
    dispatchEvent(event) {
      this.events.push(event);
      (this.listeners[event.type] || (() => {}))(event);
      return true;
    }
  };
  globalThis.CustomEvent = class {
    constructor(type, init) {
      this.type = type;
      this.detail = init?.detail;
    }
  };
  globalThis.document = {
    createElement: (tag) => new defined[tag](),
    body: { appendChild: (el) => opened.push(el) },
  };
  globalThis.customElements = {
    define: (name, cls) => {
      defined[name] = cls;
    },
    get: (name) => defined[name],
  };
  globalThis.customCards = globalThis.customCards || [];
}

export const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
