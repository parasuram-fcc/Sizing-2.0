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
// validateAndCheckQuote(inputSel, feedbackSel, btnSel, [projId])
// Validates a quote-number field (format + server uniqueness) and wires
// feedback text / input border / submit-button state in one call.
//
// inputSel    — jQuery selector for the quote <input>
// feedbackSel — jQuery selector for the feedback <small>/<span>
// btnSel      — jQuery selector for the submit button to enable/disable
// projId      — (optional) project id to exclude from the uniqueness check
//               (edit-project scenario)
//
// Validation order: empty → bad first char → non-digits after Q →
// incomplete length → server uniqueness check.
// One XHR is tracked per inputSel; starting a new check aborts the previous
// so rapid typing never races.
// ---------------------------------------------------------------------------
window.validateAndCheckQuote = (function () {
    var _xhrMap = {};   // one in-flight XHR per input selector

    return function (inputSel, feedbackSel, btnSel, projId) {
        var val  = ($(inputSel).val() || '').trim();
        var $fb  = $(feedbackSel);
        var $inp = $(inputSel);

        function setFeedback(text, state) {
            $fb.text(text);
            $fb.removeClass('text-success text-danger text-muted text-warning');
            $inp.css('border-color', '');
            if (state === 'ok') {
                $fb.addClass('text-success');
                $inp.css('border-color', '#198754');
            } else if (state === 'error') {
                $fb.addClass('text-danger');
                $inp.css('border-color', '#dc3545');
            } else if (state === 'checking') {
                $fb.addClass('text-muted');
            }
        }

        function setBtn(enabled) {
            $(btnSel).prop('disabled', !enabled);
        }

        /* ── Format checks (client-side) ── */
        if (val.length === 0) {
            setFeedback('', '');
            setBtn(false);
            return;
        }

        if (val[0] !== 'Q') {
            setFeedback('Must start with Q', 'error');
            setBtn(false);
            return;
        }

        if (val.length > 1 && !/^\d+$/.test(val.slice(1))) {
            setFeedback('After Q, only digits are allowed', 'error');
            setBtn(false);
            return;
        }

        if (val.length < 8) {
            setFeedback('Enter 7 digits after Q (' + val.length + '/8)', 'checking');
            setBtn(false);
            return;
        }

        /* ── Format OK → server uniqueness check ── */
        setFeedback('Checking\u2026', 'checking');
        setBtn(false);

        if (_xhrMap[inputSel]) { _xhrMap[inputSel].abort(); }

        var params = { quote: val };
        if (projId) { params.proj_id = projId; }

        _xhrMap[inputSel] = $.get('/project/check_quote', params)
            .done(function (data) {
                if (data.is_exists) {
                    setFeedback('Quote number already exists', 'error');
                    setBtn(false);
                } else {
                    setFeedback('Available', 'ok');
                    setBtn(true);
                }
            })
            .fail(function (xhr) {
                if (xhr.statusText !== 'abort') {
                    setFeedback('Could not verify \u2014 try again', 'error');
                    setBtn(false);
                }
            });
    };
}());

// ---------------------------------------------------------------------------
// showFlash(message, category)
// Injects a flash message into .flash-message-container and auto-removes it.
// category: 'success' | anything else → failure styling.
// ---------------------------------------------------------------------------
window.showFlash = function (message, category) {
    var $container = $('.flash-message-container');
    var cssClass   = category === 'success' ? 'flash-success' : 'flash-failure';
    var $msg = $('<ul class="flash-messages ' + cssClass + '"><li>' + message + '</li></ul>');
    $container.empty().append($msg).show();
    setTimeout(function () {
        $msg.fadeOut(400, function () {
            $(this).remove();
            $container.hide();
        });
    }, 3000);
};

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
