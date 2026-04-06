/**
 * app/static/js/common/utils.js
 * Shared utilities for auth pages.
 * Requires jQuery to be loaded before this file.
 */

// ---------------------------------------------------------------------------
// debounce(fn, delay)
// Returns a function that delays invoking `fn` until `delay` ms have elapsed
// since the last call. Prevents rapid-fire API calls on input events.
// ---------------------------------------------------------------------------
function debounce(fn, delay) {
    var timer;
    return function () {
        var context = this;
        var args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () {
            fn.apply(context, args);
        }, delay);
    };
}

// ---------------------------------------------------------------------------
// RequestManager
// Wraps $.ajax so that starting a new request automatically aborts the
// previous one. Prevents duplicate in-flight requests for the same endpoint.
//
// Usage:
//   var rm = new RequestManager();
//   rm.send({ url: '/auth/send_otp', data: { emailID: val }, success: fn });
// ---------------------------------------------------------------------------
function RequestManager() {
    this._xhr = null;
}

RequestManager.prototype.send = function (ajaxOptions) {
    if (this._xhr && this._xhr.readyState !== 4) {
        this._xhr.abort();
    }
    this._xhr = $.ajax(ajaxOptions);
    return this._xhr;
};

// ---------------------------------------------------------------------------
// checkQuoteNumber(val, feedbackEl, [callback])
// Validates a quote-number string (format + server uniqueness check).
//
// val        — the raw input string (will be trimmed internally)
// feedbackEl — DOM element used to display status messages
// callback   — optional fn(isValid) called after all checks complete;
//              isValid is true only when the format is correct AND the
//              quote is available on the server.
//
// Validation is step-by-step (empty → bad first char → non-digits →
// incomplete length → server check). In-flight requests are aborted when a
// new call arrives so rapid typing never races.
// ---------------------------------------------------------------------------
window.checkQuoteNumber = (function () {
    var _xhr = null;   // track in-flight request so we can abort on fast typing

    return function (val, feedbackEl, callback) {
        val = (val || '').trim();

        function setFeedback(text, cls) {
            feedbackEl.textContent = text;
            feedbackEl.className   = 'form-text' + (cls ? ' ' + cls : '');
        }

        /* ── Step-by-step client-side checks ── */
        if (val.length === 0) {
            setFeedback('', '');
            if (callback) callback(false);
            return;
        }

        if (val[0] !== 'Q') {
            setFeedback('Must start with Q', 'text-danger');
            if (callback) callback(false);
            return;
        }

        if (val.length > 1 && !/^\d+$/.test(val.slice(1))) {
            setFeedback('After Q, only digits are allowed', 'text-danger');
            if (callback) callback(false);
            return;
        }

        if (val.length < 8) {
            setFeedback('Enter 7 digits after Q (' + val.length + '/8)', 'text-muted');
            if (callback) callback(false);
            return;
        }

        /* ── Format OK (Q + 7 digits) → check uniqueness via API ── */
        setFeedback('Checking\u2026', 'text-muted');

        if (_xhr) { _xhr.abort(); }

        _xhr = $.get('/check_quote', { quote: val })
            .done(function (data) {
                if (data.is_exists) {
                    setFeedback('Quote number already exists.', 'text-danger');
                    if (callback) callback(false);
                } else {
                    setFeedback('Available', 'text-success');
                    if (callback) callback(true);
                }
            })
            .fail(function (xhr) {
                if (xhr.statusText !== 'abort') {
                    setFeedback('Could not verify \u2014 try again', 'text-warning');
                    if (callback) callback(false);
                }
            });
    };
}());

// ---------------------------------------------------------------------------
// showNotification(message, type)
// Displays a fixed top-right toast. type: 'success' | 'error' | 'warning'
// Auto-dismisses after 3 seconds.
// ---------------------------------------------------------------------------
(function () {
    var COLORS = {
        success: '#2e7d32',
        error:   '#c62828',
        warning: '#e65100'
    };

    window.showNotification = function (message, type) {
        var color = COLORS[type] || COLORS.warning;

        var $toast = $('<div>')
            .css({
                position:     'fixed',
                top:          '18px',
                right:        '18px',
                background:   color,
                color:        '#fff',
                padding:      '12px 20px',
                borderRadius: '8px',
                fontSize:     '14px',
                fontFamily:   '"Inter", sans-serif',
                boxShadow:    '0 4px 12px rgba(0,0,0,0.2)',
                zIndex:       9999,
                maxWidth:     '320px',
                lineHeight:   '1.4',
                opacity:      0
            })
            .text(message);

        $('body').append($toast);
        $toast.animate({ opacity: 1 }, 200);

        setTimeout(function () {
            $toast.animate({ opacity: 0 }, 300, function () {
                $toast.remove();
            });
        }, 3000);
    };
}());
