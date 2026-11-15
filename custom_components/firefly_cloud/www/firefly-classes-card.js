// Upcoming classes card for the Firefly Cloud integration: the next school day in detail (what to pack,
// kit days, lessons) and a strip of the coming school days. Logic lives in classes-logic.js (unit-tested).
const version = new URL(import.meta.url).search;
const { CARD_STYLE, DEFAULT_KIT_SUBJECTS, escapeHtml, nextSchoolDay, renderClassesCard, visibleDays } = await import(
  new URL("./classes-logic.js" + version, import.meta.url)
);
const { OverviewCard } = await import(new URL("./overview-card.js" + version, import.meta.url));

const CARD_TYPE = "firefly-classes-card";
// Re-render (without fetching) so "after school" switches over by itself
const RERENDER_MS = 300_000;

class FireflyClassesCard extends OverviewCard {
  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { filter: [{ integration: "firefly_cloud", domain: "todo" }] } } },
        { name: "title", selector: { text: {} } },
        { name: "kit_subjects", selector: { text: { multiple: true } } },
        { name: "hide_subjects", selector: { text: { multiple: true } } },
      ],
    };
  }

  static getStubConfig() {
    return { entity: "" };
  }

  constructor() {
    super();
    this.selectedDate = null;
    // The automatic day when a day was tapped; the tap is forgotten once that moves on
    this._selectedFor = null;
    this.now = () => new Date();
    this.shadowRoot.addEventListener("click", (ev) => {
      const button = ev.target?.closest?.("[data-date]");
      if (button) this.selectDay(button.dataset.date);
    });
  }

  normaliseConfig(config) {
    return {
      ...config,
      kit_subjects: config.kit_subjects ?? DEFAULT_KIT_SUBJECTS,
      hide_subjects: config.hide_subjects ?? [],
    };
  }

  connectedCallback() {
    this._timer = setInterval(() => this.render(), RERENDER_MS);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() {
    return 6;
  }

  /** The day shown when nothing is tapped: today, or the next day with lessons. */
  autoDate() {
    if (!this.overview) return null;
    const { today, time } = this.localNow();
    return nextSchoolDay(visibleDays(this.overview, this.config), today, time)?.date ?? null;
  }

  /** Show a day from the strip (no fetch). Tapping the automatic day goes back to following it. */
  selectDay(date) {
    const auto = this.autoDate();
    this.selectedDate = date === auto ? null : date;
    this._selectedFor = auto;
    this.render();
  }

  /** Today's date and the time in Home Assistant's timezone. */
  localNow() {
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-CA", {
        timeZone: this.hass?.config?.time_zone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      })
        .formatToParts(this.now())
        .map((p) => [p.type, p.value]),
    );
    return { today: `${parts.year}-${parts.month}-${parts.day}`, time: `${parts.hour}:${parts.minute}` };
  }

  styles() {
    return `${CARD_STYLE} .error { color: var(--error-color, #db4437); } .title { font-size: 0.85em; color: var(--secondary-text-color); margin-bottom: 4px; }`;
  }

  renderError(message) {
    return `<div class="error">${escapeHtml(message)}</div>`;
  }

  renderBody() {
    const { today, time } = this.localNow();
    if (this.selectedDate && this.autoDate() !== this._selectedFor) this.selectedDate = null;
    const title = this.config.title ? `<div class="title">${escapeHtml(this.config.title)}</div>` : "";
    return title + renderClassesCard(this.overview, this.config, this.selectedDate, today, time);
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, FireflyClassesCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "Firefly upcoming classes",
    description: "The next school day's lessons, what to pack and kit days, with the week ahead.",
  });
}
