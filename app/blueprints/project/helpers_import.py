"""
helpers_import.py — Helpers for the import-project flow.

Covers:
  - Data coercion utilities (get_null_or_value, safe_get_id, getCheckedValue,
    getCheckedElement, int_to_float_convertor, clean_item_data)
  - DB lookup shortcuts (get_by_id, get_by_name, float_convert)
  - Foreign-key mapping (map_valve_fk, map_actuator_fk)
  - getpipe_sch_params  — pipe schedule lookup
  - testcase_module     — full testcase-import logic
"""

from __future__ import annotations

import ast
from datetime import datetime

import pandas as pd
from flask import request
from flask_login import current_user
from sqlalchemy import func

from app.extensions import db
from app.models.master import (
    industryMaster,
    regionMaster,
    pipeArea,
    ratingMaster,
    materialMaster,
    designStandard,
    valveStyle,
    fluidState,
    endConnection,
    endFinish,
    bodyFFDimension,
    bonnetType,
    packingType,
    trimType,
    flowCharacter,
    flowDirection,
    plug,
    seatLeakageClass,
    bonnet,
    shaft,
    disc,
    seat,
    seal,
    packing,
    balancing,
    balanceSeal,
    studNut,
    gasket,
    cageClamp,
    packingFriction,
    packingTorque,
    seatLoadForce,
)
from app.models.transactional import (
    projectMaster,
    itemMaster,
    itemRevisionTable,
    valveDetailsMaster,
    caseMaster,
    actuatorMaster,
    actuatorCaseData,
    rotaryCaseData,
    volumeTank,
    accessoriesData,
    itemNotesData,
    caseWarnings,
    valveDataWarnings,
)


# ---------------------------------------------------------------------------
# DB lookup helpers
# ---------------------------------------------------------------------------

def get_by_id(model, id_):
    """Return model instance by PK, or None."""
    if id_:
        return db.session.get(model, int(id_))
    return None


def get_by_name(model, name):
    """Return first model instance matching name, or None."""
    if name:
        return db.session.query(model).filter_by(name=name).first()
    return None


def float_convert(input_):
    try:
        return float(input_)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Data coercion utilities
# ---------------------------------------------------------------------------

_NULL_SENTINEL = [['N/A'], [''], 'N/A']


def get_null_or_value(value):
    if value in _NULL_SENTINEL:
        return (None,)
    return value


def safe_get_id(value):
    if value is None or value in (['N/A'], 'N/A'):
        return None
    return value.id


def getCheckedValue(value):
    """Return None for NaN / 'N/A' / empty string, else value."""
    try:
        if pd.isna(value) or value in ('N/A', ''):
            return None
    except (TypeError, ValueError):
        pass
    return value


def getCheckedElement(model, value):
    """Return model row by name, or None for empty/N/A values."""
    null_vals = [['N/A'], '', 'N/A', None]
    try:
        if pd.isna(value) or value in null_vals:
            return None
    except (TypeError, ValueError):
        pass
    return get_by_name(model, value)


def int_to_float_convertor(value):
    return float(value) if isinstance(value, int) else value


def clean_item_data(item_: dict) -> dict:
    float_fields = [
        'quantity', 'shutOffDelP', 'maxPressure', 'maxTemp', 'minTemp',
        'bonnetExtDimension', 'bonnetExtensionDimen',
    ]
    for key in float_fields:
        item_[key] = get_null_or_value(float_convert(item_[key][0])),

    for key in ('cvType', 'turns'):
        item_[key] = get_null_or_value(item_[key])

    return item_


# ---------------------------------------------------------------------------
# Foreign-key mapping (module-level — not created inside a loop)
# ---------------------------------------------------------------------------

_VALVE_FK_TABLE = {
    'ratingId': ratingMaster,
    'materialId': materialMaster,
    'designStandardId': designStandard,
    'valveStyleId': valveStyle,
    'fluidStateId': fluidState,
    'endConnectionId': endConnection,
    'endFinishId': endFinish,
    'bodyFFDimenId': bodyFFDimension,
    'bonnetTypeId': bonnetType,
    'packingTypeId': packingType,
    'trimTypeId': trimType,
    'flowCharacterId': flowCharacter,
    'flowDirectionId': flowDirection,
    'plugId': plug,
    'seatLeakageClassId': seatLeakageClass,
    'bonnetId': bonnet,
    'shaftId': shaft,
    'discId': disc,
    'seatId': seat,
    'sealId': seal,
    'packingId': packing,
    'balancingId': balancing,
    'balanceSealId': balanceSeal,
    'studNutId': studNut,
    'gasketId': gasket,
    'cageId': cageClamp,
}

