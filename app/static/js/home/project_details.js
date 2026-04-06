/**
 * project_details.js — Add Project page behaviour
 *
 * Data contract (set by project_details.html via <script> block):
 *   CUSTOMER_NAMES  — { companyName: [address, ...], ... }
 *   UNITS_DICT      — { vol_flow_liq: [...], mass_flowrate: [...],
 *                       dynamic_viscosity: [...], kinematic_viscosity: [...],
 *                       vol_flow_gas: [...] }
 */

/* ── Company → Address cascade ─────────────────────────────────────────── */

function companyAddress(companySelector, addressSelector, companyNames) {
    $(companySelector).on('change', function () {
        var selectedCompany  = $(this).val();
        var addressDropdown  = $(addressSelector);

        addressDropdown.empty();

        if (selectedCompany && companyNames[selectedCompany]) {
            $.each(companyNames[selectedCompany], function (index, address) {
                addressDropdown.append(
                    $('<option>', { value: address, text: address })
                );
            });
        }
    });
}

/* ── Unit-list rebuilders ───────────────────────────────────────────────── */

function rebuildUnits(selectId, units) {
    var $sel = $(selectId);
    $sel.empty();
    $.each(units, function (i, unit) {
        $sel.append($('<option>', { value: unit.id, text: unit.name }));
    });
}

/* ── Quote-number validation ────────────────────────────────────────────── */

/**
 * Show feedback text and colour under the quote input.
 * state: 'ok' | 'error' | 'checking' | ''
 */
function setQuoteFeedback(msg, state) {
    var $fb  = $('#quoteno-feedback');
    var $inp = $('#quoteno');
    $fb.text(msg);
    $fb.removeClass('text-success text-danger text-muted');
    /* Do NOT add is-valid / is-invalid to the input — those classes change
       padding-right (validation icon) and cause the field to resize. */
    $inp.css('border-color', '');   // reset any previous override
    if (state === 'ok') {
        $fb.addClass('text-success');
        $inp.css('border-color', '#198754');   // green border only
    } else if (state === 'error') {
        $fb.addClass('text-danger');
        $inp.css('border-color', '#dc3545');   // red border only
    } else if (state === 'checking') {
        $fb.addClass('text-muted');
    }
}

/**
 * Enable or disable the Add Project button.
 * For non-FCC users the button is always enabled (no quote check needed).
 */
function setSubmitEnabled(enabled) {
    $('#add-project-btn').prop('disabled', !enabled);
}

var _quoteCheckXhr = null;   // track in-flight AJAX so we can abort on fast typing

function validateAndCheckQuote() {
    if (!IS_FCC_PROJ) { return; }   // nothing to do for non-FCC project types

    var val = $('#quoteno').val();

    /* ── Format checks (client-side, no network needed) ─────────────────── */
    if (val.length === 0) {
        setQuoteFeedback('', '');
        setSubmitEnabled(false);
        return;
    }

    if (val[0] !== 'Q') {
        setQuoteFeedback('Must start with Q', 'error');
        setSubmitEnabled(false);
        return;
    }

    if (val.length > 1 && !/^\d+$/.test(val.slice(1))) {
        setQuoteFeedback('After Q, only digits are allowed', 'error');
        setSubmitEnabled(false);
        return;
    }

    if (val.length < 8) {
        setQuoteFeedback('Enter 7 digits after Q (' + val.length + '/8)', 'checking');
        setSubmitEnabled(false);
        return;
    }

    /* ── Length == 8 and format OK → check uniqueness via API ───────────── */
    setQuoteFeedback('Checking…', 'checking');
    setSubmitEnabled(false);

    if (_quoteCheckXhr) { _quoteCheckXhr.abort(); }

    var projId = $('#quoteno').data('proj-id') || null;   // set on edit-project page
    var params = { quote: val };
    if (projId) { params.proj_id = projId; }

    _quoteCheckXhr = $.get('/check_quote', params)
        .done(function (data) {
            if (data.is_exists) {
                setQuoteFeedback('Quote number already exists', 'error');
                setSubmitEnabled(false);
            } else {
                setQuoteFeedback('Available', 'ok');
                setSubmitEnabled(true);
            }
        })
        .fail(function (xhr) {
            if (xhr.statusText !== 'abort') {
                setQuoteFeedback('Could not verify — try again', 'error');
                setSubmitEnabled(false);
            }
        });
}

/* ── Document ready ─────────────────────────────────────────────────────── */

$(document).ready(function () {

    /* Disable submit for FCC project type until quote is validated */
    if (IS_FCC_PROJ) {
        setSubmitEnabled(false);
    }

    /* Quote number: live validation */
    $('#quoteno').on('input', function () {
        /* Force uppercase Q */
        var v = $(this).val();
        if (v.length > 0 && v[0] !== 'Q') {
            $(this).val('Q' + v.replace(/^Q*/i, ''));
        }
        validateAndCheckQuote();
    });

    /* Company / address cascades */
    companyAddress('#company',  '#address',  CUSTOMER_NAMES);
    companyAddress('#companyE', '#addressE', CUSTOMER_NAMES);

    /* Viscosity type → unit list */
    $('#viscos').on('change', function () {
        var type  = $(this).val();
        var units = (type === 'dynamic')
            ? UNITS_DICT['dynamic_viscosity']
            : UNITS_DICT['kinematic_viscosity'];
        rebuildUnits('#v_units', units);
    });

    /* Liquid flow type → unit list */
    $('#liq_flow').on('change', function () {
        var type  = $(this).val();
        var units = (type === 'vol')
            ? UNITS_DICT['vol_flow_liq']
            : UNITS_DICT['mass_flowrate'];
        rebuildUnits('#liq_unit', units);
    });

    /* Gas flow type → unit list */
    $('#gas_flow').on('change', function () {
        var type  = $(this).val();
        var units = (type === 'vol')
            ? UNITS_DICT['vol_flow_gas']
            : UNITS_DICT['mass_flowrate'];
        rebuildUnits('#gas_unit', units);
    });

});