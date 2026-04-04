/* =============================================
   footer.js — Global keyboard-navigation helper
   Loaded on every page via common/footer.html
   ============================================= */

// Tab-through form fields on Enter key — prevents accidental form submission
// and moves focus to the next visible, enabled input.
$(':input').keydown(function (e) {
    const key = e.charCode ? e.charCode : e.keyCode ? e.keyCode : 0;
    if (key !== 13) return;

    e.preventDefault();
    const inputs = $(this).closest('form').find(':input:visible:enabled');
    const idx    = inputs.index(this);

    if (idx === inputs.length - 1) {
        $(':input:enabled:visible:first').focus();
    } else {
        inputs.eq(idx + 1).focus();
    }
});
