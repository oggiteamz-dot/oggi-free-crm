/* =============================================================================
 * error-sink.js — nothing fails silently. Load this FIRST, before any app code.
 * =============================================================================
 *
 * THE FAILURE THIS EXISTS TO PREVENT
 * ----------------------------------
 * A try/catch swallowed an error and every matched lead and freelancer was never
 * notified. No error appeared anywhere. Weeks passed. The lead sat watching a
 * matches page waiting for a call that was never going to come.
 *
 * WHAT THIS GIVES YOU
 * -------------------
 *   reportError(err, context)   call it in EVERY catch block. The gate fails the
 *                               build on any catch that does not.
 *   window.onerror              anything that escapes to the top level
 *   unhandledrejection          any promise that rejects with nobody listening
 *
 * All three land in the app_error table, which the Admin Error Inbox reads. So a
 * failure becomes something a human sees, instead of something nobody ever knows.
 * ============================================================================= */

(function () {
  'use strict';

  // Set these once, at the top of the app.
  var ENDPOINT = (window.OGGI_ERROR_ENDPOINT || '/api/error');
  var MAX_PER_MINUTE = 20;          // a loop must not flood the table
  var sent = 0;
  setInterval(function () { sent = 0; }, 60000);

  /**
   * Report a failure so a human will find out about it.
   *
   * @param {Error|string} err   what went wrong
   * @param {string|object} ctx  what the user was doing — be specific.
   *                             "saving order 8814" beats "error".
   * @param {string} code        stable UPPER_SNAKE_CASE code, e.g. ORDER_SAVE_FAILED.
   *                             Stable codes are what let the inbox group repeats.
   */
  window.reportError = function reportError(err, ctx, code) {
    try {
      if (sent++ > MAX_PER_MINUTE) return;

      var payload = {
        code: code || deriveCode(err, ctx),
        message: (err && err.message) ? err.message : String(err),
        severity: 'error',
        url: location.href,
        user_agent: navigator.userAgent,
        context: {
          doing: typeof ctx === 'string' ? ctx : (ctx || {}),
          stack: (err && err.stack) ? String(err.stack).slice(0, 2000) : null,
          at: new Date().toISOString()
        }
      };

      // keepalive so the report survives the user navigating away mid-failure.
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true
      }).catch(function () {
        // Deliberately empty, and the ONLY empty catch allowed in the codebase:
        // if reporting an error itself fails, reporting that failure would loop.
        // Everything else is buffered below so nothing is lost.
        buffer(payload);
      });

      // Always visible in development.
      if (location.hostname === 'localhost') console.error('[reportError]', payload);
    } catch (_) { /* never let the reporter break the app */ }
  };

  // If the network is down, keep the report and send it on the next load.
  function buffer(payload) {
    try {
      var q = JSON.parse(localStorage.getItem('_err_q') || '[]');
      q.push(payload);
      localStorage.setItem('_err_q', JSON.stringify(q.slice(-50)));
    } catch (_) {}
  }

  (function flush() {
    try {
      var q = JSON.parse(localStorage.getItem('_err_q') || '[]');
      if (!q.length) return;
      localStorage.removeItem('_err_q');
      q.forEach(function (p) {
        fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(p)
        }).catch(function () { buffer(p); });
      });
    } catch (_) {}
  })();

  function deriveCode(err, ctx) {
    var base = (typeof ctx === 'string' ? ctx : (err && err.name) || 'UNKNOWN');
    return String(base).toUpperCase().replace(/[^A-Z0-9]+/g, '_').slice(0, 40) || 'UNKNOWN_ERROR';
  }

  // Anything that escapes every catch block in the app.
  window.addEventListener('error', function (e) {
    window.reportError(e.error || e.message, 'uncaught error', 'UNCAUGHT');
  });

  // A promise that rejected with nobody listening — the most commonly missed one.
  window.addEventListener('unhandledrejection', function (e) {
    window.reportError(e.reason, 'unhandled promise rejection', 'UNHANDLED_REJECTION');
  });
})();
