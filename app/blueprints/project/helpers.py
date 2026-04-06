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

from sqlalchemy.orm import load_only
from flask_login import current_user

from app.extensions import db
from app.models.master import (
    companyMaster,
    addressMaster,
    industryMaster,
    regionMaster,
    engineerMaster,
)
from app.models.transactional import (
    projectMaster,
    itemMaster,
    userMaster,
    addressProject,
    engineerProject,
)


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
                .filter(addressMaster.createdById.in_(fcc_ids_subq))
                .all()
            )
        else:
            addresses = (
                db.session.query(addressMaster)
                .filter(addressMaster.createdById == user.id)
                .all()
            )

        company_ids = [a.company.id for a in addresses]
        all_companies = (
            db.session.query(companyMaster)
            .filter(companyMaster.id.in_(company_ids))
            .order_by(companyMaster.name.asc())
            .all()
        )
        for company in all_companies:
            active = (
                db.session.query(addressMaster)
                .filter_by(company=company, isActive=True)
                .all()
            )
            notes_dict[company.name] = [a.address for a in active]

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
    company_element   = db.session.query(companyMaster).filter_by(name=cname).first()
    company_element_E = db.session.query(companyMaster).filter_by(name=cnameE).first()
    company_address_element   = db.session.query(addressMaster).filter_by(
        address=address, company=company_element).first()
    company_address_element_E = db.session.query(addressMaster).filter_by(
        address=addressE, company=company_element_E).first()

    aEng_ = db.session.get(engineerMaster, int(aEng))
    cEng_ = db.session.get(engineerMaster, int(cEng))

    if not current_user.fccUser:
        user_name = db.session.get(userMaster, int(cEng))
        cEng_ = db.session.query(engineerMaster).filter_by(name=user_name.name).first()
        company_element   = db.session.query(companyMaster).filter_by(name=cname).all()
        company_element_E = db.session.query(companyMaster).filter_by(name=cnameE).all()
        company_address_element   = None
        company_address_element_E = None
        for i, j in zip(company_element, company_element_E):
            ele   = db.session.query(addressMaster).filter_by(
                address=address, company=i, user=current_user).first()
            ele_E = db.session.query(addressMaster).filter_by(
                address=addressE, company=j, user=current_user).first()
            if ele:
                company_address_element = ele
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
