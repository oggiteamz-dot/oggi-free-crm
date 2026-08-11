// core/router.js — which screen is showing. One entry per screen, nothing else.
//
// Every screen id here must also appear in SCREENMAP.md, which blockout_check.py
// uses to prove there are no orphan screens and no dead ends.

const routes = new Map();
export function screen(id, render) { routes.set(id, render); }

export function go(id) {
  if (location.hash !== '#' + id) { location.hash = id; return; }
  paint();
}

export function paint() {
  const id = location.hash.slice(1) || 'screen-home';
  const app = document.getElementById('app');
  const render = routes.get(id);

  if (!render) {
    app.dataset.screen = 'screen-not-found';
    app.textContent = 'That screen does not exist.';   // never a blank page
    reportError(new Error('unknown screen: ' + id), 'routing');
    return;
  }
  app.dataset.screen = id;
  app.replaceChildren();
  render(app);
}

addEventListener('hashchange', paint);
