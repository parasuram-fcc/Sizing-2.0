/* =============================================
   header.js — Global layout / navigation logic
   Loaded on every page via common/header.html

   Jinja2 values passed via hidden inputs:
     #hdrUserId   — current_user.id
     #hdrUserName — current_user.name
   ============================================= */

/* =================== NAVIGATION GUARD =================== */
// Prevents accidental tab-close / refresh while unsaved work exists.
// Set allowNavigation = true before any intentional navigation.

let allowNavigation = false;

// Mark navigation as intentional when any link or submit is clicked.
document.addEventListener("click", function (e) {
    if (e.target.closest("a") || e.target.tagName === "A") {
        allowNavigation = true;
    }
});

document.addEventListener("submit", function () {
    allowNavigation = true;
});

// Keyboard shortcuts: F5 / Ctrl+R are intentional reloads.
window.addEventListener("keydown", function (e) {
    if (e.key === "F5" || (e.ctrlKey && e.key === "r")) {
        allowNavigation = true;
    }
});

// Reset flag when page is restored from back/forward cache.
window.addEventListener("pageshow", function () {
    allowNavigation = false;
});

// Warn on unintentional close / refresh.
window.addEventListener("beforeunload", function (event) {
    if (!allowNavigation) {
        event.preventDefault();
        event.returnValue = "";
    }
});


/* =================== UTILITIES =================== */

/**
 * getCurrentIds()
 * Extract proj-<id> and item-<id> from the current URL path.
 * Returns { projectId, itemId } — both strings or undefined.
 */
function getCurrentIds() {
    sessionStorage.getItem('proj_id')
    // const parts = window.location.pathname.split('/');
    return {
        projectId: sessionStorage.getItem('proj_id'),
        itemId:    sessionStorage.getItem('item_id')
    };
}

function fullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen)            elem.requestFullscreen();
    else if (elem.webkitRequestFullscreen) elem.webkitRequestFullscreen();
    else if (elem.msRequestFullscreen)     elem.msRequestFullscreen();
}


/* =================== SIDEBAR NAV-DYNAMIC HANDLER =================== */
// Handles all sidebar and table links that carry a `data-page` attribute.
// Constructs URL as  /<page>/proj-<id>/item-<id>  and navigates.
//
// NOTE: Links carrying `data-action` (page-specific actions) are handled
// separately in each page's own JS file (e.g. dashboard.js).

document.addEventListener("click", function (e) {
    const link = e.target.closest(".nav-dynamic");
    if (!link) return;

    const page = link.dataset.page;
    if (!page) return;          // data-action links — let the page handler deal with them

    e.preventDefault();

    const { projectId, itemId } = getCurrentIds();
    if (!projectId || !itemId) {
        alert("Please select a project and item first");
        return;
    }

    allowNavigation = true;
    window.location.href = `/${page}`; // /proj-${projectId}/item-${itemId}
});


/* =================== FLASH MESSAGES =================== */

document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        flashMessages.classList.add('show');
        setTimeout(() => flashMessages.classList.remove('show'), 5000);
    }
});

$(document).ready(function () {
    setTimeout(function () { $(".flashes").fadeOut('slow'); }, 5000);
});


/* =================== AMPLITUDE ANALYTICS =================== */

window.addEventListener("load", function () {
    const user_id   = document.getElementById('hdrUserId')?.value   || '';
    const user_name = document.getElementById('hdrUserName')?.value || '';

    if (user_id && String(user_id).length >= 5) {
        amplitude.init("7abd972126f84a8268f7bc9d8c4b2674", null, {
            autocapture:     false,
            defaultTracking: false
        });
        amplitude.setUserId(String(user_id));
        amplitude.setUserProperties({ name: user_name });
        amplitude.track("Dashboard Loaded");
    } else {
        console.warn("Invalid user_id for Amplitude");
    }
});


/* =================== INTRO.JS TOUR HELPER =================== */
// Lightweight wrapper that tracks per-page tour completion in localStorage.
// Usage: Tour.start(name, steps, opts) / Tour.isDone(name) / Tour.reset(name)

const Tour = (() => {
    const key    = (n) => `tour:${n}:done`;
    const isDone = (n) => localStorage.getItem(key(n)) === '1';
    const done   = (n) => localStorage.setItem(key(n), '1');
    const reset  = (n) => localStorage.removeItem(key(n));

    const start  = (name, steps, opts = {}) => {
        const filtered = steps.filter(s => !s.element || document.querySelector(s.element));
        if (!filtered.length) return;

        const intro = introJs().setOptions({
            steps:           filtered,
            showProgress:    true,
            showBullets:     false,
            scrollToElement: true,
            ...opts
        });
        intro.oncomplete(() => done(name));
        intro.onexit(()    => done(name));
        intro.start();
    };

    return { isDone, done, reset, start };
})();
