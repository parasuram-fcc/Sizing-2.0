"""
routes.py — Project blueprint routes.

Routes:
  GET  /project/export-project/proj-<proj_id>/item-<item_id>
  POST /project/import-project/proj-<proj_id>/item-<item_id>
  GET  /project/add-project/
  POST /project/add-project/
  GET  /project/check_quote
  GET  /project/submit-project-type
  POST /project/project-delete
  POST /project/project-submit
  POST /project/check-project-draftst
  POST /project/item-delete
  GET  /project/get_items_only/proj-<proj_id>
  GET  /project/get_project_revisions/<proj_id>
  GET  /project/get_item_revisions/item-<item_id>
  POST /project/get-item-revision
  POST /project/change-revision-status
  POST /project/delete-draft
"""

import ast
import json
import re
from collections import defaultdict
from datetime import datetime
from io import BytesIO
import traceback

import pandas as pd
from flask import flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import distinct
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, selectinload

from app.blueprints.project import bp
from app.extensions import db
from openpyxl import Workbook

from app.models.master import (
    addressMaster,
    balancing,
    balanceSeal,
    bodyFFDimension,
    bonnet,
    bonnetType,
    cageClamp,
    companyMaster,
    designStandard,
    disc,
    endConnection,
    endFinish,
    engineerMaster,
    fluidProperties,
    fluidState,
    flowCharacter,
    flowDirection,
    gasket,
    industryMaster,
    materialMaster,
    nde1,
    nde2,
    packing,
    packingFriction,
    packingTorque,
    packingType,
    plug,
    ratingMaster,
    regionMaster,
    seat,
    seatLeakageClass,
    seatLoadForce,
    seal,
    shaft,
    studNut,
    trimType,
    valveStyle,
)
from app.models.transactional import (
    accessoriesData,
    actuatorCaseData,
    actuatorMaster,
    caseMaster,
    caseWarnings,
    engineerProject,
    addressProject,
    itemMaster,
    itemNotesData,
    itemRevisionTable,
    projectMaster,
    projectRevisionTable,
    rotaryCaseData,
    strokeCase,
    userMaster,
    valveDataWarnings,
    valveDetailsMaster,
    volumeTank,
)
from app.blueprints.project.helpers_import import (
    get_by_id,
    get_by_name,
    get_null_or_value,
    safe_get_id,
    getCheckedValue,
    getCheckedElement,
    int_to_float_convertor,
    clean_item_data,
    map_valve_fk,
    map_actuator_fk,
    testcase_module,
)
from app.blueprints.project.helpers import (
    add_project_metadata,
    add_project_rels,
    generate_quote,
    get_db_element_with_id,
    get_eng_addr_project,
    get_item_for_add_project,
)
from app.blueprints.home.helpers import (
    get_items_for_project,
    getLatestFccLiveProject,
    serialize_item,
)
from app.utils.helpers import error_handler


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_new_item(project, item_number, alternate):
    """Create a blank item with all related records for a project."""
    fluid_state = db.session.query(fluidState).first()
    new_item = itemMaster(
        project=project,
        itemNumber=item_number,
        alternate=alternate,
        revision=0,
        cur_revType='initial',
        cur_status='In progress',
        cur_revno=0,
        draft_status=-1,
        initial_status=1,
    )
    db.session.add(new_item)
    db.session.flush()

    new_valve = valveDetailsMaster(
        item=new_item, state=fluid_state, revision=0, draft_status=-1,
        tagNumber='TBA', serialNumber='TBA', application='TBA',
        isActive=0, cases_length=5, solveCase=1,
        inpres_unit=project.pressure_unit, outpres_unit=project.pressure_unit,
        vaporpres_unit=project.pressure_unit, criticalpres_unit=project.pressure_unit,
        inpipe_unit=project.length_unit, outpipe_unit=project.length_unit,
        valvesize_unit=project.length_unit, intemp_unit=project.temperature_unit,
        viscosity_unit=project.viscosity_unit,
    )
    db.session.add(new_valve)

    new_act = actuatorMaster(item=new_item, revision=0, draft_status=-1)
    db.session.add(new_act)
    db.session.flush()

    new_act_case = actuatorCaseData(actuator_=new_act, revision=0, draft_status=-1)
    db.session.add(new_act_case)
    db.session.flush()

    db.session.add(rotaryCaseData(actuator_=new_act, revision=0, draft_status=-1))
    db.session.add(strokeCase(actuatorCase_=new_act_case, status=1, revision=0, draft_status=-1))
    db.session.add(accessoriesData(item=new_item, revision=0, draft_status=-1))

    item_rev = itemRevisionTable(
        item=new_item, itemRevisionNo=0, status="In progress",
        prepared_by=current_user.code,
        time=datetime.today().strftime("%Y-%m-%d %H:%M"),
    )
    db.session.add(item_rev)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return new_item


def _new_user_project_item(user):
    """Create a bare project + item when a user deletes their last project."""
    fluid_state = db.session.query(fluidState).first()
    new_project = projectMaster(
        user=user, quoteNo=None, projectRef='TBA', enquiryRef='TBA',
        noise_limit=85, trim_exit_velocity='no',
        enquiryReceivedDate=datetime.today(),
        receiptDate=datetime.today(),
        bidDueDate=datetime.today(),
        revision=0, cur_revno=0,
    )
    new_item = itemMaster(project=new_project, itemNumber=1, alternate='A',
                          revision=0, cur_revno=0)
    new_valve = valveDetailsMaster(
        item=new_item, state=fluid_state, tagNumber='TBA', serialNumber='TBA',
        application='TBA', revision=0, isActive=0, cases_length=5,
        inpres_unit=new_project.pressure_unit, outpres_unit=new_project.pressure_unit,
        vaporpres_unit=new_project.pressure_unit, criticalpres_unit=new_project.pressure_unit,
        inpipe_unit=new_project.length_unit, outpipe_unit=new_project.length_unit,
        valvesize_unit=new_project.length_unit, intemp_unit=new_project.temperature_unit,
        viscosity_unit=new_project.viscosity_unit,
    )
    new_act = actuatorMaster(item=new_item, revision=0)
    new_acc = accessoriesData(item=new_item, revision=0)
    new_company = companyMaster(name='FCC', description='Oil and Gas')
    new_address = addressMaster(
        address='Chennai', isActive=1, user=user,
        company=new_company, customerCode='A001',
    )
    new_addr_proj = addressProject(address=new_address, isCompany=True, project=new_project)
    db.session.add_all([
        new_project, new_item, new_valve, new_act, new_acc,
        new_company, new_address, new_addr_proj,
    ])
    db.session.commit()
    return new_project, new_item


# ---------------------------------------------------------------------------
# /project/check_quote
# ---------------------------------------------------------------------------

@bp.route('/check_quote', methods=['GET'])
@login_required
def check_quote():
    """
    Check whether a quote number is already taken.

    Params:
        quote   — the quote string to test
        proj_id — (optional) project id to exclude (edit-project case)

    Returns:
        JSON { is_exists: true/false }
        403  if caller is not an FCC user
    """
    if not current_user.fccUser:
        return jsonify({'error': 'Forbidden'}), 403

    quote   = request.args.get('quote', '').strip()
    proj_id = request.args.get('proj_id', None)

    q = db.session.query(projectMaster).filter(projectMaster.quoteNo == quote)
    if proj_id:
        q = q.filter(projectMaster.id != int(proj_id))

    exists = q.first() is not None
    return jsonify({'is_exists': exists})


# ---------------------------------------------------------------------------
# /project/add-project — Create a new project
# ---------------------------------------------------------------------------

