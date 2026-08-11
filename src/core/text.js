// core/text.js — every word a customer reads comes from here, never from the code.
//
// This is what makes "edit any text whenever I want" true, and what gives the
// writer / copywriter / QC roles something to actually edit. A key with no value
// renders a LOUD marker rather than a blank, so an unfinished screen cannot be
// mistaken for a finished one.

let STRINGS = {};

export async function loadText(api) {
  try {
    STRINGS = await api.getPublishedText();     // reads content_published
  } catch (err) {
    reportError(err, 'loading the product text');
    STRINGS = {};
  }
}

export function t(key) {
  const v = STRINGS[key];
  return (v === undefined || v === null || v === '') ? `⟦MISSING:${key}⟧` : v;
}

/** Use for anything a person typed. Never put raw input into innerHTML. */
export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