_ACTUATOR_FK_TABLE = {
    'trimTypeId': trimType,
    'balancingId': balancing,
    'flowDirectionId': flowDirection,
    'flowCharacterId': flowCharacter,
    'packingFrictionId': packingFriction,
    'packingTorqueId': packingTorque,
    'seatLoadId': seatLoadForce,
}


def map_valve_fk(item_: dict) -> dict:
    for key, model in _VALVE_FK_TABLE.items():
        raw = item_[key][0] if isinstance(item_[key], (list, tuple)) else item_[key]
        item_[key] = (safe_get_id(getCheckedElement(model, str(raw))),)
    return item_


def map_actuator_fk(act_: dict) -> dict:
    for key, model in _ACTUATOR_FK_TABLE.items():
        raw = act_[key][0] if isinstance(act_[key], (list, tuple)) else act_[key]
        act_[key] = (safe_get_id(getCheckedElement(model, raw)),)
    return act_


# ---------------------------------------------------------------------------
# Pipe schedule helper
# ---------------------------------------------------------------------------

def _mm_to_inch(val_mm: float) -> float:
    """Convert mm → inch (1 inch = 25.4 mm)."""
    return val_mm / 25.4


def getpipe_sch_params(pipesize, pipeunit: str, sch: str):
    """Return [wall_thickness_str, inner_dia_inch_str] for given pipe spec."""
    if sch and sch.endswith('S'):
        sch = sch[:-1]

    if pipeunit == 'mm':
        row = (
            db.session.query(pipeArea)
            .filter_by(schedule=sch)
            .order_by(func.abs(pipeArea.nominalDia - pipesize))
            .first()
        )
        thickness = row.thickness
    else:  # inch
        row = (
            db.session.query(pipeArea)
            .filter_by(schedule=sch)
            .order_by(func.abs(pipeArea.nominalPipeSize - pipesize))
            .first()
        )
        thickness = _mm_to_inch(row.thickness)

    inner_dia_inch = _mm_to_inch(row.outerDia - 2 * row.thickness)
    return [str(round(thickness, 3)), str(round(inner_dia_inch, 3))]


# ---------------------------------------------------------------------------
# Testcase import module
# ---------------------------------------------------------------------------