@bp.route('/add-project/', methods=['GET', 'POST'])
@login_required
@error_handler
def add_project():
    """
    GET  — Render the add-project form.
    POST — JSON body. Validate, create projectMaster + first item.
           Returns JSON {status, project_id, item_id} on success
           or {status, error} on failure.
    """

    if request.method == 'POST':
        user = current_user
        a    = request.get_json()

        # ── 1. Determine quote number and project type ────────────────────
        if user.fccUser and user.projType == 1:
            fccproject = True
            quote_no   = a['quoteNo'].strip()
            if not re.fullmatch(r"Q\d{7}", quote_no):
                return jsonify({
                    'status': 'error',
                    'error': "Quote format should be 'Q' followed by 7 digit Number",
                }), 400

        elif user.fccUser and user.projType == 2:
            fccproject = None
            quote_no   = generate_quote("T")

        else:
            fccproject = False
            quote_no   = generate_quote("C")

        proj_id = str(quote_no)
        # ── 2. Create projectMaster ───────────────────────────────────────
        try:
            new_project = projectMaster(
                quoteNo              = proj_id,
                isFccProject         = fccproject,
                isObsolete           = False,
                projectRef           = a['projectRef'],
                enquiryRef           = a['enquiryRef'],
                enquiryReceivedDate  = datetime.strptime(a['enquiryReceivedDate'], '%Y-%m-%d'),
                receiptDate          = datetime.strptime(a['receiptDate'], '%Y-%m-%d'),
                bidDueDate           = datetime.strptime(a['bidDueDate'], '%Y-%m-%d'),
                purpose              = a['purpose'],
                custPoNo             = a['custPoNo'],
                workOderNo           = a['workOderNo'],
                status               = a['status'],
                user                 = current_user,
                industry             = db.session.get(industryMaster, int(a['industry']))
                                        if a['industry'] != 'OEM'
                                        else None,
                region               = db.session.get(regionMaster, int(a['region'])),
                revision             = 0,
                cur_revno            = 0,
                # Preferences
                pressure_unit        = a['pressureUnit'],
                l_flowrate_type      = a['LiquidflowrateType'],
                l_flowrate_unit      = a['LiquidflowrateUnit'],
                g_flowrate_type      = a['GasflowrateType'],
                g_flowrate_unit      = a['GasflowrateUnit'],
                viscosity_type       = a['viscosity_'],
                viscosity_unit       = a['vis_units'],
                length_unit          = a['lengthUnit'],
                temperature_unit     = a['temperatureUnit'],
                trim_exit_velocity   = a['tev'],
                noise_limit          = a['noise_limit'],
            )
            db.session.add(new_project)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if 'unique' in str(e.orig).lower() or 'duplicate' in str(e.orig).lower():
                return jsonify({'status': 'error', 'message': 'Quote Number already exists!', 'error':str(e)}), 400
            return jsonify({'status': 'error', 'message': 'Database error occurred. Please try again.', 'error':str(e)}), 400
        except Exception as e:
            # traceback.print_exc()
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Something went wrong. Please try again.', 'error':str(e)}), 400
        # ── 3. Create first item ──────────────────────────────────────────
        try:
            add_item = _add_new_item(new_project, 1, 'A')
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Failed to create item. Please try again.', 'error':str(e)}), 400
        # ── 4. Link company / engineer relationships ──────────────────────
        try:
            project_element = db.session.query(projectMaster).filter_by(quoteNo=proj_id).first()
            eng_element     = db.session.query(engineerMaster).filter_by(name=a['aEng']).first()
            add_project_rels(
                cname     = a['cname'],
                cnameE    = a['cnameE'],
                address   = a['address'],
                addressE  = a['addressE'],
                aEng      = eng_element.id,
                cEng      = a['cEng'],
                project   = project_element,
                operation = 'create',
            )
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Failed to save project relationships. Please try again.', 'error':str(e)}), 400

        # ── 5. Update session bucket to new project's range ──────────────
        last_project = new_project.quoteNo
        if last_project:
            prefix       = last_project[:3]
            last_num     = int(last_project[3:])
            bucket_start = (last_num // 100) * 100
            bucket_end   = bucket_start + 99
            session['selected_bucket'] = (
                f"{prefix}{str(bucket_start).zfill(5)} - {prefix}{str(bucket_end).zfill(5)}"
            )
        return jsonify({
            'status': 'success',
            'project_id': add_item.projectID,
            'item_id': add_item.id,
        })

    # ── GET ───────────────────────────────────────────────────────────────
    metadata_ = add_project_metadata()

    return render_template(
        'project/project_details.html',
        metadata=metadata_, user=current_user,
    )


# ---------------------------------------------------------------------------
# /project/submit-project-type
# ---------------------------------------------------------------------------

@bp.route('/submit-project-type', methods=['GET'])
def submitProjectType():
    proj_type = request.args.get('proj_type')
    user = current_user
    if user.fccUser:
        user.projType = int(proj_type)
        db.session.commit()
    return jsonify({"status": "success"})


# ---------------------------------------------------------------------------
# /project/get_items_only
# ---------------------------------------------------------------------------

@bp.route('/get_items_only/proj-<int:proj_id>', methods=['GET'])
@login_required
def get_items_only(proj_id):
    """Return a JSON list of items for a project."""
    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')

    items = get_items_for_project(proj_id, search_type, search_value)
    return jsonify({"items": [serialize_item(i) for i in items]})


# ---------------------------------------------------------------------------
# /project/get_project_revisions
# ---------------------------------------------------------------------------

@bp.route('/get_project_revisions/<int:proj_id>')
@login_required
def get_project_revisions(proj_id):
    if not current_user.fccUser:
        return jsonify([])

    rows = (
        db.session.query(
            distinct(projectRevisionTable.projectRevision),
            projectRevisionTable.projectRevision,
            projectRevisionTable.prepared_by,
        )
        .filter_by(projectId=proj_id)
        .all()
    )
    return jsonify([{"projectRevision": r.projectRevision} for r in rows])


# ---------------------------------------------------------------------------
# /project/get_item_revisions
# ---------------------------------------------------------------------------

@bp.route('/get_item_revisions/item-<int:item_id>')
@login_required
def get_item_revisions(item_id):
    if not current_user.fccUser:
        return jsonify([])

    rows = (
        db.session.query(
            distinct(itemRevisionTable.itemRevisionNo),
            itemRevisionTable.itemRevisionNo,
            itemRevisionTable.status,
            itemRevisionTable.prepared_by,
        )
        .filter_by(itemId=item_id)
        .all()
    )
    return jsonify([
        {
            "revision":       r.itemRevisionNo,
            "status":         r.status,
            "prepared_by":    r.prepared_by,
            "itemRevisionNo": r.itemRevisionNo,
        }
        for r in rows
    ])


# ---------------------------------------------------------------------------
# /project/get-item-revision
# ---------------------------------------------------------------------------

@bp.route('/get-item-revision', methods=['POST'])
@login_required
def get_item_revision():
    item_id      = request.form['itemNumber']
    item_element = db.session.get(itemMaster, int(item_id))
    rows = (
        db.session.query(itemRevisionTable)
        .filter_by(item=item_element)
        .order_by(itemRevisionTable.itemRevisionNo.asc())
        .all()
    )
    revisions = [
        {
            'itemRevisionNo': r.itemRevisionNo,
            'status':         r.status,
            'prepared_by':    r.prepared_by,
            'time':           r.time,
            'remarks':        r.remarks,
        }
        for r in rows
    ]
    return jsonify(revisions), 200


# ---------------------------------------------------------------------------
# /project/change-revision-status
# ---------------------------------------------------------------------------

@bp.route('/change-revision-status', methods=['POST'])
@login_required
def change_revision_status():
    revision_type          = request.form['revisionType']
    item_no                = request.form['itemNumber']
    revision_no            = int(request.form['revisionNumber'])
    selected_revision_type = request.form['selectedRevisionType']
    item_element           = db.session.get(itemMaster, int(item_no))

    # ── Reopen a Draft Completed revision ──
    if revision_type == 'existingdraft' and selected_revision_type == 'Draft Completed':
        cur_rev = item_element.cur_revno

        def _set_draft(obj):
            if obj:
                obj.draft_status = -1
                db.session.commit()

        _set_draft(valveDetailsMaster.getValveElement(item_element, cur_rev))

        for case in db.session.query(caseMaster).filter_by(item=item_element, revision=cur_rev).all():
            _set_draft(case)

        act = db.session.query(actuatorMaster).filter_by(item=item_element, revision=cur_rev).first()
        if act:
            _set_draft(act)
            if act.actSelectionType == 'sliding':
                act_case = db.session.query(actuatorCaseData).filter_by(actuator_=act, revision=cur_rev).first()
                _set_draft(act_case)
                _set_draft(db.session.query(strokeCase).filter_by(actuatorCase_=act_case, revision=cur_rev).first())
            elif act.actSelectionType == 'rotary':
                _set_draft(db.session.query(rotaryCaseData).filter_by(actuator_=act, revision=cur_rev).first())
            _set_draft(db.session.query(volumeTank).filter_by(actuator_=act, revision=cur_rev).first())

        _set_draft(db.session.query(accessoriesData).filter_by(item=item_element, revision=cur_rev).first())

        for note in db.session.query(itemNotesData).filter_by(item=item_element, revision=cur_rev).all():
            _set_draft(note)

        item_rev = db.session.query(itemRevisionTable).filter(
            itemRevisionTable.item == item_element,
            itemRevisionTable.status.in_(["Draft Completed", "In progress"]),
        ).first()
        item_rev.status      = 'In progress'
        item_rev.prepared_by = current_user.code
        item_element.draft_status   = -1
        item_element.cur_revType    = 'draft'
        item_element.initial_status = 1
        item_element.cur_status     = 'In progress'
        db.session.commit()
        return jsonify([{'itemId': item_no}, {'projId': item_element.project.id}]), 200

    # ── Switch to an existing revision (view/existingdraft) ──
    if revision_type not in ('draft',):
        item_element.cur_revno   = revision_no
        item_element.cur_revType = revision_type
        db.session.commit()
        return jsonify([{'itemId': item_no}, {'projId': item_element.project.id}]), 200

    # ── Create a new draft revision (copy) ──
    updated_revision = item_element.revision + 1
    item_element.cur_revno    = updated_revision
    item_element.cur_revType  = 'initial'
    item_element.draft_status = -1
    item_element.cur_status   = 'In progress'
    item_element.revision     = updated_revision
    db.session.commit()

    item_rev = itemRevisionTable(
        item=item_element, itemRevisionNo=updated_revision,
        status="In progress", prepared_by=current_user.code,
        time=datetime.today().strftime("%Y-%m-%d %H:%M"),
    )
    db.session.add(item_rev)
    db.session.commit()

    def _copy_attrs(src, dst, skip):
        for attr in sa_inspect(type(src)).attrs:
            if attr.key not in skip:
                setattr(dst, attr.key, getattr(src, attr.key))

    # valve
    old_valve = valveDetailsMaster.getValveElement(item_element, revision_no)
    new_valve = valveDetailsMaster(item=item_element)
    db.session.add(new_valve)
    _copy_attrs(old_valve, new_valve, {'id', 'revision'})
    new_valve.draft_status = -1
    new_valve.revision     = updated_revision
    db.session.commit()

    # cases
    for case in db.session.query(caseMaster).filter_by(item=item_element, revision=revision_no).order_by(caseMaster.id).all():
        new_case = caseMaster(item=item_element)
        db.session.add(new_case)
        _copy_attrs(case, new_case, {'id', 'revision'})
        new_case.revision     = updated_revision
        new_case.draft_status = -1
        db.session.commit()

    # actuator
    old_act = db.session.query(actuatorMaster).filter_by(item=item_element, revision=revision_no).first()
    if old_act:
        new_act = actuatorMaster(item=item_element)
        db.session.add(new_act)
        _copy_attrs(old_act, new_act, {'id', 'revision', 'rotCase', 'actCase', 'volume_tank'})
        new_act.revision     = updated_revision
        new_act.draft_status = -1
        db.session.commit()

        if old_act.actSelectionType == 'sliding':
            old_ac  = db.session.query(actuatorCaseData).filter_by(actuator_=old_act, revision=revision_no).first()
            new_ac  = actuatorCaseData(actuator_=new_act)
            db.session.add(new_ac)
            if old_ac:
                _copy_attrs(old_ac, new_ac, {'id', 'actuatorMasterId', 'actuator_', 'slidingActuatorId', 'slidingActuator', 'rotaryActuatorId', 'rotaryActuator', 'strokeCase_', 'revision'})
            new_ac.revision     = updated_revision
            new_ac.draft_status = -1
            new_ac.actuator_    = new_act
            db.session.commit()

            old_sc = db.session.query(strokeCase).filter_by(actuatorCase_=old_ac, revision=revision_no).first()
            if old_sc:
                new_sc = strokeCase(actuatorCase_=new_ac)
                db.session.add(new_sc)
                _copy_attrs(old_sc, new_sc, {'id', 'revision', 'actuatorCase_', 'actuatorCaseId'})
                new_sc.revision     = updated_revision
                new_sc.draft_status = -1
                new_sc.status       = 1
                new_sc.actuatorCase_ = new_ac
                db.session.commit()

        elif old_act.actSelectionType == 'rotary':
            old_rc = db.session.query(rotaryCaseData).filter_by(actuator_=old_act, revision=revision_no).first()
            new_rc = rotaryCaseData(actuator_=new_act)
            db.session.add(new_rc)
            _copy_attrs(old_rc, new_rc, {'id', 'actuatorMasterId', 'actuator_', 'revision'})
            new_rc.revision     = updated_revision
            new_rc.draft_status = -1
            new_rc.actuator_    = new_act
            db.session.commit()

        old_vt = db.session.query(volumeTank).filter_by(actuator_=old_act, revision=revision_no).first()
        if old_vt:
            new_vt = volumeTank(actuator_=new_act)
            db.session.add(new_vt)
            _copy_attrs(old_vt, new_vt, {'id', 'revision', 'actuatorMasterId', 'actuator_'})
            new_vt.revision     = updated_revision
            new_vt.draft_status = -1
            db.session.commit()

    # order notes
    for note in db.session.query(itemNotesData).filter_by(item=item_element, revision=revision_no).all():
        new_note = itemNotesData(item=item_element)
        db.session.add(new_note)
        _copy_attrs(note, new_note, {'id', 'itemId', 'revision'})
        new_note.revision     = updated_revision
        new_note.draft_status = -1
        db.session.commit()

    # accessories
    old_acc = db.session.query(accessoriesData).filter_by(item=item_element, revision=revision_no).first()
    if old_acc:
        new_acc = accessoriesData(item=item_element)
        db.session.add(new_acc)
        _copy_attrs(old_acc, new_acc, {'id', 'revision'})
        new_acc.revision     = updated_revision
        new_acc.draft_status = -1
        db.session.commit()

    return jsonify([{'itemId': item_no}, {'projId': item_element.project.id}]), 200


# ---------------------------------------------------------------------------
# /project/check-project-draftst
# ---------------------------------------------------------------------------

@bp.route('/check-project-draftst', methods=['POST'])
@login_required
@error_handler
def check_project_draftst():
    proj_id = request.form['projectId']
    project = db.session.get(projectMaster, int(proj_id))
    items = (
        db.session.query(itemMaster)
        .filter_by(project=project)
        .order_by(itemMaster.itemNumber.asc())
        .all()
    )

    # All items already completed — nothing to submit
    if not any(i.draft_status in (0, -1) for i in items):
        return jsonify({'has_submitable': False, 'reason': 'all_completed'})

    # Active items exist but none are proper drafts (all unsaved)
    has_submitable = any(i.draft_status == 0 for i in items)
    if not has_submitable:
        return jsonify({'has_submitable': False, 'reason': 'no_drafts'})

    # Has submittable drafts — flag any unsaved items
    unsaved_ids = [i.id for i in items if i.draft_status == -1]
    if unsaved_ids:
        return jsonify({'item_ids': unsaved_ids, 'has_submitable': True})


# ---------------------------------------------------------------------------
# /project/project-submit
# ---------------------------------------------------------------------------

@bp.route('/project-submit', methods=['POST'])
@login_required
@error_handler
def project_submit():
    proj_id  = request.form['projectId']
    project  = db.session.get(projectMaster, int(proj_id))
    last_rev = project.revision

    items = (
        db.session.query(itemMaster)
        .filter_by(project=project, draft_status=0)
        .order_by(itemMaster.itemNumber.asc())
        .all()
    )

    now = datetime.today().strftime("%Y-%m-%d %H:%M")

    for item_ in items:
        cur_rev = item_.revision

        proj_rev_row = projectRevisionTable(
            project=project, projectRevision=last_rev,
            item=item_, itemRevision=cur_rev,
            prepared_by=current_user.code,
            time=now,
        )
        db.session.add(proj_rev_row)

        item_rev = db.session.query(itemRevisionTable).filter_by(item=item_, itemRevisionNo=cur_rev).first()
        if item_rev:
            item_rev.status = "Completed"
            item_rev.time   = now

        valve = valveDetailsMaster.getValveElement(item_, cur_rev)
        if valve:
            valve.draft_status = 1

        for case in db.session.query(caseMaster).filter_by(item=item_, revision=cur_rev).all():
            case.draft_status = 1

        act = db.session.query(actuatorMaster).filter_by(item=item_, revision=cur_rev).first()
        if act:
            act.draft_status = 1
            if act.actSelectionType == 'sliding':
                ac = db.session.query(actuatorCaseData).filter_by(actuator_=act, revision=cur_rev).first()
                if ac:
                    ac.draft_status = 1
                sc = db.session.query(strokeCase).filter_by(actuatorCase_=ac, revision=cur_rev).first() if ac else None
                if sc:
                    sc.draft_status = 1
            elif act.actSelectionType == 'rotary':
                rc = db.session.query(rotaryCaseData).filter_by(actuator_=act, revision=cur_rev).first()
                if rc:
                    rc.draft_status = 1

        vt = db.session.query(volumeTank).filter_by(actuator_=act, revision=cur_rev).first() if act else None
        if vt:
            vt.draft_status = 1

        acc = db.session.query(accessoriesData).filter_by(item=item_, revision=cur_rev).first()
        if acc:
            acc.draft_status = 1

        for note in db.session.query(itemNotesData).filter_by(item=item_, revision=cur_rev).all():
            note.draft_status = 1

        item_.cur_revType  = 'view'
        item_.draft_status = 1
        item_.cur_status   = 'Completed'

    project.revision = last_rev + 1
    db.session.commit()
    return jsonify({'status':'success', 'message':'Project Submitted succesfully'})


# ---------------------------------------------------------------------------
# /project/delete-draft
# ---------------------------------------------------------------------------

@bp.route('/delete-draft', methods=['POST'])
@login_required
def delete_draft():
    item_id      = request.form['itemId']
    item_rev_no  = request.form['itemRevNo']
    item_element = db.session.get(itemMaster, int(item_id))

    item_rev = db.session.query(itemRevisionTable).filter_by(
        item=item_element, itemRevisionNo=item_rev_no
    ).first()
    db.session.delete(item_rev)
    db.session.commit()

    valve = valveDetailsMaster.getValveElement(item_element, item_rev_no)
    if valve:
        db.session.delete(valve)
        db.session.commit()

    for case in db.session.query(caseMaster).filter_by(item=item_element, revision=item_rev_no).all():
        db.session.delete(case)
    db.session.commit()

    act = db.session.query(actuatorMaster).filter_by(item=item_element, revision=item_rev_no).first()
    if act:
        if act.actSelectionType == 'sliding':
            ac = db.session.query(actuatorCaseData).filter_by(actuator_=act, revision=item_rev_no).first()
            if ac:
                db.session.delete(ac)
                db.session.commit()
        elif act.actSelectionType == 'rotary':
            rc = db.session.query(rotaryCaseData).filter_by(actuator_=act, revision=item_rev_no).first()
            if rc:
                db.session.delete(rc)
                db.session.commit()
        db.session.delete(act)
        db.session.commit()

    acc = db.session.query(accessoriesData).filter_by(item=item_element, revision=item_rev_no).first()
    if acc:
        db.session.delete(acc)
        db.session.commit()

    for note in db.session.query(itemNotesData).filter_by(item=item_element, revision=item_rev_no).all():
        db.session.delete(note)
    db.session.commit()

    last_rev = (
        db.session.query(itemRevisionTable)
        .filter(itemRevisionTable.itemId == item_element.id)
        .order_by(itemRevisionTable.id.desc())
        .first()
    )
    item_element.cur_status   = last_rev.status
    item_element.revision     = last_rev.itemRevisionNo
    item_element.draft_status = 0
    db.session.commit()
    return "success"


# ---------------------------------------------------------------------------
# /project/item-delete
# ---------------------------------------------------------------------------

@bp.route('/item-delete', methods=['POST'])
@login_required
def item_delete():
    item_id    = request.form['item_id']
    reason     = request.form['reasonfordelete']
    item_      = db.session.get(itemMaster, int(item_id))
    project_id = item_.project.id

    all_items = db.session.query(itemMaster).filter_by(project=item_.project).all()

    if len(all_items) == 1:
        new_item = _add_new_item(item_.project, 1, "A")
        flash("Blank Item Added, and item deleted successfully", "success")
        db.session.delete(item_)
        db.session.commit()
        return_item_id = new_item.id
    else:
        for rev in db.session.query(projectRevisionTable).filter_by(item=item_).all():
            rev.message = reason
            valve_data  = db.session.query(valveDetailsMaster).filter_by(item=item_).first()
            rev.tagno   = valve_data.tagNumber if valve_data else None
        db.session.commit()
        db.session.delete(item_)
        db.session.commit()
        flash("Item deleted successfully", "success")
        remaining      = db.session.query(itemMaster).filter_by(
            project=db.session.get(projectMaster, project_id)
        ).all()
        return_item_id = remaining[0].id if remaining else None

    proj           = db.session.get(projectMaster, project_id)
    items_after    = db.session.query(itemMaster).filter_by(project=proj).all()
    valve_data_list = (
        db.session.query(valveDetailsMaster)
        .filter(valveDetailsMaster.itemId.in_([i.id for i in items_after]))
        .all()
    )
    data_list = [
        {
            "Item":        vd.item.itemNumber,
            "alt":         vd.item.alternate,
            "tagNo":       vd.item.id,
            "series":      vd.item.id,
            "size":        vd.item.id,
            "model":       vd.item.id,
            "type":        vd.item.id,
            "rating":      vd.item.id,
            "material":    vd.item.id,
            "unitprice":   vd.item.id,
            "qty":         vd.item.id,
            "total_price": vd.item.id,
        }
        for vd in valve_data_list
    ]
    return json.dumps(data_list)


# ---------------------------------------------------------------------------
# /project/project-delete
# ---------------------------------------------------------------------------

@bp.route('/project-delete', methods=['POST'])
@login_required
@error_handler
def project_delete():
    data       = request.get_json()
    project_id = data['projectId']
    project_   = db.session.get(projectMaster, int(project_id))
    creator    = db.session.get(userMaster, project_.createdById)

    if current_user.id != project_.createdById:
        return jsonify({'status': 'warning', 'message': f"Only the project creator '{creator.name}' can delete the project"}), 400

    all_projects = db.session.query(projectMaster).filter_by(user=current_user).all()

    if len(all_projects) == 1:
        _, new_item = _new_user_project_item(current_user)
        db.session.delete(project_)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Blank project added, deleted project successfully', 'proj': new_item.project.id, 'item': new_item.id})

    db.session.delete(project_)
    db.session.commit()

    remaining = db.session.query(projectMaster).filter_by(user=current_user).all()
    last_proj  = remaining[-1]
    last_item  = db.session.query(itemMaster).filter_by(project=last_proj).first()

    last_fcc_proj = getLatestFccLiveProject('last')
    if last_fcc_proj:
        project_num  = int(last_fcc_proj[1:])
        num_suffix   = project_num % 1000
        bucket_start = (num_suffix // 100) * 100
        prefix       = last_fcc_proj[:3]
        session['selected_bucket'] = (
            f"{prefix}{str(bucket_start).zfill(5)} - {prefix}{str(bucket_start + 99).zfill(5)}"
        )

    return jsonify({'status': 'success', 'message': 'Project deleted successfully', 'proj': last_proj.id, 'item': last_item.id})


# ---------------------------------------------------------------------------
# /project/import-project — Import project from Excel
# ---------------------------------------------------------------------------

@bp.route('/import-project/proj-<int:proj_id>/item-<int:item_id>', methods=['POST'])
@login_required
@error_handler
def import_project(item_id, proj_id):
    item = get_by_id(itemMaster, item_id)

    if request.method == 'POST':
        # --- quote number ---
        if current_user.fccUser and current_user.projType == 1:
            quote_no = request.form.get('quote_no', '').strip()
            if not re.fullmatch(r'Q\d{7}', quote_no):
                flash("Quote format should be 'Q' followed by 7 digit Number", 'failure')
                return render_template(
                    'project/import_project.html',
                    item=item, page='importProject', user=current_user,
                )
        elif current_user.fccUser and current_user.projType == 2:
            quote_no = generate_quote('T')
        else:
            quote_no = generate_quote('C')

        file = request.files.get('file')
        df = pd.read_excel(file, header=None, keep_default_na=False)

        # Testcase users get a simpler import path
        if current_user.projType == 2:
            testcase_module(item_id, proj_id, quote_no)
            return redirect(url_for('home.home', item_id=item_id, proj_id=proj_id))

        # ---- parse section indices ----
        def _find_index(marker: str) -> int:
            return df[df.apply(
                lambda row: row.astype(str).str.contains(marker).any(), axis=1
            )].index[0]

        items_index         = _find_index('Items')
        valveWarnings_index = _find_index('ValveWarnings')
        case_index          = _find_index('CaseDetails')
        caseWarnings_index  = _find_index('CaseWarnings')
        actuator_index      = _find_index('Actuator')
        volumetank_index    = _find_index('VolumeTank')
        accessories_index   = _find_index('Accessories')
        itemnotes_index     = _find_index('ItemNotes')
        customer_index      = _find_index('Customer')
        end_index           = _find_index('FinishExcel')

        # ---- parse project row ----
        proj_headers = df.iloc[1].to_list()
        proj_data    = df.iloc[2].to_list()

        _skip_proj = {'id', 'projectId', '', 'bidDueDate', 'receiptDate',
                      'enquiryReceivedDate', 'cur_revno', 'revisionNo'}
        project_details = {
            k: [v] for k, v in zip(proj_headers, proj_data) if k not in _skip_proj
        }

        # ---- parse customer ----
        cus_headers = df.iloc[customer_index + 1].to_list()
        cus_values  = df.iloc[customer_index + 2].to_list()
        cus_details = {
            k: get_null_or_value(v)
            for k, v in zip(cus_headers, cus_values)
            if k not in {'id', ''}
        }
        company_name    = [cus_details['Companyname'],  cus_details['Enduser']]
        company_address = [cus_details['Companyaddress'], cus_details['EnduserAdd']]
        engg_names      = [cus_details['AppEngg'],       cus_details['ContactEngg']]

        # ---- parse items ----
        item_headers = df.iloc[items_index + 1].to_list()
        _skip_item   = {'id', '', 'fluidPropertiesId', 'nde1Id', 'nde2Id', 'cur_revno'}
        all_items = [
            {k: [v] for k, v in zip(item_headers, df.iloc[r].to_list()) if k not in _skip_item}
            for r in range(items_index + 2, case_index - 1)
        ]

        # ---- parse valve warnings ----
        vw_headers = df.iloc[valveWarnings_index + 1].to_list()
        vw_start   = valveWarnings_index + 2
        vw_end     = end_index - 1
        all_valve_warnings = []
        if vw_start != vw_end:
            all_valve_warnings = [
                {k: [v] for k, v in zip(vw_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(vw_start, vw_end)
            ]

        # ---- parse cases ----
        case_headers = df.iloc[case_index + 1].to_list()
        cs_start = case_index + 2; cs_end = actuator_index - 1
        all_item_cases = []
        if cs_start != cs_end:
            all_item_cases = [
                {k: v for k, v in zip(case_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(cs_start, cs_end)
            ]

        # ---- parse case warnings ----
        warn_headers = df.iloc[caseWarnings_index + 1].to_list()
        cw_start = caseWarnings_index + 2; cw_end = valveWarnings_index - 1
        all_case_warnings = []
        if cw_start != cw_end:
            all_case_warnings = [
                {k: v for k, v in zip(warn_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(cw_start, cw_end)
            ]

        # ---- parse actuators ----
        act_headers = df.iloc[actuator_index + 1].to_list()
        _skip_act   = {'id', '', 'slidingActuatorId', 'actuatorMasterId', 'rotaryActuatorId'}
        act_start = actuator_index + 2; act_end = accessories_index - 1
        act_list = []
        all_actuators = []
        if act_start != act_end:
            act_list = [df.iloc[r] for r in range(act_start, act_end)]
            all_actuators = [
                {k: [v] for k, v in zip(act_headers, row) if k not in _skip_act}
                for row in act_list
            ]

        # ---- parse accessories ----
        acc_headers = df.iloc[accessories_index + 1].to_list()
        acc_start = accessories_index + 2; acc_end = volumetank_index - 1
        acc_list = []
        all_accessories = []
        if acc_start != acc_end:
            acc_list = [df.iloc[r] for r in range(acc_start, acc_end)]
            all_accessories = [
                {k: [v] for k, v in zip(acc_headers, row) if k not in {'id', ''}}
                for row in acc_list
            ]

        # ---- parse volume tanks ----
        vt_headers = df.iloc[volumetank_index + 1].to_list()
        vt_start = volumetank_index + 2; vt_end = itemnotes_index - 1
        all_volumetank = []
        if vt_start != vt_end:
            all_volumetank = [
                {k: v for k, v in zip(vt_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(vt_start, vt_end)
            ]

        # ---- parse item notes ----
        notes_headers = df.iloc[itemnotes_index + 1].to_list()
        note_start = itemnotes_index + 2; note_end = customer_index - 1
        all_itemnotes = []
        if note_start != note_end:
            all_itemnotes = [
                {k: [v] for k, v in zip(notes_headers, df.iloc[r]) if k not in {'id', ''}}
                for r in range(note_start, note_end)
            ]

        # ------------------------------------------------------------------ #
        # Persist project
        # ------------------------------------------------------------------ #
        new_project = projectMaster(
            user=current_user,
            projectRef='TBA',
            enquiryRef='TBA',
            isFccProject=current_user.fccUser,
        )
        try:
            new_project.quoteNo = quote_no
            db.session.add(new_project)
            db.session.commit()
        except IntegrityError as exc:
            import traceback
            # traceback.print_exc()
            db.session.rollback()
            if 'unique' in str(exc.orig).lower() or 'duplicate' in str(exc.orig).lower():
                flash('Quote Number already exists!', 'failure')
            else:
                flash('Database error occurred. Please try again.', 'failure')
            return render_template(
                'project/import_project.html',
                item=item, page='importProject', user=current_user,
            )

        time = datetime.now()
        project_details['IndustryId'] = [get_by_name(industryMaster, project_details['IndustryId'][0])]
        project_details['regionID']   = [get_by_name(regionMaster,   project_details['regionID'][0])]
        project_details['industry']   = project_details.pop('IndustryId')
        project_details['region']     = project_details.pop('regionID')

        for key in project_details:
            project_details[key] = get_null_or_value(project_details[key])

        new_project.revision            = 0
        new_project.cur_revno           = 0
        new_project.enquiryReceivedDate = time
        new_project.receiptDate         = time
        new_project.bidDueDate          = time
        new_project.industry            = project_details['industry'][0]
        new_project.region              = project_details['region'][0]
        new_project.trim_exit_velocity  = 'yes'
        db.session.commit()

        # ---- customers / addresses / engineers ----
        for idx, (cname, caddr, engg) in enumerate(
            zip(company_name, company_address, engg_names)
        ):
            company = db.session.query(companyMaster).filter_by(name=cname).first()
            if not company:
                company = companyMaster(name=cname)
                db.session.add(company)
                db.session.commit()

            if current_user.fccUser:
                address = db.session.query(addressMaster).filter_by(
                    address=caddr, companyId=company.id).first()
            else:
                address = db.session.query(addressMaster).filter_by(
                    address=caddr, companyId=company.id, user=current_user).first()

            if not address:
                address = addressMaster(
                    address=caddr, company=company,
                    user=current_user, isActive=True,
                )
                db.session.add(address)
                db.session.commit()

            db.session.add(addressProject(
                address=address, project=new_project, isCompany=(idx == 0),
            ))
            db.session.commit()

            engineer = db.session.query(engineerMaster).filter_by(name=engg).first()
            if not engineer:
                engineer = engineerMaster(name=engg, designation='Engineer')
                db.session.add(engineer)
                db.session.commit()

            db.session.add(engineerProject(
                project=new_project, engineer=engineer, isApplication=(idx == 0),
            ))
            db.session.commit()

        # ---- items ----
        item_element_dict = {}
        val_ele  = {}
        item_num = 1
        valve_num = 1

        for item_ in all_items:
            new_item = itemMaster(project=new_project)
            db.session.add(new_item)
            db.session.commit()

            for key in item_:
                item_[key] = get_null_or_value(item_[key])

            new_item.update(item_, new_item.id)
            item_element_dict[item_num] = new_item

            new_item.revision       = 0
            new_item.itemNumber     = item_num
            new_item.draft_status   = -1
            new_item.initial_status = 1
            new_item.cur_revType    = 'initial'
            new_item.cur_status     = 'In progress'
            new_item.cur_revno      = 0
            db.session.commit()
            item_num += 1

            if not acc_list:
                db.session.add(accessoriesData(item=new_item, revision=0, draft_status=-1))
                db.session.commit()

            if not act_list:
                db.session.add(actuatorMaster(item=new_item, revision=0, draft_status=-1))
                db.session.commit()

            db.session.add(itemRevisionTable(
                item=new_item,
                itemRevisionNo=0,
                status='In progress',
                prepared_by=current_user.code,
                time=datetime.today().strftime('%Y-%m-%d %H:%M'),
            ))
            db.session.commit()

            # valve details
            new_valve = valveDetailsMaster(item=new_item)
            db.session.add(new_valve)
            db.session.commit()

            item_ = clean_item_data(item_)
            item_['isActive']  = [1]
            item_['solveCase'] = [1]
            if item_['minTemp'] == (None,):
                item_['minTemp'] = (0,)

            item_ = map_valve_fk(item_)
            new_valve.update(item_, new_valve.id)
            new_valve.revision        = 0
            new_valve.draft_status    = -1
            new_valve.fluidproperties = None
            new_valve.nde1__          = None
            new_valve.nde2__          = None
            db.session.commit()

            val_ele[valve_num] = new_valve
            valve_num += 1

        # ---- valve warnings ----
        for vwar in all_valve_warnings:
            val_element = val_ele[vwar['valveWarningId'][0]]
            for key in vwar:
                vwar[key] = get_null_or_value(vwar[key])

            new_vw = valveDataWarnings(valve_warning=val_element)
            db.session.add(new_vw)
            db.session.commit()

            vw_obj = db.session.get(valveDataWarnings, new_vw.id)
            del vwar['valveWarningId']
            vw_obj.update(vwar, vw_obj.id)

        # ---- cases ----
        case_element = {}
        case_num     = 1
        _case_kv = {'flowrate', 'inletPressure', 'outletPressure', 'inletTemp',
                    'specificHeatRatio', 'specificGravity', 'molecularWeight',
                    'kinematicViscosity'}

        for case_ in all_item_cases:
            item_element = item_element_dict[case_['itemId']]
            case_['revision'] = -1

            for key in case_:
                case_[key] = getCheckedValue(case_[key])
                case_[key] = int_to_float_convertor(case_[key])
                if key in _case_kv and case_[key] is None:
                    case_[key] = 0

            new_case = caseMaster(item=item_element)
            db.session.add(new_case)
            db.session.commit()

            if case_['cv_lists'] is not None:
                case_['cv_lists'] = [float(x.strip()) for x in case_['cv_lists'].split(',')]

            del case_['itemId']
            case_obj = db.session.get(caseMaster, new_case.id)
            case_obj.update(case_, case_obj.id)
            case_obj.revision     = 0
            case_obj.draft_status = -1
            db.session.commit()

            case_element[case_num] = new_case
            case_num += 1

        # ---- case warnings ----
        for war_ in all_case_warnings:
            case_ele = case_element[war_['caseId']]
            for key in war_:
                war_[key] = get_null_or_value(war_[key])

            new_cw = caseWarnings(case=case_ele)
            db.session.add(new_cw)
            db.session.commit()

            cw_obj = db.session.get(caseWarnings, new_cw.id)
            del war_['caseId']
            cw_obj.update(war_, cw_obj.id)

        # ---- actuators ----
        act_element_dict = {}
        act_count = 1

        for act_ in all_actuators:
            item_element = item_element_dict[act_['itemId'][0]]
            del act_['itemId']

            new_act = actuatorMaster(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_act)
            db.session.commit()
            act_element_dict[act_count] = new_act
            act_count += 1

            act_['revision']     = [0]
            act_['draft_status'] = [-1]
            for key in act_:
                act_[key] = get_null_or_value(act_[key])

            act_obj = db.session.get(actuatorMaster, new_act.id)
            act_obj.update(act_, act_obj.id)

            if new_act.actSelectionType == 'sliding':
                new_act_case = actuatorCaseData(
                    actuator_=new_act, revision=0, draft_status=-1,
                )
                db.session.add(new_act_case)
                db.session.commit()

                act_ = map_actuator_fk(act_)
                act_case_obj = db.session.get(actuatorCaseData, new_act_case.id)
                act_case_obj.update(act_, act_case_obj.id)
                act_case_obj.revision     = 0
                act_case_obj.draft_status = -1
                db.session.commit()

            elif new_act.actSelectionType == 'rotary':
                new_rot_case = rotaryCaseData(
                    actuator_=new_act, revision=0, draft_status=-1,
                )
                db.session.add(new_rot_case)
                db.session.commit()

                rot_obj = db.session.get(rotaryCaseData, new_rot_case.id)
                rot_obj.update(act_, rot_obj.id)
                rot_obj.revision     = 0
                rot_obj.draft_status = -1
                db.session.commit()

        # ---- volume tanks ----
        for vt_ in all_volumetank:
            act_element = act_element_dict[vt_['actuatorMasterId']]

            new_vt = volumeTank(actuator_=act_element)
            db.session.add(new_vt)
            db.session.commit()

            vt_obj = db.session.get(volumeTank, new_vt.id)
            for key in vt_:
                vt_[key] = getCheckedValue(vt_[key])

            del vt_['actuatorMasterId']
            if vt_.get('end_of_strokes') not in ('', 'N/A', None):
                vt_['end_of_strokes'] = ast.literal_eval(vt_['end_of_strokes'])
            vt_['revision'] = 0
            vt_obj.update(vt_, vt_obj.id)
            db.session.commit()

        # ---- accessories ----
        for acc_ in all_accessories:
            item_element = item_element_dict[acc_['itemId'][0]]
            new_acc = accessoriesData(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_acc)
            db.session.commit()

            acc_obj = db.session.get(accessoriesData, new_acc.id)
            for key in acc_:
                acc_[key] = get_null_or_value(acc_[key])
            del acc_['itemId']
            acc_['revision']     = [0]
            acc_['draft_status'] = [-1]
            acc_obj.update(acc_, acc_obj.id)
            db.session.commit()

        # ---- item notes ----
        for note_ in all_itemnotes:
            item_element = item_element_dict[note_['itemId'][0]]
            new_note = itemNotesData(item=item_element, revision=0, draft_status=-1)
            db.session.add(new_note)
            db.session.commit()

            note_obj = db.session.get(itemNotesData, new_note.id)
            for key in note_:
                note_[key] = get_null_or_value(note_[key])
            del note_['itemId']
            note_['revision']     = [0]
            note_['draft_status'] = [-1]
            note_obj.update(note_, note_obj.id)
            db.session.commit()

        flash('Project imported successfully', 'success')
        return redirect(url_for('home.home', item_id=item_id, proj_id=proj_id))


# ---------------------------------------------------------------------------
# /project/export-project — Export project data as Excel
# ---------------------------------------------------------------------------

@bp.route('/export-project', methods=['GET'])
@login_required
@error_handler
def export_project():
    """
    Export all project data (items, cases, actuators, accessories, notes,
    customer, warnings, volume-tank) to an Excel workbook and send it as
    a file download.

    Query params:
        proj_id     — project ID
        item_id     — item ID
        export_proj — project revision number to export up to
    """
    proj_id         = request.args.get('proj_id')
    item_id         = request.args.get('item_id')
    export_proj_rev = request.args.get('export_proj')
    project_element = get_db_element_with_id(projectMaster, proj_id)

    proj_rev_list = (
        db.session.query(projectRevisionTable)
        .filter(
            projectRevisionTable.project == project_element,
            projectRevisionTable.projectRevision <= export_proj_rev,
            projectRevisionTable.item != None,
        )
        .order_by(projectRevisionTable.id)
        .all()
    )
    if not current_user.fccUser:
        proj_rev_list = db.session.query(itemMaster).filter_by(project=project_element).all()

    project_elements = db.session.query(projectMaster).filter_by(id=proj_id).all()
    address_c, address_e, eng_a, eng_c = get_eng_addr_project(project_element)
    heading = [
        ['Project'], ['Items'], ['CaseDetails'], ['Actuator'], ['Accessories'],
        ['ItemNotes'], ['FinishExcel'], ['Customer'], ['CaseWarnings'],
        ['ValveWarnings'], ['VolumeTank'],
    ]

    # Master-table lookup map for FK fields
    key_table = {
        'ratingId':           ratingMaster,
        'materialId':         materialMaster,
        'designStandardId':   designStandard,
        'valveStyleId':       valveStyle,
        'fluidStateId':       fluidState,
        'fluidPropertiesId':  fluidProperties,
        'endConnectionId':    endConnection,
        'endFinishId':        endFinish,
        'bodyFFDimenId':      bodyFFDimension,
        'bonnetTypeId':       bonnetType,
        'packingTypeId':      packingType,
        'trimTypeId':         trimType,
        'flowCharacterId':    flowCharacter,
        'flowDirectionId':    flowDirection,
        'plugId':             plug,
        'seatLeakageClassId': seatLeakageClass,
        'bonnetId':           bonnet,
        'nde1Id':             nde1,
        'nde2Id':             nde2,
        'shaftId':            shaft,
        'discId':             disc,
        'seatId':             seat,
        'sealId':             seal,
        'packingId':          packing,
        'balancingId':        balancing,
        'balanceSealId':      balanceSeal,
        'studNutId':          studNut,
        'gasketId':           gasket,
        'cageId':             cageClamp,
        'packingFrictionId':  packingFriction,
        'packingTorqueId':    packingTorque,
        'seatLoadId':         seatLoadForce,
        'fluidId' : fluidProperties
    }

    # Pre-load all master-table lookups into dicts — eliminates 30×N_items individual DB queries
    _master_name_cache = {}
    for _f, _t in key_table.items():
        if _f == 'fluidId':
            _master_name_cache[_f] = {r.id: r.fluidName for r in db.session.query(_t).all()}
        else:
            _master_name_cache[_f] = {r.id: getattr(r, 'name', None) for r in db.session.query(_t).all()}

    _industry_cache = {r.id: r.name for r in db.session.query(industryMaster).all()}
    _region_cache   = {r.id: r.name for r in db.session.query(regionMaster).all()}

    def _name_from_master(field, id_):
        return _master_name_cache.get(field, {}).get(int(id_))

    wb = Workbook()
    ws = wb.active

    # ---- Project ----
    ws.append(heading[0])
    all_keys = projectMaster.__table__.columns.keys()
    all_keys.remove('createdById')
    ws.append(all_keys)
    for data_ in project_elements:
        single_row_data = []
        for key_ in all_keys:
            if key_ == 'createdById':
                continue
            abc = getattr(data_, key_, None)
            if abc:
                if key_ == 'IndustryId':
                    single_row_data.append(_industry_cache.get(int(abc), abc))
                elif key_ == 'regionID':
                    single_row_data.append(_region_cache.get(int(abc), abc))
                elif key_ == 'revisionNo':
                    single_row_data.append(1)
                elif key_ == 'id':
                    single_row_data.append(1)
                else:
                    single_row_data.append(abc)
            else:
                single_row_data.append('N/A')
        ws.append(single_row_data)
    ws.append([])

    # ---- Items ----
    ws.append(heading[1])
    item_datas  = itemMaster.__table__.columns.keys()
    valve_datas = valveDetailsMaster.__table__.columns.keys()
    item_datas.remove('projectID')
    valve_datas.remove('id')
    valve_datas.remove('itemId')
    allkeys_item = item_datas + valve_datas
    item_id_ctr = 1; case_id = 1; act_id = 1; acc_id = 1
    itemnotes_id = 1; voltank_id = 1
    item_details = []; case_details = []; act_details = []; accessories_ = []
    item_notes = []; customer_details = []; case_warnings = []
    valve_warnings_ = []; volume_tank_ = []

    valve_map_ = {}
    vl = 1

    # ---- Column key lists (computed once, not per-item) ----
    all_keys_valve_warnings = valveDataWarnings.__table__.columns.keys()
    all_keys_cases          = caseMaster.__table__.columns.keys()
    if 'itemId' in all_keys_cases:
        all_keys_cases.remove('itemId')
        all_keys_cases.insert(1, 'itemId')
    all_keys_warnings    = caseWarnings.__table__.columns.keys()
    all_keys_actuator    = actuatorMaster.__table__.columns.keys()
    if 'itemId' in all_keys_actuator:
        all_keys_actuator.remove('itemId')
        all_keys_actuator.insert(1, 'itemId')
    all_keys_volumetank  = volumeTank.__table__.columns.keys()
    all_keys_rotaryCase  = rotaryCaseData.__table__.columns.keys()
    all_keys_slidingCase = actuatorCaseData.__table__.columns.keys()
    all_keys_accessories = accessoriesData.__table__.columns.keys()
    if 'itemId' in all_keys_accessories:
        all_keys_accessories.remove('itemId')
        all_keys_accessories.insert(1, 'itemId')
    all_keys_itemNotes = itemNotesData.__table__.columns.keys()
    if 'itemId' in all_keys_itemNotes:
        all_keys_itemNotes.remove('itemId')
        all_keys_itemNotes.insert(1, 'itemId')

    # ---- Batch-load all child records for all items (replaces N queries per section) ----
    _item_rev_pairs = [
        (pr.item, pr.itemRevision) if current_user.fccUser else (pr, 0)
        for pr in proj_rev_list
    ]
    _all_item_ids = [pair[0].id for pair in _item_rev_pairs]

    # valves
    _valve_bulk = (
        db.session.query(valveDetailsMaster)
        .filter(valveDetailsMaster.itemId.in_(_all_item_ids))
        .all()
    ) if _all_item_ids else []
    _valve_by_item_rev = {(v.itemId, v.revision): v for v in _valve_bulk}

    # valve warnings
    _all_valve_ids = [v.id for v in _valve_bulk]
    _vwarn_bulk = (
        db.session.query(valveDataWarnings)
        .filter(valveDataWarnings.valveWarningId.in_(_all_valve_ids))
        .all()
    ) if _all_valve_ids else []
    _vwarn_by_valve = {w.valveWarningId: w for w in _vwarn_bulk}

    # cases
    _cases_bulk = (
        db.session.query(caseMaster)
        .filter(caseMaster.itemId.in_(_all_item_ids))
        .order_by(caseMaster.id)
        .all()
    ) if _all_item_ids else []
    _cases_by_item_rev = defaultdict(list)
    for _c in _cases_bulk:
        _cases_by_item_rev[(_c.itemId, _c.revision)].append(_c)

    # case warnings
    _all_case_ids = [_c.id for _c in _cases_bulk]
    _cwarn_bulk = (
        db.session.query(caseWarnings)
        .filter(caseWarnings.caseId.in_(_all_case_ids))
        .all()
    ) if _all_case_ids else []
    _cwarn_by_case = defaultdict(list)
    for _w in _cwarn_bulk:
        _cwarn_by_case[_w.caseId].append(_w)

    # actuators
    _act_bulk = (
        db.session.query(actuatorMaster)
        .filter(actuatorMaster.itemId.in_(_all_item_ids))
        .all()
    ) if _all_item_ids else []
    _act_by_item_rev = defaultdict(list)
    for _a in _act_bulk:
        _act_by_item_rev[(_a.itemId, _a.revision)].append(_a)

    _all_act_ids = [_a.id for _a in _act_bulk]

    # volume tanks
    _vtank_bulk = (
        db.session.query(volumeTank)
        .filter(volumeTank.actuatorMasterId.in_(_all_act_ids))
        .all()
    ) if _all_act_ids else []
    _vtank_by_act_rev = {(v.actuatorMasterId, v.revision): v for v in _vtank_bulk}

    # rotary case data
    _rotary_bulk = (
        db.session.query(rotaryCaseData)
        .filter(rotaryCaseData.actuatorMasterId.in_(_all_act_ids))
        .all()
    ) if _all_act_ids else []
    _rotary_by_act_rev = {(r.actuatorMasterId, r.revision): r for r in _rotary_bulk}

    # sliding (actuator case) data
    _sliding_bulk = (
        db.session.query(actuatorCaseData)
        .filter(actuatorCaseData.actuatorMasterId.in_(_all_act_ids))
        .all()
    ) if _all_act_ids else []
    _sliding_by_act_rev = {(s.actuatorMasterId, s.revision): s for s in _sliding_bulk}

    # accessories
    _acc_bulk = (
        db.session.query(accessoriesData)
        .filter(accessoriesData.itemId.in_(_all_item_ids))
        .all()
    ) if _all_item_ids else []
    _acc_by_item_rev = defaultdict(list)
    for _a in _acc_bulk:
        _acc_by_item_rev[(_a.itemId, _a.revision)].append(_a)

    # item notes
    _notes_bulk = (
        db.session.query(itemNotesData)
        .filter(itemNotesData.itemId.in_(_all_item_ids))
        .all()
    ) if _all_item_ids else []
    _notes_by_item_rev = defaultdict(list)
    for _n in _notes_bulk:
        _notes_by_item_rev[(_n.itemId, _n.revision)].append(_n)
    for proj_rev in proj_rev_list:
        if current_user.fccUser:
            data_              = proj_rev.item
            export_proj_revision = proj_rev.itemRevision
        else:
            data_              = proj_rev
            export_proj_revision = 0

        # item row
        single_row_data = []
        for key_ in item_datas:
            abc = getattr(data_, key_)
            single_row_data.append(item_id_ctr if key_ == 'id' else abc)

        # valve row
        valve_item = _valve_by_item_rev.get((data_.id, export_proj_revision))
        single_row_data_valve = []
        v_warnings = _vwarn_by_valve.get(valve_item.id) if valve_item else None
        single_row_valve_warnings = []

        for key_ in valve_datas:
            abc = getattr(valve_item, key_)
            if abc:
                if key_ in key_table:
                    single_row_data_valve.append(_name_from_master(key_, abc))
                else:
                    single_row_data_valve.append(abc)
            else:
                single_row_data_valve.append('N/A')
        item_details.append(single_row_data + single_row_data_valve)
        valve_map_[valve_item] = vl
        vl += 1

        if v_warnings:
            for keys in all_keys_valve_warnings:
                abc_ = getattr(v_warnings, keys)
                if abc_:
                    if keys == 'valveWarningId':
                        single_row_valve_warnings.append(valve_map_[valve_item])
                    else:
                        single_row_valve_warnings.append(abc_)
            valve_warnings_.append(single_row_valve_warnings)

        # ---- Cases ----
        cases_ = _cases_by_item_rev.get((data_.id, export_proj_revision), [])
        single_row_data_warnings = []
        for case_ in cases_:
            case_warns = _cwarn_by_case.get(case_.id, [])
            if case_warns:
                c_id = 1
                for warn_ in case_warns:
                    case__ = []
                    for key_ in all_keys_warnings:
                        abc = getattr(warn_, key_)
                        if abc:
                            if key_ == 'id':
                                case__.append(c_id)
                            elif key_ == 'caseId':
                                case__.append(case_id)
                            else:
                                case__.append(abc)
                        else:
                            case__.append('N/A')
                    single_row_data_warnings.append(case__)
                    c_id += 1

            single_row_data_case = []
            for key_ in all_keys_cases:
                abc = getattr(case_, key_)
                if abc:
                    if key_ == 'id':
                        single_row_data_case.append(case_id)
                    elif key_ == 'cv_lists':
                        single_row_data_case.append(', '.join(str(v) for v in abc))
                    elif key_ == 'itemId':
                        single_row_data_case.append(item_id_ctr)
                    elif key_ not in ['valveDiaId', 'fluidId']:
                        single_row_data_case.append(abc)
                else:
                    single_row_data_case.append('N/A')
            case_details.append(single_row_data_case)
            case_id += 1
        case_warnings.append(single_row_data_warnings)

        # ---- Actuators ----
        actuator_mas = _act_by_item_rev.get((data_.id, export_proj_revision), [])
        for act_ in actuator_mas:
            vol_tank_data = _vtank_by_act_rev.get((act_.id, export_proj_revision))
            if vol_tank_data:
                single_row_data_voltank = []
                for key_ in all_keys_volumetank:
                    abc = getattr(vol_tank_data, key_)
                    if abc:
                        if key_ == 'id':
                            single_row_data_voltank.append(voltank_id)
                        elif key_ == 'actuatorMasterId':
                            single_row_data_voltank.append(act_id)
                        elif key_ == 'end_of_strokes':
                            single_row_data_voltank.append(str(abc))
                        else:
                            single_row_data_voltank.append(abc)
                    else:
                        single_row_data_voltank.append('N/A')
                voltank_id += 1
                volume_tank_.append(single_row_data_voltank)

            single_row_data_act = []
            for key_ in all_keys_actuator:
                abc = getattr(act_, key_)
                if abc:
                    if key_ == 'id':
                        single_row_data_act.append(act_id)
                    elif key_ == 'itemId':
                        single_row_data_act.append(item_id_ctr)
                    elif key_ not in ['valveDiaId', 'fluidId']:
                        single_row_data_act.append(abc)
                else:
                    single_row_data_act.append('N/A')

            if act_.actuatorType in ['SY', 'SYC', 'SYCDA']:
                actuator_case = _rotary_by_act_rev.get((act_.id, export_proj_revision))
                if actuator_case:
                    for _ in all_keys_slidingCase:
                        single_row_data_act.append('N/A')
                    for key_ in all_keys_rotaryCase:
                        abc = getattr(actuator_case, key_)
                        if abc:
                            if key_ in key_table:
                                single_row_data_act.append(_name_from_master(key_, abc))
                            else:
                                single_row_data_act.append(abc)
                        else:
                            single_row_data_act.append('N/A')
            else:
                actuator_case = _sliding_by_act_rev.get((act_.id, export_proj_revision))
                if actuator_case:
                    for key_ in all_keys_slidingCase:
                        abc = getattr(actuator_case, key_)
                        if abc:
                            if key_ in key_table:
                                single_row_data_act.append(_name_from_master(key_, abc))
                            else:
                                single_row_data_act.append(abc)
                        else:
                            single_row_data_act.append('N/A')
                    for _ in all_keys_rotaryCase:
                        single_row_data_act.append('N/A')

            act_details.append(single_row_data_act)
            act_id += 1

        # ---- Accessories ----
        for acc_ in _acc_by_item_rev.get((data_.id, export_proj_revision), []):
            single_row_data_accessories = []
            for key_ in all_keys_accessories:
                abc = getattr(acc_, key_)
                if abc:
                    if key_ == 'id':
                        single_row_data_accessories.append(acc_id)
                    elif key_ == 'itemId':
                        single_row_data_accessories.append(item_id_ctr)
                    else:
                        single_row_data_accessories.append(abc)
                else:
                    single_row_data_accessories.append('N/A')
            accessories_.append(single_row_data_accessories)
            acc_id += 1

        # ---- Item Notes ----
        for notes_ in _notes_by_item_rev.get((data_.id, export_proj_revision), []):
            single_row_data_itemnotes = []
            for key_ in all_keys_itemNotes:
                abc = getattr(notes_, key_)
                if abc:
                    if key_ == 'id':
                        single_row_data_itemnotes.append(itemnotes_id)
                    elif key_ == 'itemId':
                        single_row_data_itemnotes.append(item_id_ctr)
                    else:
                        single_row_data_itemnotes.append(abc)
                else:
                    single_row_data_itemnotes.append('N/A')
            item_notes.append(single_row_data_itemnotes)
            itemnotes_id += 1

        item_id_ctr += 1

    # ---- Customer ----
    customer_key_datas = ['Companyname', 'Companyaddress', 'Enduser', 'EnduserAdd', 'AppEngg', 'ContactEngg']
    customer_values = []
    for key_ in customer_key_datas:
        if key_ == 'Companyname':
            customer_values.append(address_c.address.company.name)
        elif key_ == 'Companyaddress':
            customer_values.append(address_c.address.address)
        elif key_ == 'Enduser':
            customer_values.append(address_e.address.company.name)
        elif key_ == 'EnduserAdd':
            customer_values.append(address_e.address.address)
        elif key_ == 'AppEngg':
            customer_values.append(eng_a.engineer.name)
        elif key_ == 'ContactEngg':
            customer_values.append(eng_c.engineer.name)
    customer_details.append(customer_values)

    # ---- Write all sections ----
    item_details.insert(0, allkeys_item)
    for row in item_details:
        ws.append(row)

    ws.append([])
    ws.append(heading[2])
    case_details.insert(0, all_keys_cases)
    for row in case_details:
        ws.append(row)

    ws.append([])
    ws.append(heading[3])
    all_keys_actdatas = all_keys_actuator + all_keys_slidingCase + all_keys_rotaryCase
    act_details.insert(0, all_keys_actdatas)
    for row in act_details:
        ws.append(row)

    ws.append([])
    ws.append(heading[4])
    accessories_.insert(0, all_keys_accessories)
    for row in accessories_:
        ws.append(row)

    ws.append([])
    ws.append(heading[10])
    volume_tank_.insert(0, all_keys_volumetank)
    for row in volume_tank_:
        ws.append(row)

    ws.append([])
    ws.append(heading[5])
    item_notes.insert(0, all_keys_itemNotes)
    for row in item_notes:
        ws.append(row)

    ws.append([])
    ws.append(heading[7])
    customer_details.insert(0, customer_key_datas)
    for row in customer_details:
        ws.append(row)

    ws.append([])
    ws.append(heading[8])
    case_warnings.insert(0, all_keys_warnings)
    az = 0
    for cas_ in case_warnings:
        if az == 0:
            ws.append(cas_)
            az = 1
        else:
            for wr_ in cas_:
                ws.append(wr_)

    ws.append([])
    ws.append(heading[9])
    valve_warnings_.insert(0, all_keys_valve_warnings)
    for row in valve_warnings_:
        ws.append(row)

    ws.append([])
    ws.append(heading[6])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"{projectMaster.__tablename__}.xlsx",
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')