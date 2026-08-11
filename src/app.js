// app.js — the shell. Loads text, loads saved data, then paints. Nothing else.
//
// Keep this file small. Anything that grows belongs in core/ or in its own
// feature folder. A shell that accumulates logic becomes the monolith again.

import { paint } from './core/router.js';
import { hydrate } from './core/store.js';
import { loadText } from './core/text.js';

// import every feature — one line each, added as each is built
// import './features/contacts/index.js';

(async function start() {
  try {
    // await loadText(api);
    // await hydrate(api);
    paint();
  } catch (err) {
    reportError(err, 'starting the app');
    document.getElementById('app').textContent =
      'Something went wrong starting up. Please refresh.';   // never a blank page
  }
})();
