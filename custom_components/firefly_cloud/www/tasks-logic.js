// Pure logic and HTML rendering for the Firefly tasks card. No DOM access, so it's unit-tested with node --test.
// Everything from Firefly or typed by a user (titles, subjects, teachers, reasons, labels) goes through escapeHtml.

export const QUICK_REASONS = ["Doing it in class today", "Extended in class", "Teacher emailed", "Firefly is wrong"];

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DASHBOARD_COLOR = "#9c6ade";

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Dates are local calendar dates as YYYY-MM-DD; do the maths in UTC so the browser's timezone never shifts them.
const toUtc = (iso) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};

export function daysBetween(fromIso, toIso) {
  return Math.round((toUtc(toIso) - toUtc(fromIso)) / 86400000);
}

/** "Year 8 Mathematics" → "Mathematics"; anything else unchanged. */
export const shortSubject = (subject) => (subject ? String(subject).replace(/^Year \d+\s+/i, "") : subject);

/** "Wed 11 Nov" for a YYYY-MM-DD date (or the date part of an ISO timestamp). */
export function formatDay(iso) {
  if (!iso) return "";
  const d = toUtc(iso);
  return `${DAY_NAMES[d.getUTCDay()]} ${d.getUTCDate()} ${MONTH_NAMES[d.getUTCMonth()]}`;
}

export function counts(tasks) {
  const result = { overdue: 0, this_week: 0, later: 0 };
  for (const task of tasks) {
    if (task.bucket in result) result[task.bucket] += 1;
  }
  return result;
}

/** How far away or late a task is, and the tone used to colour it. */
export function relativeDue(task, today) {
  const tone = task.bucket === "overdue" ? "late" : task.bucket === "this_week" ? "soon" : "later";
  if (!task.due) return { text: "no due date", tone: "later" };
  const days = daysBetween(today, task.due);
  if (days < 0) return { text: `${-days} day${days === -1 ? "" : "s"} late`, tone };
  if (days === 0) return { text: "due today", tone };
  if (days === 1) return { text: "tomorrow", tone };
  return { text: `in ${days} days`, tone };
}

/** The purple tag for a dashboard change or note (escaped HTML), or null. */
export function changeTag(task, label) {
  const change = task.change;
  if (!change) return null;
  if (change.kind === "note") return `✎ Note: ${escapeHtml(change.reason)}`;
  const who = label ? `${escapeHtml(label)} moved from` : "Changed on dashboard from";
  const parts = [`✎ ${who} <s>${formatDay(change.from)}</s>`];
  if (change.reason) parts.push(`"${escapeHtml(change.reason)}"`);
  parts.push(formatDay(change.changed_at));
  if (change.confirmed) parts.push("confirmed by school");
  return parts.join(" · ");
}

/** The blue tag for the latest change Firefly itself made to the date (escaped HTML), or null. */
export function schoolTag(task) {
  const school = task.school_change;
  if (!school) return null;
  const seen = `seen ${formatDay(school.seen_at)}`;
  if (!school.from) return `↻ School set the due date · ${seen}`;
  if (!school.to) return `↻ School removed the due date · ${seen}`;
  return `↻ School moved from <s>${formatDay(school.from)}</s> · ${seen}`;
}

