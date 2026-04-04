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
