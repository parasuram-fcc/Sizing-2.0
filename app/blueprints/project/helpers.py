"""
helpers.py — Project blueprint helper functions.

Covers the add-project flow:
  - add_project_metadata()   : lean metadata (replaces full metadata() call)
  - get_item_for_add_project(): targeted load_only item query
  - generate_quote()         : auto-generate quote number
  - add_project_rels()       : create/update addressProject + engineerProject rows
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import load_only, joinedload, selectinload
from flask_login import current_user

from app.extensions import db
from app.models.master import (
    companyMaster,
    addressMaster,
    industryMaster,
    regionMaster,
    engineerMaster,
)
import json

from app.models.master import caseWarningMaster
from app.models.transactional import (
    projectMaster,
    itemMaster,
    userMaster,
    addressProject,
    engineerProject,
    caseMaster,
    caseWarnings,
    valveDetailsMaster,
)


# ---------------------------------------------------------------------------
# Generic DB lookup helpers
# ---------------------------------------------------------------------------

def get_db_element_with_id(table, id_):
    """Return the first row of *table* matching the given id, or None."""
    if id_:
        return db.session.query(table).filter_by(id=id_).first()
    return None


def get_eng_addr_project(project):
    """
    Return (address_c, address_e, eng_a, eng_c) for the given project.
    2 queries instead of 4: fetch all rows per table, split by flag in Python.
    Relationships are eagerly loaded to prevent lazy hits in the template.
    """
    addrs = (
        db.session.query(addressProject)
        .options(
            selectinload(addressProject.address)
            .selectinload(addressMaster.company)
        )
        .filter_by(project=project)
        .all()
    )
    engs = (
        db.session.query(engineerProject)
        .options(selectinload(engineerProject.engineer))
        .filter_by(project=project)
        .all()
    )
    address_c = next((a for a in addrs if a.isCompany),         None)
    address_e = next((a for a in addrs if not a.isCompany),     None)
    eng_a     = next((e for e in engs  if e.isApplication),     None)
    eng_c     = next((e for e in engs  if not e.isApplication), None)
    return address_c, address_e, eng_a, eng_c


# ---------------------------------------------------------------------------
# Static unit lists — only the subsets used by project_details.html
# ---------------------------------------------------------------------------

_PRESSURE_UNITS = [
    {'id': 'bar (a)',    'name': 'bar (a)'},    {'id': 'bar (g)',    'name': 'bar (g)'},
    {'id': 'kPa (a)',    'name': 'kPa (a)'},    {'id': 'kPa (g)',    'name': 'kPa (g)'},
    {'id': 'MPa (a)',    'name': 'MPa (a)'},    {'id': 'MPa (g)',    'name': 'MPa (g)'},
    {'id': 'pa (a)',     'name': 'Pa (a)'},     {'id': 'pa (g)',     'name': 'Pa (g)'},
    {'id': 'kg/cm2 (a)', 'name': 'kg/cm2 (a)'},{'id': 'kg/cm2 (g)', 'name': 'kg/cm2 (g)'},
    {'id': 'mmh20 (a)',  'name': 'mm H2O (a)'}, {'id': 'mmh20 (g)',  'name': 'mm H2O (g)'},
    {'id': 'mbar (a)',   'name': 'mbar (a)'},   {'id': 'mbar (g)',   'name': 'mbar (g)'},
    {'id': 'mmhg (a)',   'name': 'mm Hg (a)'},  {'id': 'mmhg (g)',   'name': 'mm Hg (g)'},
    {'id': 'psi (a)',    'name': 'psi (a)'},    {'id': 'psi (g)',    'name': 'psi (g)'},
    {'id': 'atm (a)',    'name': 'atm (a)'},    {'id': 'atm (g)',    'name': 'atm (g)'},
    {'id': 'torr (a)',   'name': 'torr (a)'},   {'id': 'torr (g)',   'name': 'torr (g)'},
]

_TEMPERATURE_UNITS = [
    {'id': 'C', 'name': '°C'}, {'id': 'F', 'name': '°F'},
    {'id': 'R', 'name': 'R'},  {'id': 'K', 'name': 'K'},
]

_LENGTH_UNITS = [
    {'id': 'inch', 'name': 'inch'}, {'id': 'mm', 'name': 'mm'}, {'id': 'm', 'name': 'm'},
]

_VOL_FLOW_LIQ = [
    {'id': 'm3/hr',    'name': 'm3/hr'},     {'id': 'gpm',      'name': 'gpm(US)'},
    {'id': 'l/hr',     'name': 'l/hr'},      {'id': 'ft3/hr',   'name': 'ft3/hr'},
    {'id': 'barrel/h', 'name': 'barrel/h'},  {'id': 'm3/m',     'name': 'm3/m'},
    {'id': 'l/min',    'name': 'l/min'},     {'id': 'ft3/m',    'name': 'ft3/m'},
    {'id': 'barrel/m', 'name': 'barrel/m'},  {'id': 'barrel/d', 'name': 'barrel/d'},
    {'id': 'in3/m',    'name': 'in3/m'},     {'id': 'mm3/s',    'name': 'mm3/s'},
    {'id': 'cm3/m',    'name': 'cm3/m'},     {'id': 'ml/m',     'name': 'ml/m'},
    {'id': 'gph',      'name': 'gph(US)'},
]

_MASS_FLOWRATE = [
    {'id': 'kg/hr',    'name': 'kg/hr'},    {'id': 'lb/hr',    'name': 'lb/hr'},
    {'id': 'tonne/hr', 'name': 'tonne/hr'}, {'id': 'kg/m',     'name': 'kg/m'},
    {'id': 'lb/m',     'name': 'lb/m'},     {'id': 'tonne/m',  'name': 'tonne/m'},
    {'id': 'kg/s',     'name': 'kg/s'},     {'id': 'lb/s',     'name': 'lb/s'},
    {'id': 'tonne/s',  'name': 'tonne/s'},
]

_VOL_FLOW_GAS = [
    {'id': 'Nm3/hr',  'name': 'Nm3/hr'},  {'id': 'scfh',   'name': 'scfh'},
    {'id': 'MMscfd',  'name': 'MMscfd'},  {'id': 'scfm',   'name': 'scfm'},
    {'id': 'scfd',    'name': 'scfd'},    {'id': 'Nm3/m',  'name': 'Nm3/m'},
    {'id': 'Nm3/d',   'name': 'Nm3/d'},  {'id': 'Sm3/m',  'name': 'Sm3/m'},
    {'id': 'Sm3/h',   'name': 'Sm3/h'},  {'id': 'Sm3/d',  'name': 'Sm3/d'},
]

_DYNAMIC_VISCOSITY   = [{'id': 'cP',   'name': 'cP'},   {'id': 'Pa.s', 'name': 'Pa.s'}]
_KINEMATIC_VISCOSITY = [{'id': 'cSt',  'name': 'cSt'},  {'id': 'm2/s', 'name': 'm2/s'}]

ADD_PROJECT_UNITS = {
    'pressure':           _PRESSURE_UNITS,
    'temperature':        _TEMPERATURE_UNITS,
    'length':             _LENGTH_UNITS,
    'vol_flow_liq':       _VOL_FLOW_LIQ,
    'mass_flowrate':      _MASS_FLOWRATE,
    'vol_flow_gas':       _VOL_FLOW_GAS,
    'dynamic_viscosity':  _DYNAMIC_VISCOSITY,
    'kinematic_viscosity': _KINEMATIC_VISCOSITY,
}

PROJECT_STATUS_LIST = ['Live', 'Dead', 'Lost', 'Regret', 'Won']
PURPOSE_LIST        = ['Firm', 'Bid On', 'Budget', 'Example', 'Technical']


# ---------------------------------------------------------------------------
# Lean metadata — only what project_details.html needs
# ---------------------------------------------------------------------------

def add_project_metadata() -> dict:
    """
    Return the minimal metadata dict for project_details.html.

    Replaces the full metadata() call (~30 DB queries) with 5 targeted queries.
    Static unit lists and config constants come from module-level definitions.
    """
    user = current_user
    notes_dict: dict = {}

    if user.is_authenticated:
        if user.fccUser:
            fcc_ids_subq = (
                db.session.query(userMaster.id)
                .filter_by(fccUser=True)
                .subquery()
            )
            addresses = (
                db.session.query(addressMaster)
                .options(joinedload(addressMaster.company))
                .filter(
                    addressMaster.createdById.in_(fcc_ids_subq),
                    addressMaster.isActive == True,
                )
                .all()
            )
        else:
            addresses = (
                db.session.query(addressMaster)
                .options(joinedload(addressMaster.company))
                .filter(
                    addressMaster.createdById == user.id,
                    addressMaster.isActive == True,
                )
                .all()
            )

        for a in sorted(addresses, key=lambda x: x.company.name):
            notes_dict.setdefault(a.company.name, []).append(a.address)

    industries = (
        db.session.query(industryMaster)
        .options(load_only(industryMaster.id, industryMaster.name))
        .all()
    )
    regions = (
        db.session.query(regionMaster)
        .options(load_only(regionMaster.id, regionMaster.name))
        .all()
    )
    engineers = (
        db.session.query(engineerMaster)
        .options(load_only(engineerMaster.id, engineerMaster.name))
        .all()
    )

    return {
        'notes_dict_': notes_dict,
        'units_dict':  ADD_PROJECT_UNITS,
        'industries':  industries,
        'regions':     regions,
        'engineers':   engineers,
        'status':      PROJECT_STATUS_LIST,
        'purpose':     PURPOSE_LIST,
        'date':        datetime.now().strftime('%Y-%m-%d'),
    }


# ---------------------------------------------------------------------------
# Item loader — load only the columns the template reads
# ---------------------------------------------------------------------------

def get_item_for_add_project(item_id: int) -> itemMaster | None:
    """
    Load the itemMaster row with only the columns used by project_details.html:
    id, flowrate_unit, inpres_unit, inpipe_unit, intemp_unit.

    Avoids triggering any relationship lazy-loads in the template.
    """
    return (
        db.session.query(itemMaster)
        .options(load_only(
            itemMaster.id,
            itemMaster.projectID,
            itemMaster.flowrate_unit,
            itemMaster.inpres_unit,
            itemMaster.inpipe_unit,
            itemMaster.intemp_unit,
        ))
        .filter_by(id=int(item_id))
        .first()
    )


# ---------------------------------------------------------------------------
# Quote number generator — unchanged from app.py
# ---------------------------------------------------------------------------

def generate_quote(prefix: str) -> str:
    """
    Auto-generate a quote number: e.g. Q260xxxx / T260xxxx / C260xxxx.
    Business logic unchanged from generateQuote() in app.py.
    """
    current_year = datetime.now().year % 100
    last = (
        projectMaster.query
        .filter(projectMaster.quoteNo.like(f"{prefix}{current_year:02d}%"))
        .order_by(projectMaster.quoteNo.desc())
        .first()
    )
    new_seq = int(last.quoteNo[-5:]) + 1 if last else 1
    return f"{prefix}{current_year:02d}{new_seq:05d}"


# ---------------------------------------------------------------------------
# Project relationship creator — unchanged from addProjectRels() in app.py
# ---------------------------------------------------------------------------

def add_project_rels(
    cname: str,
    cnameE: str,
    address: str,
    addressE: str,
    aEng: int,
    cEng: int,
    project: projectMaster,
    operation: str,
) -> None:
    """
    Create or update addressProject and engineerProject rows for a project.
    """
    aEng_ = db.session.get(engineerMaster, int(aEng))
    cEng_ = db.session.get(engineerMaster, int(cEng))

    if current_user.fccUser:
        # Batch: 1 query for both companies instead of 2
        companies = (
            db.session.query(companyMaster)
            .filter(companyMaster.name.in_([cname, cnameE]))
            .all()
        )
        company_map          = {c.name: c for c in companies}
        company_element      = company_map.get(cname)
        company_element_E    = company_map.get(cnameE)
        company_address_element   = db.session.query(addressMaster).filter_by(
            address=address,  company=company_element).first()
        company_address_element_E = db.session.query(addressMaster).filter_by(
            address=addressE, company=company_element_E).first()
    else:
        user_name = db.session.get(userMaster, int(cEng))
        cEng_ = db.session.query(engineerMaster).filter_by(name=user_name.name).first()
        company_element   = db.session.query(companyMaster).filter_by(name=cname).all()
        company_element_E = db.session.query(companyMaster).filter_by(name=cnameE).all()
        company_address_element   = None
        company_address_element_E = None
        for i, j in zip(company_element, company_element_E):
            ele   = db.session.query(addressMaster).filter_by(
                address=address,  company=i, user=current_user).first()
            ele_E = db.session.query(addressMaster).filter_by(
                address=addressE, company=j, user=current_user).first()
            if ele:
                company_address_element   = ele
            if ele_E:
                company_address_element_E = ele_E

    if operation == 'create':
        db.session.add_all([
            addressProject(isCompany=True,  address=company_address_element,   project=project),
            addressProject(isCompany=False, address=company_address_element_E, project=project),
            engineerProject(isApplication=True,  engineer=aEng_, project=project),
            engineerProject(isApplication=False, engineer=cEng_, project=project),
        ])
        db.session.commit()

    elif operation == 'update':
        # Batch: 2 queries instead of 4 to fetch relationship rows
        addrs = db.session.query(addressProject).filter_by(project=project).all()
        engs  = db.session.query(engineerProject).filter_by(project=project).all()
        addr_c = next((a for a in addrs if a.isCompany),         None)
        addr_e = next((a for a in addrs if not a.isCompany),     None)
        er_app = next((e for e in engs  if e.isApplication),     None)
        er_con = next((e for e in engs  if not e.isApplication), None)

        if addr_c and addr_e and er_app and er_con:
            addr_c.address  = company_address_element
            addr_e.address  = company_address_element_E
            er_app.engineer = aEng_
            er_con.engineer = cEng_
            db.session.commit()
        else:
            db.session.add_all([
                addressProject(isCompany=True,  address=company_address_element,   project=project),
                addressProject(isCompany=False, address=company_address_element_E, project=project),
                engineerProject(isApplication=True,  engineer=aEng_, project=project),
                engineerProject(isApplication=False, engineer=cEng_, project=project),
            ])
            db.session.commit()

    elif operation == 'update':
        addr_c  = db.session.query(addressProject).filter_by(isCompany=True,  project=project).first()
        addr_e  = db.session.query(addressProject).filter_by(isCompany=False, project=project).first()
        er_app  = db.session.query(engineerProject).filter_by(isApplication=True,  project=project).first()
        er_con  = db.session.query(engineerProject).filter_by(isApplication=False, project=project).first()

        if addr_c and addr_e and er_app and er_con:
            addr_c.address  = company_address_element
            addr_e.address  = company_address_element_E
            er_app.engineer = aEng_
            er_con.engineer = cEng_
            db.session.commit()
        else:
            db.session.add_all([
                addressProject(isCompany=True,  address=company_address_element,   project=project),
                addressProject(isCompany=False, address=company_address_element_E, project=project),
                engineerProject(isApplication=True,  engineer=aEng_, project=project),
                engineerProject(isApplication=False, engineer=cEng_, project=project),
            ])
            db.session.commit()


# ---------------------------------------------------------------------------
# Post-edit warning refreshers — called after edit_project updates noise
# limit / trim exit velocity preferences on the project.
# ---------------------------------------------------------------------------

def _get_warning_actions(warning: str) -> list:
    """Return recommended_solution strings for a caseWarningMaster entry."""
    return [
        row[0]
        for row in db.session.query(caseWarningMaster.recommended_solution)
                             .filter_by(warning=warning)
                             .all()
    ]


def noise_limit_set_(proj_id: int, limit: int) -> None:
    """
    Add or remove the 'High Noise' caseWarnings row on every case of every
    item in the project, based on whether spl > limit.

    Optimized: 3 bulk queries with selectinload instead of N+1 per item/case.
    Single commit at the end instead of one per add/delete.
    """
    warning_dict = {
        'effect':          'Valve generated Noise is too High',
        'action':          json.dumps(_get_warning_actions('Valve generated Noise is too High')),
        'cause':           'Valve generated noise > Allowable Noise Limit',
        'display_warning': 'High Noise',
    }
    CAUSE = 'Valve generated noise > Allowable Noise Limit'

    items = (
        db.session.query(itemMaster)
        .options(
            selectinload(itemMaster.case)
            .selectinload(caseMaster.warning_)
        )
        .filter_by(projectID=proj_id)
        .all()
    )
    for item in items:
        for case in item.case:
            if case.spl is None:
                continue
            existing_causes = {w.cause for w in case.warning_}
            if case.spl > limit:
                if CAUSE not in existing_causes:
                    new_w = caseWarnings(case=case)
                    db.session.add(new_w)
                    db.session.flush()
                    for k, v in warning_dict.items():
                        setattr(new_w, k, v)
            else:
                for w in case.warning_:
                    if w.cause == CAUSE:
                        db.session.delete(w)
    db.session.commit()


def trim_warning_set_(proj_id: int, trim_: str) -> None:
    """
    Add or remove 'High Trim Velocity' caseWarnings rows for every case of
    every item in the project, based on the trim_exit_velocity preference.

    Optimized: 3 bulk queries with selectinload instead of N+1 per item/case.
    Single commit at the end instead of one per add/delete.
    """
    trim_l_dict = {
        'effect':          'Liquid Trim Exit Velocity is too High',
        'action':          json.dumps(_get_warning_actions('Liquid Trim Exit Velocity is too High')),
        'cause':           'Trim Exit Velocity > 30 m/s',
        'display_warning': 'High Trim Velocity',
    }
    trim_g_dict = {
        'effect':          'Gas Trim Exit Velocity is too High',
        'action':          json.dumps(_get_warning_actions('Gas Trim Exit Velocity is too High')),
        'cause':           'Trim Exit Velocity > 70 psi',
        'display_warning': 'High Trim Velocity',
    }
    DISPLAY = 'High Trim Velocity'

    items = (
        db.session.query(itemMaster)
        .options(
            selectinload(itemMaster.valve).selectinload(valveDetailsMaster.state),
            selectinload(itemMaster.case).selectinload(caseMaster.warning_),
        )
        .filter_by(projectID=proj_id)
        .all()
    )
    for item in items:
        fluid_type = item.valve[0].state.name if item.valve else None

        for case in item.case:
            if trim_ == 'yes':
                if fluid_type == 'Liquid' and case.tex and case.tex > 30:
                    warn_dict = trim_l_dict
                elif fluid_type == 'Gas' and case.tex and case.tex > 70:
                    warn_dict = trim_g_dict
                else:
                    continue

                existing_displays = {w.display_warning for w in case.warning_}
                if DISPLAY not in existing_displays:
                    new_w = caseWarnings(case=case)
                    db.session.add(new_w)
                    db.session.flush()
                    for k, v in warn_dict.items():
                        setattr(new_w, k, v)

            elif trim_ == 'no':
                for w in case.warning_:
                    if w.display_warning == DISPLAY:
                        db.session.delete(w)
    db.session.commit()