export const CARD_STYLE = `
  .header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
  .header h2 { margin: 0; font-size: 1.15em; font-weight: 500; }
  .counts { display: flex; gap: 8px; margin-bottom: 8px; }
  .count { flex: 1; text-align: center; border-radius: 10px; padding: 6px; background: var(--secondary-background-color); }
  .count b { display: block; font-size: 1.4em; }
  .count span { font-size: 0.8em; color: var(--secondary-text-color); }
  .late { color: var(--error-color, #db4437); }
  .soon { color: var(--warning-color, #ffa600); }
  .later { color: var(--secondary-text-color); }
  .task { display: flex; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider-color); cursor: pointer; }
  .task:first-of-type { border-top: 0; }
  .task:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .bar { width: 4px; border-radius: 2px; flex: none; background: var(--divider-color); }
  .bar.late { background: var(--error-color, #db4437); }
  .bar.soon { background: var(--warning-color, #ffa600); }
  .body { flex: 1; min-width: 0; }
  .title { font-weight: 500; }
  .meta { color: var(--secondary-text-color); font-size: 0.9em; }
  .due { text-align: right; white-space: nowrap; font-size: 0.9em; }
  .due b { display: block; }
  .tag { display: inline-block; margin-top: 6px; font-size: 0.85em; padding: 3px 8px; border-radius: 8px; }
  .tag.dashboard { color: ${DASHBOARD_COLOR}; border: 1px solid ${DASHBOARD_COLOR}; }
  .tag.school { color: var(--info-color, #039be5); border: 1px solid var(--info-color, #039be5); }
  .empty, .error { color: var(--secondary-text-color); padding: 8px 0; }
  .error { color: var(--error-color, #db4437); }
`;

function renderRow(task, today, label) {
  const due = relativeDue(task, today);
  const meta = [shortSubject(task.subject), task.setter].filter(Boolean).map(escapeHtml).join(" · ");
  const tags = [
    changeTag(task, label) && `<div class="tag dashboard">${changeTag(task, label)}</div>`,
    schoolTag(task) && `<div class="tag school">${schoolTag(task)}</div>`,
  ]
    .filter(Boolean)
    .join("");
  return `
    <div class="task" data-task-id="${escapeHtml(task.id)}" role="button" tabindex="0">
      <div class="bar ${due.tone}"></div>
      <div class="body">
        <div class="title">${escapeHtml(task.title)}</div>
        <div class="meta">${meta}</div>
        ${tags}
      </div>
      <div class="due ${due.tone}"><b>${due.text}</b>${formatDay(task.due)}</div>
    </div>`;
}

export function renderTasksCard(overview, config) {
  const c = counts(overview.tasks);
  const rows = overview.tasks.length
    ? overview.tasks.map((task) => renderRow(task, overview.today, config.changed_by_label || "")).join("")
    : `<div class="empty">No open tasks 🎉</div>`;
  return `
    <div class="header"><h2>${escapeHtml(config.title || "Tasks")}</h2></div>
    <div class="counts">
      <div class="count"><b class="late">${c.overdue}</b><span>overdue</span></div>
      <div class="count"><b class="soon">${c.this_week}</b><span>due this week</span></div>
      <div class="count"><b>${c.later}</b><span>later</span></div>
    </div>
    ${rows}`;
}

export function renderError(message) {
  return `<div class="error">${escapeHtml(message)}</div>`;
}

/** One line of a task's history, newest first in the dialog (escaped HTML). */
export function historyText(entry) {
  const f = entry.text_fields || {};
  let text;
  switch (entry.kind) {
    case "set":
      text = ["Set", f.setter && `by ${escapeHtml(f.setter)}`].filter(Boolean).join(" ") + (f.due ? `, due ${formatDay(f.due)}` : "");
      break;
    case "dashboard":
      text = [
        `Moved from ${formatDay(f.from)} to ${formatDay(f.new_due_date)}`,
        f.reason && `"${escapeHtml(f.reason)}"`,
        f.confirmed && "confirmed by school",
      ]
        .filter(Boolean)
        .join(" · ");
      break;
    case "note":
      text = `Note: ${escapeHtml(f.reason)}`;
      break;
    case "undone":
      text = f.new_due_date ? `Undid the move to ${formatDay(f.new_due_date)}` : "Undid the note";
      break;
    default:
      text = f.from && f.to ? `School moved from ${formatDay(f.from)} to ${formatDay(f.to)}` : "School changed the due date";
  }
  return entry.at ? `${formatDay(entry.at)} · ${text}` : text;
}
