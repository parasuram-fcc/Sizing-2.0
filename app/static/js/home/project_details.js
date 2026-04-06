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

/* ── Document ready ─────────────────────────────────────────────────────── */

$(document).ready(function () {

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