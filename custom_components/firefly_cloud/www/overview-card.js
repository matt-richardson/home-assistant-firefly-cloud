// Shared base for the Firefly cards: loads a child's overview over the websocket and re-renders.
// It only reads Home Assistant's own data (firefly_cloud/child_overview never calls Firefly).
const MIN_REFETCH_MS = 60_000;
// Refetch at least this often while the dashboard is open, even if the entity's state hasn't changed
const MAX_AGE_MS = 300_000;
// While Firefly data is loading (HA starting up), check again this often
const WAITING_RETRY_MS = 5_000;

// Task ids and dates are digits and dashes, but escape anyway before building a selector
const CSS_ESCAPE = (value) => String(value).replace(/["\\]/g, "\\$&");

export class OverviewCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.overview = null;
    this.error = null;
    this._fetchedAt = 0;
    this._lastUpdated = undefined;
    this._fetching = false;
    this._refetchQueued = false;
    this._waiting = false;
    this._html = null;
  }

  /** Subclasses can fill in defaults. */
  normaliseConfig(config) {
    return config;
  }

  setConfig(config) {
    if (!config?.entity) throw new Error("Pick the child's Firefly tasks entity (entity)");
    this.config = this.normaliseConfig(config);
    this.overview = null;
    this._fetchedAt = 0;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    const lastUpdated = hass.states[this.config?.entity]?.last_updated;
    const changed = lastUpdated !== this._lastUpdated;
    this._lastUpdated = lastUpdated;
    // A changed entity always refetches (it's rare, and may mean the data has just loaded)
    if (changed) this.fetchOverview(true);
    else if (Date.now() - this._fetchedAt > (this._waiting ? WAITING_RETRY_MS : MAX_AGE_MS)) this.fetchOverview(false);
  }

  get hass() {
    return this._hass;
  }

  async fetchOverview(force) {
    if (!this._hass || !this.config) return;
    if (this._fetching) {
      // A forced refresh (e.g. straight after a save) runs once the fetch in flight finishes,
      // since that fetch may have started before the save
      if (force) this._refetchQueued = true;
      return;
    }
    const minGap = this._waiting ? WAITING_RETRY_MS : MIN_REFETCH_MS;
    if (!force && this._fetchedAt && Date.now() - this._fetchedAt < minGap) return;
    this._fetching = true;
    this._waiting = false;
    try {
      this.overview = await this._hass.callWS({ type: "firefly_cloud/child_overview", entity_id: this.config.entity });
      this.error = null;
    } catch (err) {
      if (err?.code === "not_ready") {
        this._waiting = true;
        this.error = null;
      } else {
        this.error =
          err?.code === "not_found"
            ? "This isn't a Firefly tasks list. Pick the child's Firefly tasks entity."
            : err?.message || "Couldn't load from Home Assistant";
      }
    } finally {
      this._fetching = false;
      this._fetchedAt = Date.now();
    }
    this.render();
    if (this._refetchQueued) {
      this._refetchQueued = false;
      await this.fetchOverview(true);
    }
  }

  render() {
    let body;
    if (this.error) body = this.renderError(this.error);
    else if (this._waiting && !this.overview) body = `<div class="empty">Waiting for Firefly data…</div>`;
    else if (!this.overview) body = `<div class="empty">Loading…</div>`;
    else body = this.renderBody();
    const html = `<style>ha-card { padding: 16px; } ${this.styles()}</style><ha-card>${body}</ha-card>`;
    // Leave the DOM alone when nothing changed, so keyboard focus isn't lost
    if (html === this._html) return;
    const focusSelector = this._focusSelector();
    this.shadowRoot.innerHTML = html;
    this._html = html;
    if (focusSelector) this.shadowRoot.querySelector(focusSelector)?.focus();
  }

  /** A selector for the focused task row or strip day, to put focus back after re-rendering. */
  _focusSelector() {
    const data = this.shadowRoot.activeElement?.dataset;
    if (data?.taskId) return `[data-task-id="${CSS_ESCAPE(data.taskId)}"]`;
    if (data?.date) return `[data-date="${CSS_ESCAPE(data.date)}"]`;
    return null;
  }
}
