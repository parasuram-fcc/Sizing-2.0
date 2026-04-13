/**
 * project_details.js — Add Project page behaviour
 *
 * Depends on utils.js (validateAndCheckQuote, showFlash must be loaded first).
 *
 * Data contract (set by project_details.html via <script> block):
 *   CUSTOMER_NAMES  — { companyName: [address, ...], ... }
 *   UNITS_DICT      — { vol_flow_liq: [...], mass_flowrate: [...],
 *                       dynamic_viscosity: [...], kinematic_viscosity: [...],
 *                       vol_flow_gas: [...] }
 *   IS_FCC_PROJ     — boolean
 */

/* ── Company → Address cascade ─────────────────────────────────────────── */

function companyAddress(companySelector, addressSelector, companyNames) {
    $(companySelector).on('change', function () {
        var selectedCompany = $(this).val();
        var addressDropdown = $(addressSelector);

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

/* ── Collect form fields as a plain object ──────────────────────────────── */

function collectFormData() {
    var data = {};
    $('#add-project-form').serializeArray().forEach(function (field) {
        data[field.name] = field.value;
    });
    return data;
}

/* ── Document ready ─────────────────────────────────────────────────────── */

$(document).ready(function () {

    /* Disable submit for FCC live project type until quote is validated */
    if (IS_FCC_PROJ) {
        $('#add-project-btn').prop('disabled', true);
    }

    /* Quote number: force uppercase Q, then validate */
    $('#quoteno').on('input', function () {
        var v = $(this).val();
        if (v.length > 0 && v[0] !== 'Q') {
            $(this).val('Q' + v.replace(/^Q*/i, ''));
        }
        if (IS_FCC_PROJ) {
            var projId = $(this).data('proj-id') || null;
            validateAndCheckQuote('#quoteno', '#quoteno-feedback', '#add-project-btn', projId);
        }
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

    /* ── Form submit → AJAX JSON POST ─────────────────────────────────── */

    // $('#add-project-form').on('submit', function (e) {
    $('#add-project-btn').on('click', function (e) {
        e.preventDefault();
        var $btn = $('#add-project-btn');
        $btn.prop('disabled', true);
        $.ajax({
            url:         ADD_PROJECT_URL,
            method:      'POST',
            contentType: 'application/json',
            data:        JSON.stringify(collectFormData()),
            success: function (data) {
                if (data.status === 'success') {
                    sessionStorage.setItem('proj_id', data.project_id);
                    sessionStorage.setItem('item_id', data.item_id);
                    allowNavigation = true;
                    window.location.href = '/home';
                } else {
                    showFlash(data.message || 'An unexpected error occurred.', 'error');
                    $btn.prop('disabled', false);
                }
            },
            error: function (xhr) {
                var msg = 'An unexpected error occurred.';
                try {
                    var resp = JSON.parse(xhr.responseText);
                    if (resp.error) { msg = resp.error; }
                } catch (_) {}
                showFlash(msg, 'error');
                $btn.prop('disabled', false);
            },
        });
    });

});
