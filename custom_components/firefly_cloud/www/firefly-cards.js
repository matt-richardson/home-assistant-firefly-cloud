// Firefly Cloud dashboard cards, served and registered by the integration.
// Load each card with this file's own ?v= version, so an upgrade never mixes new and cached older files.
const version = new URL(import.meta.url).search;
await import(new URL("./firefly-tasks-card.js" + version, import.meta.url));
await import(new URL("./firefly-classes-card.js" + version, import.meta.url));
