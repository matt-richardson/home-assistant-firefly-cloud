// Pure logic and HTML rendering for the Firefly upcoming classes card. No DOM access, so it's unit-tested
// with node --test. Subjects and rooms from Firefly go through escapeHtml.
// (escapeHtml and the date helpers are repeated from tasks-logic.js on purpose: importing that file here
// without the card's ?v= version could load a stale cached copy after an upgrade.)

export const DEFAULT_KIT_SUBJECTS = ["PE", "Physical Education", "Sport", "Games", "Swimming"];
const STRIP_DAYS = 5;
const WHOLE_WORD_MAX_LENGTH = 3;

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const toUtc = (iso) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};
const dayName = (iso) => DAY_NAMES[toUtc(iso).getUTCDay()];
const longDate = (iso) => `${toUtc(iso).getUTCDate()} ${MONTH_NAMES[toUtc(iso).getUTCMonth()]}`;
const shortDate = (iso) => `${toUtc(iso).getUTCDate()} ${MONTH_NAMES[toUtc(iso).getUTCMonth()].slice(0, 3)}`;

/** Case-insensitive match of a subject against a list; short entries (like "PE") must match a whole word. */
function matchesAny(subject, list) {
  const text = String(subject ?? "").toLowerCase();
  return (list || []).some((entry) => {
    const needle = String(entry).trim().toLowerCase();
    if (!needle) return false;
    if (needle.length <= WHOLE_WORD_MAX_LENGTH) {
      return text.split(/[^a-z0-9]+/).includes(needle);
    }
    return text.includes(needle);
  });
}

export const isKit = (subject, kitList) => matchesAny(subject, kitList);
export const isHidden = (subject, hideList) => matchesAny(subject, hideList);

/** "Year 8 Mathematics" → "Mathematics"; anything else unchanged. */
export const shortName = (subject) => String(subject ?? "").replace(/^Year \d+\s+/i, "");

/** Lesson days with hidden subjects removed, dropping days left empty. */
export function visibleDays(overview, config) {
  const hide = config.hide_subjects || [];
  return overview.lesson_days
    .map((day) => ({ date: day.date, lessons: day.lessons.filter((l) => !isHidden(l.subject, hide)) }))
    .filter((day) => day.lessons.length > 0);
}

/** The day to show: today until its last lesson ends, otherwise the next day with lessons. */
export function nextSchoolDay(days, today, time) {
  const todayDay = days.find((d) => d.date === today);
  if (todayDay && todayDay.lessons.some((l) => l.end > time)) return { date: today, reason: "today" };
  const next = days.find((d) => d.date > today);
  if (!next) return null;
  return { date: next.date, reason: todayDay ? "after_school" : "weekend_or_break" };
}

export function stripDays(days, fromDate, n = STRIP_DAYS) {
  return days.filter((d) => d.date >= fromDate).slice(0, n);
}

/** Tasks due on each date (by the date in force), ignoring overdue tasks and tasks with no date. */
export function dueCountByDate(tasks) {
  const result = {};
  for (const task of tasks) {
    if (!task.due || task.bucket === "overdue" || task.bucket === "no_date") continue;
    result[task.due] = (result[task.due] || 0) + 1;
  }
  return result;
}

function contextNote(shown, today) {
  if (shown.reason === "after_school") return `Showing ${dayName(shown.date)} because today's lessons have finished.`;
  if (shown.reason === "weekend_or_break") {
    const weekend = [0, 6].includes(toUtc(today).getUTCDay());
    return `Showing ${dayName(shown.date)} because ${weekend ? "school's out for the weekend" : "there are no lessons today"}.`;
  }
  return "";
}