def testcase_module(item_id, proj_id, quote_no: str) -> None:
    """
    Parse a testcase Excel file from the current request and persist it.

    Handles Liquid, Gas, and TwoPhase formats.
    """
    file = request.files.get('file')
    df = pd.read_excel(file, header=None)
    max_rows = df.shape[0]
    user = current_user

    a3_value = str(df.iloc[2, 0]).strip()

    field_map_liq = {
        'valveStyle': 0, 'series': 1, 'trimType': 2, 'characteristic': 3,
        'valveSize': 4, 'inletPipeSize': 5, 'inletSch': 6, 'outletPipeSize': 7,
        'outletSch': 8, 'flowrate': 9, 'inletPressure': 10, 'outletPressure': 11,
        'inletTemp': 12, 'vaporPressure': 13, 'criticalPressure': 14,
        'kinematicViscosity': 15, 'specificGravity': 16, 'solveCase': 4,
    }
    field_map_gas = {
        'valveStyle': 0, 'series': 1, 'trimType': 2, 'characteristic': 3,
        'valveSize': 4, 'inletPipeSize': 5, 'inletSch': 6, 'outletPipeSize': 7,
        'outletSch': 8, 'flowrate': 9, 'inletPressure': 10, 'outletPressure': 11,
        'inletTemp': 12, 'molecularWeight': 13, 'compressibility': 14,
        'specificHeatRatio': 15, 'criticalPressure': 16, 'gasViscosity': 17,
        'solveCase': 4,
    }
    unit_map_liq = {
        'valvesize_unit': 4, 'inpipe_unit': 5, 'outpipe_unit': 7,
        'flowrate_unit': 9, 'inpres_unit': 10, 'outpres_unit': 11,
        'intemp_unit': 12, 'vaporpres_unit': 13, 'criticalpres_unit': 14,
        'viscosity_unit': 15,
    }
    unit_map_gas = {
        'valvesize_unit': 4, 'inpipe_unit': 5, 'outpipe_unit': 7,
        'flowrate_unit': 9, 'inpres_unit': 10, 'outpres_unit': 11,
        'intemp_unit': 12, 'criticalpres_unit': 16, 'viscosity_unit': 17,
    }

    if a3_value.startswith('G'):
        fluid_type = 'Gas'; testcase_type = 'Gas'; item_row_gap = 27
        field_map = field_map_gas; unit_map = unit_map_gas
    elif a3_value.startswith('L'):
        fluid_type = 'Liquid'; testcase_type = 'Liquid'; item_row_gap = 19
        field_map = field_map_liq; unit_map = unit_map_liq
    else:
        fluid_type = 'TwoPhase'; testcase_type = 'TwoPhase'; item_row_gap = 19
        field_map = field_map_liq; unit_map = unit_map_liq

    new_project = projectMaster(
        projectRef='TESTCASES',
        status='Draft',
        user=user,
        revision=0,
        testcase_type=testcase_type,
        cur_revno=0,
        isFccProject=None,
        quoteNo=quote_no,
    )
    db.session.add(new_project)
    db.session.commit()

    mass_units = {'kg/hr', 'kg/s', 'kg/m', 'lb/s', 'lb/m', 'lb/hr',
                  'tonne/hr', 'tonne/m', 'tonne/s'}
    solve_case_map = {'Cv': 1, 'Delp': 2, 'Flowrate': 3}

    for i, item_start in enumerate(range(2, max_rows, item_row_gap)):
        # --- units ---
        units = {}
        for field, offset in unit_map.items():
            try:
                units[field] = df.iloc[item_start + offset, 5]
            except Exception:
                units[field] = None

        flow_type = 'mass' if units.get('flowrate_unit') in mass_units else 'vol'

        # --- item ---
        new_item = itemMaster(
            itemNumber=i + 1,
            project=new_project,
            revision=0,
            draft_status=-1,
            initial_status=1,
            cur_revType='initial',
            cur_status='In progress',
            cur_revno=0,
        )
        db.session.add(new_item)
        db.session.commit()

        db.session.add(itemRevisionTable(
            item=new_item,
            itemRevisionNo=0,
            status='In progress',
            prepared_by=current_user.code,
            time=datetime.today().strftime('%Y-%m-%d %H:%M'),
        ))
        db.session.commit()

        # --- valve-level fields ---
        try:
            valve_style_val = df.iloc[item_start + field_map['valveStyle'], 4]
            series_val      = df.iloc[item_start + field_map['series'], 4]
            trim_val        = df.iloc[item_start + field_map['trimType'], 4]
            char_val        = df.iloc[item_start + field_map['characteristic'], 4]
            solve_for       = df.iloc[item_start + field_map['solveCase'], 2]
        except Exception:
            solve_for = 'Cv'

        new_valve = valveDetailsMaster(
            item=new_item,
            valveSeries=series_val,
            style=getCheckedElement(valveStyle, valve_style_val),
            trimType__=getCheckedElement(trimType, trim_val),
            flowCharacter__=getCheckedElement(flowCharacter, char_val),
            state=getCheckedElement(fluidState, fluid_type),
            solveCase=solve_case_map[solve_for],
            revision=0,
            draft_status=-1,
            flowrate_unit=units.get('flowrate_unit'),
            inpres_unit=units.get('inpres_unit'),
            outpres_unit=units.get('outpres_unit'),
            viscosity_unit=units.get('viscosity_unit'),
            intemp_unit=units.get('intemp_unit'),
            vaporpres_unit=units.get('vaporpres_unit'),
            criticalpres_unit=units.get('criticalpres_unit'),
            inpipe_unit=units.get('inpipe_unit'),
            outpipe_unit=units.get('outpipe_unit'),
            valvesize_unit=units.get('valvesize_unit'),
        )
        db.session.add(new_valve)
        db.session.commit()

        if solve_for == 'Delp':
            new_valve.flowrate_unit = units.get('inpres_unit', '').strip()
            new_valve.inpres_unit = units.get('outpres_unit')
            if new_valve.flowrate_unit in mass_units:
                flow_type = 'mass'

        # --- cases ---
        for col_index in range(6, 11):
            case_offset = col_index - 6
            case_data = {}
            for field, offset in field_map.items():
                row = item_start + offset
                try:
                    val = df.iloc[row, col_index]
                    case_data[field] = float(val) if pd.notna(val) else None
                except Exception:
                    case_data[field] = None

            try:
                if fluid_type == 'Liquid':
                    rated_cv_val = df.iloc[item_start, 13 + case_offset]
                    fl_val       = df.iloc[item_start + 1, 13 + case_offset]
                    fd_val       = df.iloc[item_start + 2, 13 + case_offset]
                    xt_val       = 0.65
                else:  # Gas / TwoPhase
                    rated_cv_val = df.iloc[item_start, 13 + case_offset]
                    fl_val       = df.iloc[item_start + 1, 13 + case_offset]
                    xt_val       = df.iloc[item_start + 2, 13 + case_offset]
                    fd_val       = df.iloc[item_start + 3, 13 + case_offset]
            except Exception:
                rated_cv_val = fl_val = fd_val = xt_val = None

            def _safe_float(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None

            def _clean_str(v):
                if isinstance(v, float) and v.is_integer():
                    return str(int(v))
                return str(v).strip() if v is not None else None

            ipipe_status = getpipe_sch_params(
                case_data['inletPipeSize'], 'inch', _clean_str(case_data['inletSch'])
            )[0]
            opipe_status = getpipe_sch_params(
                case_data['outletPipeSize'], 'inch', _clean_str(case_data['outletSch'])
            )[0]

            if solve_for == 'Cv':
                flowrate_ = getCheckedValue(case_data.get('flowrate'))
                calculated_cv = None
            elif solve_for == 'Flowrate':
                calculated_cv = getCheckedValue(case_data.get('flowrate'))
                flowrate_ = None
            else:  # Delp
                calculated_cv = getCheckedValue(case_data.get('flowrate'))
                flowrate_ = getCheckedValue(case_data.get('inletPressure'))

            is_liquid  = (fluid_type == 'Liquid')
            is_gas     = (fluid_type == 'Gas')

            new_case = caseMaster(
                item=new_item,
                flowrate=flowrate_,
                calculatedCv=calculated_cv,
                inletPressure=getCheckedValue(case_data.get('inletPressure')),
                outletPressure=getCheckedValue(case_data.get('outletPressure')),
                inletTemp=getCheckedValue(case_data.get('inletTemp')),
                vaporPressure=getCheckedValue(case_data.get('vaporPressure')) if is_liquid else None,
                criticalPressure=getCheckedValue(case_data.get('criticalPressure')),
                kinematicViscosity=getCheckedValue(case_data.get('kinematicViscosity')) if is_liquid else None,
                specificGravity=getCheckedValue(case_data.get('specificGravity')) if is_liquid else None,
                molecularWeight=getCheckedValue(case_data.get('molecularWeight')) if is_gas else None,
                compressibility=getCheckedValue(case_data.get('compressibility')) if is_gas else None,
                specificHeatRatio=getCheckedValue(case_data.get('specificHeatRatio')) if is_gas else None,
                gasViscosity=getCheckedValue(case_data.get('gasViscosity')) if is_gas else None,
                inletPipeSize=getCheckedValue(case_data.get('inletPipeSize')),
                outletPipeSize=getCheckedValue(case_data.get('outletPipeSize')),
                valveSize=getCheckedValue(case_data.get('valveSize')),
                iSch=_clean_str(case_data.get('inletSch')),
                oSch=_clean_str(case_data.get('outletSch')),
                ipipeStatus=getCheckedValue(ipipe_status),
                opipeStatus=getCheckedValue(opipe_status),
                ratedCv=_safe_float(rated_cv_val),
                fl=_safe_float(fl_val),
                fd=_safe_float(fd_val),
                xt=_safe_float(xt_val),
                revision=0,
                draft_status=-1,
                flowrateType=flow_type,
            )
            db.session.add(new_case)
            if solve_for == 'Delp':
                new_case.inletPressure = getCheckedValue(case_data.get('outletPressure'))

    db.session.commit()
