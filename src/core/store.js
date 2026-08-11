// core/store.js — the ONLY place that decides what gets saved.
//
// DATA_KEYS is the save list. If the app writes a key that is not on this list,
// the value survives until reload on the device that made it and NEVER reaches
// anyone else's device — the single most expensive bug in this estate, and one
// that was marked "done and tested" while permanently broken for customers.
//
// The `persistence` check compares what the app writes against this list and
// fails the build on any mismatch. Keep it accurate and that bug cannot recur.

export const DATA_KEYS = [
  // Every key the app saves. Add one line per key, as features are built.
  // A key written by the UI but missing from this list is THE bug that shipped
  // broken to real customers: it works until reload, and never once works on
  // anyone else's device.
];

export const STATE = {};

const LOCAL = 'app.state.v1';

/** Save to the server first; local storage is only a cache for offline. */
export async function persist(api) {
  const payload = {};
  for (const k of DATA_KEYS) payload[k] = STATE[k];

  try {
    localStorage.setItem(LOCAL, JSON.stringify(payload));   // cache
  } catch (err) {
    reportError(err, 'caching state locally');              // never silent
  }

  if (!api) return;
  try {
    await api.saveState(payload);                           // the real save
  } catch (err) {
    reportError(err, 'saving state to the server');
    throw err;   // the caller must show the user something. Never swallow.
  }
}

/** Load from the SERVER first, so a second device sees the same thing. */
export async function hydrate(api) {
  if (api) {
    try {
      const remote = await api.loadState();
      if (remote) { Object.assign(STATE, remote); return 'server'; }
    } catch (err) {
      reportError(err, 'loading state from the server');
    }
  }
  try {
    const cached = JSON.parse(localStorage.getItem(LOCAL) || '{}');
    Object.assign(STATE, cached);
    return 'cache';
  } catch (err) {
    reportError(err, 'reading the local cache');
    return 'empty';
  }
}