export const CARD_STYLE = `
  h2 { margin: 0; font-size: 1.15em; font-weight: 500; }
  h2 small { font-weight: 400; color: var(--secondary-text-color); font-size: 0.75em; margin-left: 6px; }
  .note { color: var(--secondary-text-color); font-size: 0.85em; margin: 4px 0 0; }
  h2 + .lesson, .note + .lesson { margin-top: 10px; }
  .lesson { display: grid; grid-template-columns: 52px 1fr auto; gap: 10px; padding: 6px 0;
    border-top: 1px solid var(--divider-color); }
  .lesson .t, .lesson .room { color: var(--secondary-text-color); }
  .lesson.kit .n { color: var(--success-color, #43a047); }
  .strip { display: grid; grid-template-columns: repeat(${STRIP_DAYS}, 1fr); gap: 6px; margin-top: 14px; padding-top: 12px;
    border-top: 1px solid var(--divider-color); }
  .strip button { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 4px;
    font: inherit; font-size: 0.8em; border: 0; border-radius: 8px; padding: 6px 2px;
    background: var(--secondary-background-color); color: inherit; cursor: pointer; }
  /* One line under the day name for the t-shirt and/or the due count, the same height on every day */
  .marks { display: flex; align-items: center; justify-content: center; gap: 4px; min-height: 18px; }
  .strip button[aria-current="true"] { outline: 2px solid var(--primary-color); }
  /* White t-shirt for kit days; the faint outline keeps it visible on light themes */
  .kit-icon { color: #fff; --mdc-icon-size: 18px; filter: drop-shadow(0 0 1px rgba(0, 0, 0, 0.7)); }
  .strip .due { color: var(--warning-color, #ffa600); }
  .empty { color: var(--secondary-text-color); padding: 8px 0; }
`;

function stripButton(day, shownDate, kitList, dueCounts) {
  const kit = day.lessons.some((l) => isKit(l.subject, kitList));
  const due = dueCounts[day.date] || 0;
  const label = [`${dayName(day.date)} ${longDate(day.date)}`, kit && "kit day", due && `${due} task${due === 1 ? "" : "s"} due`]
    .filter(Boolean)
    .join(", ");
  const current = day.date === shownDate ? ' aria-current="true"' : "";
  const marks =
    (kit ? `<ha-icon class="kit-icon" icon="mdi:tshirt-crew"></ha-icon>` : "") +
    (due ? `<span class="due">${due} due</span>` : "");
  return `<button data-date="${day.date}" aria-label="${escapeHtml(label)}"${current}><b>${dayName(day.date).slice(
    0,
    3,
  )}</b><span class="marks">${marks}</span></button>`;
}

/** The card: the next school day (or the selected one) in detail, with a strip of the coming school days. */
export function renderClassesCard(overview, config, selectedDate, today, time) {
  const kitList = config.kit_subjects || DEFAULT_KIT_SUBJECTS;
  const days = visibleDays(overview, config);
  const next = nextSchoolDay(days, today, time);
  if (!next) return `<div class="empty">No timetable from your school for the next two weeks</div>`;

  const shownDate = selectedDate && days.some((d) => d.date === selectedDate) ? selectedDate : next.date;
  const shown = days.find((d) => d.date === shownDate);
  const note = shownDate === next.date ? contextNote(next, today) : "";
  const when = shownDate === today ? "today" : shownDate === next.date ? "next school day" : "";

  const lessons = shown.lessons
    .map(
      (l) =>
        `<div class="lesson${isKit(l.subject, kitList) ? " kit" : ""}"><span class="t">${escapeHtml(l.start)}</span>` +
        `<span class="n">${escapeHtml(shortName(l.subject))}</span><span class="room">${escapeHtml(l.location)}</span></div>`,
    )
    .join("");
  const dueCounts = dueCountByDate(overview.tasks);
  const strip = stripDays(days, next.date)
    .map((day) => stripButton(day, shownDate, kitList, dueCounts))
    .join("");

  return `
    <h2>${dayName(shownDate)} <small>${shortDate(shownDate)}${when ? ` · ${when}` : ""}</small></h2>
    ${note ? `<p class="note">${escapeHtml(note)}</p>` : ""}
    ${lessons}
    <div class="strip">${strip}</div>`;
}
