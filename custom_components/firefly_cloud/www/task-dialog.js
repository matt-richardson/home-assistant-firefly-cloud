// The change dialog for one task: set a new due date and/or a reason, or undo a change.
// Changes go through the firefly_cloud services; Firefly itself is never changed.
const version = new URL(import.meta.url).search;
const { QUICK_REASONS, escapeHtml, formatDay, historyText, shortSubject } = await import(
  new URL("./tasks-logic.js" + version, import.meta.url)
);

const TAG = "firefly-task-dialog";
const MAX_REASON = 200;

const STYLE = `
  .backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); z-index: 1000;
    display: flex; align-items: center; justify-content: center; }
  .dialog { background: var(--card-background-color, #fff); color: var(--primary-text-color);
    border-radius: 16px; padding: 20px; width: min(420px, 100vw); max-height: 100vh; overflow: auto; box-sizing: border-box; }
  @media (max-width: 450px) { .dialog { border-radius: 0; height: 100vh; } }
  h2 { margin: 0 0 4px; font-size: 1.15em; font-weight: 500; }
  .meta { color: var(--secondary-text-color); font-size: 0.9em; }
  label { display: block; margin-top: 14px; font-size: 0.8em; color: var(--secondary-text-color); }
  input { width: 100%; box-sizing: border-box; padding: 8px; margin-top: 4px; font: inherit;
    border: 1px solid var(--divider-color); border-radius: 8px; background: transparent; color: inherit; }
  .readonly { margin-top: 4px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .chip { border: 1px solid var(--divider-color); border-radius: 14px; padding: 3px 10px; font-size: 0.85em;
    background: transparent; color: inherit; cursor: pointer; }
  .message { margin-top: 12px; color: var(--error-color, #db4437); }
  .buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
  button.action { padding: 8px 14px; border-radius: 8px; border: 0; font: inherit; cursor: pointer;
    background: transparent; color: var(--primary-color); }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .history { margin-top: 18px; border-top: 1px solid var(--divider-color); padding-top: 10px; font-size: 0.85em;
    color: var(--secondary-text-color); }
  .history div { padding: 2px 0; }
`;

class FireflyTaskDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.message = "";
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
  }

  init({ hass, entityId, task }) {
    this.hass = hass;
    this.entityId = entityId;
    this.task = task;
    this.dueDate = task.due || "";
    this.reason = "";
    this._render();
  }

  setDueDate(value) {
    this.dueDate = value;
  }

  setReason(value) {
    this.reason = String(value ?? "").slice(0, MAX_REASON);
  }

  /** A quick reason fills in the reason only; it never changes the date. */
  chooseReason(reason) {
    this.setReason(reason);
    this.message = "";
    this._render();
  }

  async save() {
    const reason = this.reason.trim();
    // An empty date field means "keep the date in force", so a reason alone never drops a move
    if (!this.dueDate) this.dueDate = this.task.due || "";
    const dateChanged = Boolean(this.dueDate) && this.dueDate !== this.task.due;
    if (!dateChanged && !reason) {
      return this._fail("Nothing to save: pick a new date or give a reason.");
    }
    // Choosing Firefly's own date again, with no reason, means "put it back"
    if (this.task.change && this.dueDate === this.task.firefly_due && !reason) return this.undo();
    const data = { entity_id: this.entityId, task_id: this.task.id };
    // Send the date whenever it differs from Firefly's, so editing the reason on a moved task keeps its date;
    // a date equal to Firefly's is saved as a note on Firefly's date
    if (this.dueDate && this.dueDate !== this.task.firefly_due) data.due_date = this.dueDate;
    if (reason) data.reason = reason;
    return this._call("set_task_due_date", data);
  }

  async undo() {
    return this._call("clear_task_due_date", { entity_id: this.entityId, task_id: this.task.id });
  }

  close() {
    this.remove();
  }

  async _call(service, data) {
    try {
      await this.hass.callService("firefly_cloud", service, data);
    } catch (err) {
      return this._fail(err?.message || "Couldn't save the change.");
    }
    this.dispatchEvent(new CustomEvent("firefly-task-changed", { detail: { taskId: this.task.id } }));
    this.close();
    return true;
  }

  _fail(message) {
    this.message = message;
    this._render();
    return false;
  }

  _onClick(ev) {
    const target = ev.target?.closest?.("[data-action]");
    if (!target) {
      if (ev.target?.classList?.contains("backdrop")) this.close();
      return;
    }
    const { action, reason } = target.dataset;
    if (action === "reason") this.chooseReason(reason);
    else if (action === "save") this.save();
    else if (action === "undo") this.undo();
    else if (action === "cancel") this.close();
  }

  _onInput(ev) {
    if (ev.target?.name === "due") this.setDueDate(ev.target.value);
    if (ev.target?.name === "reason") this.setReason(ev.target.value);
  }

  _render() {
    const task = this.task;
    const meta = [shortSubject(task.subject), task.setter].filter(Boolean).map(escapeHtml).join(" · ");
    const chips = QUICK_REASONS.map(
      (r) => `<button class="chip" data-action="reason" data-reason="${escapeHtml(r)}">${escapeHtml(r)}</button>`,
    ).join("");
    const history = (task.history || []).map((h) => `<div>${historyText(h)}</div>`).join("");
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="backdrop">
        <div class="dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(task.title)}">
          <h2>${escapeHtml(task.title)}</h2>
          <div class="meta">${meta} · Not submitted</div>
          <label>Firefly says due</label>
          <div class="readonly">${formatDay(task.firefly_due) || "No due date"}</div>
          <label for="due">New due date</label>
          <input id="due" name="due" type="date" value="${escapeHtml(this.dueDate)}">
          <label for="reason">Why? (optional)</label>
          <input id="reason" name="reason" maxlength="${MAX_REASON}" value="${escapeHtml(this.reason)}">
          <div class="chips">${chips}</div>
          ${this.message ? `<div class="message">${escapeHtml(this.message)}</div>` : ""}
          <div class="buttons">
            ${task.change ? `<button class="action" data-action="undo">Undo change</button>` : ""}
            <button class="action" data-action="cancel">Cancel</button>
            <button class="action primary" data-action="save">Save</button>
          </div>
          <div class="history"><div><b>History</b></div>${history}</div>
        </div>
      </div>`;
  }
}

if (!customElements.get(TAG)) customElements.define(TAG, FireflyTaskDialog);

/** Open the change dialog for a task; it fires "firefly-task-changed" after a save or undo. */
export function openTaskDialog({ hass, entityId, task }) {
  const dialog = document.createElement(TAG);
  dialog.init({ hass, entityId, task });
  document.body.appendChild(dialog);
  return dialog;
}
