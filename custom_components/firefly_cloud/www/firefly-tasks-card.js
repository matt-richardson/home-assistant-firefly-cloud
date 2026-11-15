// Tasks card for the Firefly Cloud integration: a child's open tasks, with due dates changed on the
// dashboard and by the school clearly marked. Tapping a task opens the change dialog.
// Logic and rendering live in tasks-logic.js (unit-tested).
const version = new URL(import.meta.url).search;
const { CARD_STYLE, renderError, renderTasksCard } = await import(new URL("./tasks-logic.js" + version, import.meta.url));
const { openTaskDialog } = await import(new URL("./task-dialog.js" + version, import.meta.url));
const { OverviewCard } = await import(new URL("./overview-card.js" + version, import.meta.url));

const CARD_TYPE = "firefly-tasks-card";

class FireflyTasksCard extends OverviewCard {
  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { filter: [{ integration: "firefly_cloud", domain: "todo" }] } } },
        { name: "title", selector: { text: {} } },
        { name: "changed_by_label", selector: { text: {} } },
      ],
    };
  }

  static getStubConfig() {
    return { entity: "" };
  }

  constructor() {
    super();
    this.shadowRoot.addEventListener("click", (ev) => this._onActivate(ev));
    this.shadowRoot.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") this._onActivate(ev);
    });
  }

  getCardSize() {
    return 3 + (this.overview?.tasks.length ?? 0);
  }

  /** Open the change dialog for one of the card's tasks. */
  openTask(taskId) {
    const task = this.overview?.tasks.find((t) => t.id === taskId);
    if (!task) return null;
    const dialog = openTaskDialog({ hass: this.hass, entityId: this.config.entity, task });
    dialog.addEventListener("firefly-task-changed", () => this.fetchOverview(true));
    return dialog;
  }

  _onActivate(ev) {
    const row = ev.target?.closest?.("[data-task-id]");
    if (!row) return;
    ev.preventDefault?.();
    this.openTask(row.dataset.taskId);
  }

  styles() {
    return CARD_STYLE;
  }

  renderError(message) {
    return renderError(message);
  }

  renderBody() {
    return renderTasksCard(this.overview, this.config);
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, FireflyTasksCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "Firefly tasks",
    description: "A child's open Firefly tasks, with due date changes marked.",
  });
}
