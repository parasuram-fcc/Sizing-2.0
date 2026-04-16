/**
 * project_details.js — Add Project and Edit Project page behaviour
 *
 * Depends on utils.js (validateAndCheckQuote, showFlash must be loaded first).
 *
 * Add-project data contract (set by project_details.html via <script> block):
 *   CUSTOMER_NAMES  — { companyName: [address, ...], ... }
 *   UNITS_DICT      — { vol_flow_liq: [...], mass_flowrate: [...],
 *                       dynamic_viscosity: [...], kinematic_viscosity: [...],
 *                       vol_flow_gas: [...] }
 *   IS_FCC_PROJ     — boolean
 *   ADD_PROJECT_URL — string
 *
 * Edit-project data contract (set by edit_project.html via <script> block):
 *   CUSTOMER_NAMES, UNITS_DICT, IS_FCC_PROJ (same as above)
 *   EDIT_PROJECT_URL     — string  (proj/item IDs live in server session, not in URL)
 *   SELECTED_CUSTOMER    — string
 *   SELECTED_ADDRESS     — string
 *   SELECTED_ENDUSER     — string
 *   SELECTED_ENDUSER_ADDR— string
 *   PROJECT_VISCOSITY_TYPE / PROJECT_VISCOSITY_UNIT
 *   PROJECT_GAS_FLOW_TYPE  / PROJECT_GAS_UNIT
 *   PROJECT_LIQ_FLOW_TYPE  / PROJECT_LIQ_UNIT
 */

/* Detect which mode we're in */
const IS_EDIT_MODE = (typeof EDIT_PROJECT_URL !== 'undefined');

/* ── Company → Address cascade ─────────────────────────────────────────── */

function companyAddress(companySelector, addressSelector, companyNames) {
    $(companySelector).on('change', function () {
        var selectedCompany = $(this).val();
        var addressDropdown = $(addressSelector);

        addressDropdown.empty();

        if (selectedCompany && companyNames[selectedCompany]) {
            $.each(companyNames[selectedCompany], function (_index, address) {
                addressDropdown.append(
                    $('<option>', { value: address, text: address })
                );
            });
        }
    });
}

/* ── Company → Address cascade (edit mode: pre-selects saved address) ─────── */

function companyAddressWithSelected(companySelector, addressSelector, companyNames, selectedAddress) {
    $(companySelector).on('change', function () {
        var selectedCompany  = $(this).val();
        var addressDropdown  = $(addressSelector);
        addressDropdown.empty();
        if (selectedCompany && companyNames[selectedCompany]) {
            $.each(companyNames[selectedCompany], function (_index, address) {
                addressDropdown.append(
                    $('<option>', { value: address, text: address, selected: address === selectedAddress })
                );
            });
        }
    });
    $(companySelector).trigger('change');
}

/* ── Unit-list rebuilders ───────────────────────────────────────────────── */

function rebuildUnits(selectId, units) {
    var $sel = $(selectId);
    $sel.empty();
    $.each(units, function (_i, unit) {
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

/* ── Rebuild a <select> with a pre-selected value ───────────────────────── */

function rebuildUnitsWithSelected(selectId, units, selectedId) {
    var $sel = $(selectId);
    $sel.empty();
    $.each(units, function (_i, unit) {
        $sel.append($('<option>', {
            value:    unit.id,
            text:     unit.name,
            selected: unit.id === selectedId,
        }));
    });
}

/* ── Collect form fields for the edit form ──────────────────────────────── */

function collectEditFormData() {
    var data = {};
    $('#edit-project-form').serializeArray().forEach(function (field) {
        data[field.name] = field.value;
    });
    return data;
}

/* ── Document ready ─────────────────────────────────────────────────────── */

$(document).ready(function () {

    if (IS_EDIT_MODE) {
        /* ── EDIT PROJECT MODE ─────────────────────────────────────────── */

        /* Quote validation for FCC live */
        if (IS_FCC_PROJ) {
            $('#quoteno').on('input', function () {
                var v = $(this).val();
                if (v.length > 0 && v[0] !== 'Q') {
                    $(this).val('Q' + v.replace(/^Q*/i, ''));
                }
                var projId = $(this).data('proj-id') || null;
                validateAndCheckQuote('#quoteno', '#quoteno-feedback', '#edit-project-btn', projId);
            });
        }

        /* Company / address cascades with pre-selected values */
        companyAddressWithSelected('#company',  '#address',  CUSTOMER_NAMES, SELECTED_ADDRESS);
        companyAddressWithSelected('#companyE', '#addressE', CUSTOMER_NAMES, SELECTED_ENDUSER_ADDR);

        /* Unit rebuilders: initial load with project defaults */
        var viscosUnits = (PROJECT_VISCOSITY_TYPE === 'dynamic')
            ? UNITS_DICT['dynamic_viscosity']
            : UNITS_DICT['kinematic_viscosity'];
        rebuildUnitsWithSelected('#v_units', viscosUnits, PROJECT_VISCOSITY_UNIT);

        var liqUnits = (PROJECT_LIQ_FLOW_TYPE === 'vol')
            ? UNITS_DICT['vol_flow_liq']
            : UNITS_DICT['mass_flowrate'];
        rebuildUnitsWithSelected('#liq_unit', liqUnits, PROJECT_LIQ_UNIT);

        var gasUnits = (PROJECT_GAS_FLOW_TYPE === 'vol')
            ? UNITS_DICT['vol_flow_gas']
            : UNITS_DICT['mass_flowrate'];
        rebuildUnitsWithSelected('#gas_unit', gasUnits, PROJECT_GAS_UNIT);

        /* Unit type change handlers */
        $('#viscos').on('change', function () {
            var type  = $(this).val();
            var units = (type === 'dynamic') ? UNITS_DICT['dynamic_viscosity'] : UNITS_DICT['kinematic_viscosity'];
            rebuildUnits('#v_units', units);
        });
        $('#liq_flow').on('change', function () {
            var type  = $(this).val();
            var units = (type === 'vol') ? UNITS_DICT['vol_flow_liq'] : UNITS_DICT['mass_flowrate'];
            rebuildUnits('#liq_unit', units);
        });
        $('#gas_flow').on('change', function () {
            var type  = $(this).val();
            var units = (type === 'vol') ? UNITS_DICT['vol_flow_gas'] : UNITS_DICT['mass_flowrate'];
            rebuildUnits('#gas_unit', units);
        });

        /* Submit — AJAX JSON POST to edit-project endpoint */
        $('#edit-project-btn').on('click', function (e) {
            e.preventDefault();
            var $btn = $('#edit-project-btn');
            $btn.prop('disabled', true);
            $.ajax({
                url:         EDIT_PROJECT_URL,
                method:      'POST',
                contentType: 'application/json',
                data:        JSON.stringify(collectEditFormData()),
                success: function (data) {
                    if (data.status === 'success') {
                        showFlash('Project updated successfully', 'success');
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
                        if (resp.message) { msg = resp.message; }
                    } catch (_) {}
                    showFlash(msg, 'error');
                    $btn.prop('disabled', false);
                },
            });
        });

    } else {
        /* ── ADD PROJECT MODE ──────────────────────────────────────────── */

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

        /* Submit — AJAX JSON POST to add-project endpoint */
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
                        if (resp.error) { msg = resp.message; }
                    } catch (_) {}
                    showFlash(msg, 'error');
                    $btn.prop('disabled', false);
                },
            });
        });
    }

});
