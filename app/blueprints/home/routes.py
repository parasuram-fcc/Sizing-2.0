"""
routes.py — Home blueprint routes.

Kept intentionally thin: read args, call helpers, render.
All DB logic lives in helpers.py.
"""

from datetime import datetime
from inspect import getmembers

import re

from flask import render_template, request, session, flash, jsonify, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, distinct
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

from app.blueprints.home import bp
from app.extensions import db
from app.models.master import (
    industryMaster,
    regionMaster,
    fluidState,
    addressMaster,
    companyMaster,
    engineerMaster,
)
from app.models.transactional import (
    itemMaster,
    projectMaster,
    userMaster,
    projectRevisionTable,
    itemRevisionTable,
    valveDetailsMaster,
    caseMaster,
    actuatorMaster,
    actuatorCaseData,
    strokeCase,
    rotaryCaseData,
    volumeTank,
    accessoriesData,
    itemNotesData,
    addressProject,
    engineerProject,
)
from app.blueprints.home.helpers import (
    _PROJECT_LOAD_ONLY,
    apply_project_search,
    build_item_query,
    build_project_query,
    get_fcc_user_ids,
    get_items_for_project,
    get_last_Q25,
    get_last_Q26,
    getLatestFccLiveProject,
    load_revisions,
    make_project_groups,
    resolve_project_bucket,
    resolve_selected_project,
    serialize_item,
    serialize_project,
)


# ---------------------------------------------------------------------------
# /home — Dashboard
# ---------------------------------------------------------------------------

@bp.route('/home', defaults={'proj_id': None, 'item_id': None})
@bp.route('/home/proj-<int:proj_id>/item-<int:item_id>', methods=['GET'])
@login_required
def home(proj_id, item_id):
    """
    Main dashboard route.

    For FCC users: builds a project list from a bucket or 'All'/'Obsolete'
    selection, applies optional search, resolves the selected project and
    item, fires revision queries, then renders the dashboard template or
    returns partial HTML/JSON for AJAX requests.
    """
    user = current_user
    selected_bucket = None
    all_buckets = []
    all_projects = []
    use_quote_order = False   # True for show_all / bucket-range queries
    suffix = year = None      # set by build_project_query when use_quote_order=True

    # =========================================================
    # 1. BUILD PROJECT QUERY
    # =========================================================
    if user.fccUser:
        user_ids_subq = get_fcc_user_ids()
        last_Q26 = get_last_Q26()
        last_Q25 = get_last_Q25()

        if not user.projType:
            user.projType = 1

        # ------ Live projects (projType == 1) ------
        if user.projType == 1:
            getLatestFccLiveProject('last')   # side-effect: warms up cache if any

            selected_bucket = resolve_project_bucket(request, session, last_Q26)

            Q26_buckets = make_project_groups(last_Q26, 'Q2600000', 100)[::-1]
            Q25_buckets = make_project_groups(last_Q25, 'Q2500000', 100)[::-1]
            all_buckets.extend(Q26_buckets)
            all_buckets.extend(Q25_buckets)
            all_buckets += ["All", "Obsolete"]

            obsolete = selected_bucket == 'Obsolete'
            show_all = selected_bucket == 'All'

            query_, suffix, year = build_project_query(
                user_ids_subq, selected_bucket, obsolete, show_all
            )
            # Bucket-range and show_all queries order by encoded year+suffix;
            # obsolete projects have no valid quoteNo so fall back to id.
            use_quote_order = not obsolete

        # ------ Testcase projects (projType == 2) ------
        elif user.projType == 2:
            query_ = (
                db.session.query(projectMaster)
                .options(
                    load_only(*_PROJECT_LOAD_ONLY),
                    selectinload(projectMaster.region).load_only(regionMaster.name),
                    selectinload(projectMaster.industry).load_only(industryMaster.name),
                    selectinload(projectMaster.user).load_only(
                        userMaster.email, userMaster.fccUser
                    ),
                )
                .filter(
                    projectMaster.createdById.in_(user_ids_subq),
                    or_(
                        projectMaster.quoteNo.like('Q24TC%'),
                        projectMaster.quoteNo.like('Q25TC%'),
                        projectMaster.quoteNo.like('Q26TC%'),
                        projectMaster.quoteNo.like('T%'),
                    ),
                )
            )

    # ------ Non-FCC users ------
    else:
        query_ = (
            db.session.query(projectMaster)
            .options(
                load_only(*_PROJECT_LOAD_ONLY),
                selectinload(projectMaster.region).load_only(regionMaster.name),
                selectinload(projectMaster.industry).load_only(industryMaster.name),
                selectinload(projectMaster.user).load_only(
                    userMaster.email, userMaster.fccUser
                ),
            )
            .filter(projectMaster.user == current_user)
        )

    # =========================================================
    # 2. APPLY SEARCH + EXECUTE
    # =========================================================
    search_type = request.args.get('search_type')
    search_value = request.args.get('search_value')
    row_type = request.args.get('type')

    if row_type == 'project' and search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

    if use_quote_order:
        all_projects = query_.order_by(year.desc(), suffix.desc()).all()
    else:
        all_projects = query_.order_by(projectMaster.id.desc()).all()

    if not all_projects:
        flash('No projects to display', 'failure')

    # =========================================================
    # 3. RESOLVE SELECTED PROJECT  (Task 1f / Task 2d)
    # =========================================================
    if proj_id:
        selected_project = resolve_selected_project(proj_id, all_projects)
        random_data = 'no'
    else:
        selected_project = all_projects[0] if all_projects else None
        if selected_project:
            proj_id = selected_project.id
        random_data = 'yes'

    if request.args.get('reload_source') == 'project_dropdown':
        random_data = 'yes'

    # =========================================================
    # 4. ITEMS  (project_id_for_items computed ONCE — Task 2d)
    # =========================================================
    project_id_for_items = (
        selected_project.id if selected_project
        else (int(proj_id) if proj_id else None)
    )

    items_list = []
    item_element = None

    if project_id_for_items:
        # Minimal-column query — enough to obtain item_element and item_id.
        # Full-column query for serialization is deferred to get_items_for_project().
        item_query = build_item_query(
            project_id_for_items,
            search_type if row_type == 'item' else None,
            search_value if row_type == 'item' else None,
        )
        items_list = item_query.order_by(itemMaster.itemNumber.asc()).all()
        item_element = items_list[0] if items_list else None

    # item_id is always derived from the first item in the list
    # (the URL's item_id parameter is used only as a path-shape hint).
    resolved_item_id = item_element.id if item_element else None

    # =========================================================
    # 5. REVISIONS
    # =========================================================
    if proj_id and resolved_item_id:
        proj_rev, item_rev = load_revisions(int(proj_id), resolved_item_id)
    else:
        proj_rev, item_rev = [0], [0]

    if not user.fccUser:
        proj_rev, item_rev = [0], [0]

    # =========================================================
    # 6. AJAX DISPATCH
    # =========================================================
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        if row_type == 'item':
            if project_id_for_items:
                items = get_items_for_project(
                    project_id_for_items, search_type, search_value
                )
                if items:
                    return jsonify({"items": [serialize_item(i) for i in items]})
            return jsonify({"output": "no data"})

        elif row_type == 'project':
            return render_template(
                "project_rows.html",
                projects=all_projects,
                item=item_element,
                random_data=random_data,
            )

        return ''

    # =========================================================
    # 7. FULL PAGE RENDER
    # =========================================================
    # proj_ref from selected_project (already loaded, no lazy hit)
    proj_ref = selected_project.projectRef if selected_project else ''

    return render_template(
        'home/dashboard.html',
        random_data=random_data,
        user=current_user,
        selected_bucket=selected_bucket,
        projects=all_projects,
        item=item_element,
        # Task 3b: pass IDs only — JS derives them from URL via getCurrentIds()
        f_projId=all_projects[0].id if all_projects else None,
        f_itemId=items_list[0].id if items_list else None,
        items_len=len(items_list),
        page='home',
        proj_rev=proj_rev,
        item_rev=item_rev,
        all_buckets=all_buckets,
        proj_ref=proj_ref,
        # Task 3a: items / sizes / models REMOVED — confirmed in commented HTML block
        # (dashboard.html lines 672–765 is inside <!-- --> so these vars are dead weight)
    )


# ---------------------------------------------------------------------------
# /get_items_only — standalone AJAX endpoint (called by JS on page load)
# ---------------------------------------------------------------------------

@bp.route('/get_items_only/proj-<int:proj_id>', methods=['GET'])
@login_required
def get_items_only(proj_id):
    """
    Return a JSON list of items for a project.

    Task 4: project_id accepted as int via route converter.
    Always queries with all columns needed for serialization so
    serialize_item() never triggers lazy loads.

    JS expects: {"items": [...]} — keys defined in serialize_item().
    """
    search_type = request.args.get('search_type')
    search_value = request.args.get('search_value')

    items = get_items_for_project(proj_id, search_type, search_value)
    return jsonify({"items": [serialize_item(i) for i in items]})


# ---------------------------------------------------------------------------
# /load_projects — AJAX endpoint for dynamic project table
# ---------------------------------------------------------------------------

@bp.route('/load_projects', methods=['GET'])
@login_required
def load_projects():
    """
    Return a JSON list of projects for the dashboard project table.

    Replaces the server-rendered {% include 'home/project_rows.html' %} so the
    table refreshes without a full page reload (bucket change, search, initial load).

    Query params:
        quote_range  — bucket string like 'Q26000 - Q26099', 'All', 'Obsolete'.
                       Saved to session when supplied; falls back to session /
                       last-known bucket otherwise.
        search_type  — 'quote' | 'customer' | 'region' | 'engineer'
        search_value — raw search string

    User-type behaviour mirrors /home exactly:
        fccUser + projType=1  → bucket/live-project query
        fccUser + projType=2  → testcase pattern filter
        non-fcc / auth user   → own projects only
    """
    user = current_user
    use_quote_order = False
    suffix = year = None

    # ── 1. Build base project query (same logic as /home) ─────────────────
    if user.fccUser:
        user_ids_subq = get_fcc_user_ids()

        if not user.projType:
            user.projType = 1

        if user.projType == 1:
            last_Q26 = get_last_Q26()
            last_Q25 = get_last_Q25()

            # Resolve selected bucket (mirrors resolve_project_bucket but
            # accepts 'quote_range' param instead of 'set-projects')
            quote_range = request.args.get('quote_range')
            if quote_range:
                session['selected_bucket'] = quote_range
                selected_bucket = quote_range
            elif session.get('selected_bucket'):
                selected_bucket = session['selected_bucket']
            else:
                # Derive default from latest Q26 project (same as resolve_project_bucket)
                if last_Q26:
                    last_num = int(last_Q26[3:])
                    bucket_start = (last_num // 100) * 100
                    bucket_end   = bucket_start + 99
                    selected_bucket = (
                        f"Q26{str(bucket_start).zfill(4)} - "
                        f"Q26{str(bucket_end).zfill(4)}"
                    )
                else:
                    selected_bucket = "Obsolete"
                session['selected_bucket'] = selected_bucket

            obsolete = selected_bucket == 'Obsolete'
            show_all = selected_bucket == 'All'

            query_, suffix, year = build_project_query(
                user_ids_subq, selected_bucket, obsolete, show_all
            )
            use_quote_order = not obsolete

        else:
            # projType == 2 — testcase projects
            query_ = (
                db.session.query(projectMaster)
                .options(
                    load_only(*_PROJECT_LOAD_ONLY),
                    selectinload(projectMaster.region).load_only(regionMaster.name),
                    selectinload(projectMaster.industry).load_only(industryMaster.name),
                    selectinload(projectMaster.user).load_only(
                        userMaster.email, userMaster.fccUser
                    ),
                )
                .filter(
                    projectMaster.createdById.in_(user_ids_subq),
                    or_(
                        projectMaster.quoteNo.like('Q24TC%'),
                        projectMaster.quoteNo.like('Q25TC%'),
                        projectMaster.quoteNo.like('Q26TC%'),
                        projectMaster.quoteNo.like('T%'),
                    ),
                )
            )

    else:
        # Non-FCC / regular authenticated user — own projects only
        query_ = (
            db.session.query(projectMaster)
            .options(
                load_only(*_PROJECT_LOAD_ONLY),
                selectinload(projectMaster.region).load_only(regionMaster.name),
                selectinload(projectMaster.industry).load_only(industryMaster.name),
                selectinload(projectMaster.user).load_only(
                    userMaster.email, userMaster.fccUser
                ),
            )
            .filter(projectMaster.user == current_user)
        )

    # ── 2. Apply search ────────────────────────────────────────────────────
    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')
    if search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

    # ── 3. Add extra eager-load options needed by serialize_project ────────
    #   customer_name → project_address → address → company
    #   engineer_name → project_engineer → engineer
    query_ = query_.options(
        selectinload(projectMaster.project_address)
            .selectinload(addressProject.address)
            .selectinload(addressMaster.company)
            .load_only(companyMaster.name),
        selectinload(projectMaster.project_engineer)
            .selectinload(engineerProject.engineer)
            .load_only(engineerMaster.name),
    )

    # ── 4. Execute ─────────────────────────────────────────────────────────
    if use_quote_order:
        projects = query_.order_by(year.desc(), suffix.desc()).all()
    else:
        projects = query_.order_by(projectMaster.id.desc()).all()

    # ── 5. Serialize and return ────────────────────────────────────────────
    return jsonify({"projects": [serialize_project(p) for p in projects]})


# ---------------------------------------------------------------------------
# /load_testcase_projects — AJAX endpoint for testcase project table (FCC only)
# ---------------------------------------------------------------------------

@bp.route('/load_testcase_projects', methods=['GET'])
@login_required
def load_testcase_projects():
    """
    Return a JSON list of testcase projects for the dashboard project table.
    Only accessible by FCC users (projType == 2).

    Mirrors the projType==2 branch in /home exactly.
    Query params:
        search_type  — 'quote' | 'customer' | 'region' | 'engineer'
        search_value — raw search string
    """
    user = current_user

    if not user.fccUser:
        return jsonify({"projects": []})

    user_ids_subq = get_fcc_user_ids()

    query_ = (
        db.session.query(projectMaster)
        .options(
            load_only(*_PROJECT_LOAD_ONLY),
            selectinload(projectMaster.region).load_only(regionMaster.name),
            selectinload(projectMaster.industry).load_only(industryMaster.name),
            selectinload(projectMaster.user).load_only(
                userMaster.email, userMaster.fccUser
            ),
        )
        .filter(
            projectMaster.createdById.in_(user_ids_subq),
            or_(
                projectMaster.quoteNo.like('Q24TC%'),
                projectMaster.quoteNo.like('Q25TC%'),
                projectMaster.quoteNo.like('Q26TC%'),
                projectMaster.quoteNo.like('T%'),
            ),
        )
    )

    # Apply optional search
    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')
    if search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

    # Extra eager-load options needed by serialize_project
    query_ = query_.options(
        selectinload(projectMaster.project_address)
            .selectinload(addressProject.address)
            .selectinload(addressMaster.company)
            .load_only(companyMaster.name),
        selectinload(projectMaster.project_engineer)
            .selectinload(engineerProject.engineer)
            .load_only(engineerMaster.name),
    )

    projects = query_.order_by(projectMaster.id.desc()).all()
    return jsonify({"projects": [serialize_project(p) for p in projects]})


# ---------------------------------------------------------------------------
# Private helpers (used only by delete/create routes below)
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
# /get_project_revisions — AJAX: project revision list for export modal
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
# /get_item_revisions — AJAX: item revision list for copy modal
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
            "revision":      r.itemRevisionNo,
            "status":        r.status,
            "prepared_by":   r.prepared_by,
            "itemRevisionNo": r.itemRevisionNo,
        }
        for r in rows
    ])


# ---------------------------------------------------------------------------
# /get-item-revision — AJAX: full revision history for #revisionModal
# ---------------------------------------------------------------------------

@bp.route('/get-item-revision', methods=['POST'])
@login_required
def get_item_revision():
    item_id = request.form['itemNumber']
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
# /change-revision-status — changes cur_revno / creates draft copy
# ---------------------------------------------------------------------------

@bp.route('/change-revision-status', methods=['POST'])
@login_required
def change_revision_status():
    revision_type         = request.form['revisionType']
    item_no               = request.form['itemNumber']
    revision_no           = int(request.form['revisionNumber'])
    selected_revision_type = request.form['selectedRevisionType']
    item_element          = db.session.get(itemMaster, int(item_no))

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
        item_rev.status = 'In progress'
        item_rev.prepared_by = current_user.code
        item_element.draft_status = -1
        item_element.cur_revType = 'draft'
        item_element.initial_status = 1
        item_element.cur_status = 'In progress'
        db.session.commit()
        return jsonify([{'itemId': item_no}, {'projId': item_element.project.id}]), 200

    # ── Switch to an existing revision (view/existingdraft) ──
    if revision_type not in ('draft',):
        item_element.cur_revno = revision_no
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
    new_valve.revision = updated_revision
    db.session.commit()

    # cases
    for case in db.session.query(caseMaster).filter_by(item=item_element, revision=revision_no).order_by(caseMaster.id).all():
        new_case = caseMaster(item=item_element)
        db.session.add(new_case)
        _copy_attrs(case, new_case, {'id', 'revision'})
        new_case.revision = updated_revision
        new_case.draft_status = -1
        db.session.commit()

    # actuator
    old_act = db.session.query(actuatorMaster).filter_by(item=item_element, revision=revision_no).first()
    if old_act:
        new_act = actuatorMaster(item=item_element)
        db.session.add(new_act)
        _copy_attrs(old_act, new_act, {'id', 'revision', 'rotCase', 'actCase', 'volume_tank'})
        new_act.revision = updated_revision
        new_act.draft_status = -1
        db.session.commit()

        if old_act.actSelectionType == 'sliding':
            old_ac = db.session.query(actuatorCaseData).filter_by(actuator_=old_act, revision=revision_no).first()
            new_ac = actuatorCaseData(actuator_=new_act)
            db.session.add(new_ac)
            if old_ac:
                _copy_attrs(old_ac, new_ac, {'id', 'actuatorMasterId', 'actuator_', 'slidingActuatorId', 'slidingActuator', 'rotaryActuatorId', 'rotaryActuator', 'strokeCase_', 'revision'})
            new_ac.revision = updated_revision
            new_ac.draft_status = -1
            new_ac.actuator_ = new_act
            db.session.commit()

            old_sc = db.session.query(strokeCase).filter_by(actuatorCase_=old_ac, revision=revision_no).first()
            if old_sc:
                new_sc = strokeCase(actuatorCase_=new_ac)
                db.session.add(new_sc)
                _copy_attrs(old_sc, new_sc, {'id', 'revision', 'actuatorCase_', 'actuatorCaseId'})
                new_sc.revision = updated_revision
                new_sc.draft_status = -1
                new_sc.status = 1
                new_sc.actuatorCase_ = new_ac
                db.session.commit()

        elif old_act.actSelectionType == 'rotary':
            old_rc = db.session.query(rotaryCaseData).filter_by(actuator_=old_act, revision=revision_no).first()
            new_rc = rotaryCaseData(actuator_=new_act)
            db.session.add(new_rc)
            _copy_attrs(old_rc, new_rc, {'id', 'actuatorMasterId', 'actuator_', 'revision'})
            new_rc.revision = updated_revision
            new_rc.draft_status = -1
            new_rc.actuator_ = new_act
            db.session.commit()

        old_vt = db.session.query(volumeTank).filter_by(actuator_=old_act, revision=revision_no).first()
        if old_vt:
            new_vt = volumeTank(actuator_=new_act)
            db.session.add(new_vt)
            _copy_attrs(old_vt, new_vt, {'id', 'revision', 'actuatorMasterId', 'actuator_'})
            new_vt.revision = updated_revision
            new_vt.draft_status = -1
            db.session.commit()

    # order notes
    for note in db.session.query(itemNotesData).filter_by(item=item_element, revision=revision_no).all():
        new_note = itemNotesData(item=item_element)
        db.session.add(new_note)
        _copy_attrs(note, new_note, {'id', 'itemId', 'revision'})
        new_note.revision = updated_revision
        new_note.draft_status = -1
        db.session.commit()

    # accessories
    old_acc = db.session.query(accessoriesData).filter_by(item=item_element, revision=revision_no).first()
    if old_acc:
        new_acc = accessoriesData(item=item_element)
        db.session.add(new_acc)
        _copy_attrs(old_acc, new_acc, {'id', 'revision'})
        new_acc.revision = updated_revision
        new_acc.draft_status = -1
        db.session.commit()

    return jsonify([{'itemId': item_no}, {'projId': item_element.project.id}]), 200


# ---------------------------------------------------------------------------
# /check-project-draftst — check which items still have unsaved drafts
# ---------------------------------------------------------------------------

@bp.route('/check-project-draftst', methods=['POST'])
@login_required
def check_project_draftst():
    proj_id = request.form['projectId']
    project = db.session.get(projectMaster, int(proj_id))
    items = (
        db.session.query(itemMaster)
        .filter_by(project=project)
        .order_by(itemMaster.itemNumber.asc())
        .all()
    )
    unsaved_ids = [i.id for i in items if i.draft_status == -1]
    if unsaved_ids:
        return jsonify({'item_ids': unsaved_ids, 'success': 'no'})
    return jsonify({'success': 'yes'})


# ---------------------------------------------------------------------------
# /project-submit — mark all draft items in a project as Completed
# ---------------------------------------------------------------------------

@bp.route('/project-submit', methods=['POST'])
@login_required
def project_submit():
    proj_id = request.form['projectId']
    project = db.session.get(projectMaster, int(proj_id))
    last_rev = project.revision

    items = (
        db.session.query(itemMaster)
        .filter_by(project=project)
        .order_by(itemMaster.itemNumber.asc())
        .all()
    )

    has_submittable = any(i.draft_status in (0, -1) for i in items)
    if not has_submittable:
        return "all completed"

    for item_ in items:
        if item_.draft_status != 0:
            continue
        cur_rev = item_.revision

        proj_rev_row = projectRevisionTable(
            project=project, projectRevision=last_rev,
            item=item_, itemRevision=cur_rev,
            prepared_by=current_user.code,
            time=datetime.today().strftime("%Y-%m-%d %H:%M"),
        )
        db.session.add(proj_rev_row)
        db.session.commit()

        item_rev = db.session.query(itemRevisionTable).filter_by(item=item_, itemRevisionNo=cur_rev).first()
        if item_rev:
            item_rev.status = "Completed"
            item_rev.time = datetime.today().strftime("%Y-%m-%d %H:%M")
            db.session.commit()

        valve = valveDetailsMaster.getValveElement(item_, cur_rev)
        if valve:
            valve.draft_status = 1
            db.session.commit()

        for case in db.session.query(caseMaster).filter_by(item=item_, revision=cur_rev).all():
            case.draft_status = 1
        db.session.commit()

        act = db.session.query(actuatorMaster).filter_by(item=item_, revision=cur_rev).first()
        if act:
            act.draft_status = 1
            db.session.commit()
            if act.actSelectionType == 'sliding':
                ac = db.session.query(actuatorCaseData).filter_by(actuator_=act, revision=cur_rev).first()
                if ac:
                    ac.draft_status = 1
                    db.session.commit()
                sc = db.session.query(strokeCase).filter_by(actuatorCase_=ac, revision=cur_rev).first()
                if sc:
                    sc.draft_status = 1
                    db.session.commit()
            elif act.actSelectionType == 'rotary':
                rc = db.session.query(rotaryCaseData).filter_by(actuator_=act, revision=cur_rev).first()
                if rc:
                    rc.draft_status = 1
                    db.session.commit()

        vt = db.session.query(volumeTank).filter_by(actuator_=act, revision=cur_rev).first() if act else None
        if vt:
            vt.draft_status = 1
            db.session.commit()

        acc = db.session.query(accessoriesData).filter_by(item=item_, revision=cur_rev).first()
        if acc:
            acc.draft_status = 1
            db.session.commit()

        for note in db.session.query(itemNotesData).filter_by(item=item_, revision=cur_rev).all():
            note.draft_status = 1
        db.session.commit()

        item_.cur_revType = 'view'
        item_.draft_status = 1
        item_.cur_status = 'Completed'

    project.revision = last_rev + 1
    db.session.commit()
    return "success"


# ---------------------------------------------------------------------------
# /delete-draft — remove a draft revision and all its related records
# ---------------------------------------------------------------------------

@bp.route('/delete-draft', methods=['POST'])
@login_required
def delete_draft():
    item_id           = request.form['itemId']
    item_rev_no       = request.form['itemRevNo']
    item_element      = db.session.get(itemMaster, int(item_id))

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
    item_element.cur_status  = last_rev.status
    item_element.revision    = last_rev.itemRevisionNo
    item_element.draft_status = 0
    db.session.commit()
    return "success"


# ---------------------------------------------------------------------------
# /item-delete — delete an item (adds blank if last item in project)
# ---------------------------------------------------------------------------

@bp.route('/item-delete', methods=['POST'])
@login_required
def item_delete():
    item_id          = request.form['item_id']
    reason           = request.form['reasonfordelete']
    item_            = db.session.get(itemMaster, int(item_id))
    project_id       = item_.project.id

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
            valve_data = db.session.query(valveDetailsMaster).filter_by(item=item_).first()
            rev.tagno = valve_data.tagNumber if valve_data else None
        db.session.commit()
        db.session.delete(item_)
        db.session.commit()
        flash("Item deleted successfully", "success")
        remaining = db.session.query(itemMaster).filter_by(
            project=db.session.get(projectMaster, project_id)
        ).all()
        return_item_id = remaining[0].id if remaining else None

    # Return updated item list for the project
    proj = db.session.get(projectMaster, project_id)
    items_after = db.session.query(itemMaster).filter_by(project=proj).all()
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
    import json
    return json.dumps(data_list)


# ---------------------------------------------------------------------------
# /project-delete — delete a project (adds blank if last project for user)
# ---------------------------------------------------------------------------

@bp.route('/project-delete', methods=['POST'])
@login_required
def project_delete():
    project_id = request.form['projectId']
    project_   = db.session.get(projectMaster, int(project_id))
    creator    = db.session.get(userMaster, project_.createdById)

    if current_user.id != project_.createdById:
        return {'error-message': f"Only the project creator '{creator.name}' can delete the project"}

    all_projects = db.session.query(projectMaster).filter_by(user=current_user).all()

    if len(all_projects) == 1:
        _, new_item = _new_user_project_item(current_user)
        flash("Blank Project Added, and project deleted successfully", "success")
        db.session.delete(project_)
        db.session.commit()
        return {'proj': new_item.project.id, 'item': new_item.id}

    db.session.delete(project_)
    db.session.commit()
    flash("Project deleted successfully", "success")

    remaining = db.session.query(projectMaster).filter_by(user=current_user).all()
    last_proj  = remaining[-1]
    last_item  = db.session.query(itemMaster).filter_by(project=last_proj).first()

    # Update session bucket to match the new last project
    last_fcc_proj = getLatestFccLiveProject('last')
    if last_fcc_proj:
        project_num  = int(last_fcc_proj[1:])
        num_suffix   = project_num % 1000
        bucket_start = (num_suffix // 100) * 100
        prefix       = last_fcc_proj[:3]
        session['selected_bucket'] = (
            f"{prefix}{str(bucket_start).zfill(5)} - {prefix}{str(bucket_start + 99).zfill(5)}"
        )

    return {'proj': last_proj.id, 'item': last_item.id}

@bp.route('/submit-project-type', methods=['GET'])
def submitProjectType():
    proj_type = request.args.get('proj_type')
    user = current_user
    if user.fccUser:
        user.projType = int(proj_type)
        db.session.commit()
    return jsonify({"status":"success"})


# ---------------------------------------------------------------------------
# /add-project — Create a new project
# ---------------------------------------------------------------------------

from app.blueprints.project.helpers import (  # noqa: E402
    add_project_metadata,
    add_project_rels,
    generate_quote,
    get_item_for_add_project,
)


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


@bp.route('/add-project/', methods=['GET', 'POST'])
# @bp.route('/add-project/proj-<proj_id>/item-<item_id>', methods=['GET', 'POST'])
@login_required
def add_project():
    """
    GET  — Render the add-project form.
    POST — Validate, create projectMaster + first item, redirect to dashboard.

    Business logic unchanged from addProject() in app.py.
    Metadata is a targeted subset (replaces full metadata() call).
    Item is loaded with load_only — no relationship lazy-loads in the template.
    """
    metadata_ = add_project_metadata()
    # if item_id:
    #     item  = get_item_for_add_project(item_id)
    # else:
    #     item  = None

    if request.method == 'POST':
        user = current_user
        a    = request.form.to_dict(flat=False)

        # ── 1. Determine quote number and project type ────────────────────
        if user.fccUser and user.projType == 1:
            fccproject = True
            quote_no   = a['quoteNo'][0].strip()
            if not re.fullmatch(r"Q\d{7}", quote_no):
                flash("Quote format should be 'Q' followed by 7 digit Number", 'failure')
                return render_template(
                    'home/project_details.html',
                    metadata=metadata_, user=user, #item=item, proj_id=proj_id,
                )

        elif user.fccUser and user.projType == 2:
            fccproject = None
            quote_no   = generate_quote("T")

        else:
            fccproject = False
            quote_no   = generate_quote("C")

        proj_id = str(quote_no)

        # ── 2. Create projectMaster ───────────────────────────────────────
        new_project = projectMaster(
            quoteNo              = proj_id,
            isFccProject         = fccproject,
            isObsolete           = False,
            projectRef           = a['projectRef'][0],
            enquiryRef           = a['enquiryRef'][0],
            enquiryReceivedDate  = datetime.strptime(a['enquiryReceivedDate'][0], '%Y-%m-%d'),
            receiptDate          = datetime.strptime(a['receiptDate'][0], '%Y-%m-%d'),
            bidDueDate           = datetime.strptime(a['bidDueDate'][0], '%Y-%m-%d'),
            purpose              = a['purpose'][0],
            custPoNo             = a['custPoNo'][0],
            workOderNo           = a['workOderNo'][0],
            status               = a['status'][0],
            user                 = current_user,
            industry             = db.session.get(industryMaster, int(a['industry'][0]))
                                    if a['industry'][0] != 'OEM'
                                    else None,
            region               = db.session.get(regionMaster, int(a['region'][0])),
            revision             = 0,
            cur_revno            = 0,
            # Preferences
            pressure_unit        = a['pressureUnit'][0],
            l_flowrate_type      = a['LiquidflowrateType'][0],
            l_flowrate_unit      = a['LiquidflowrateUnit'][0],
            g_flowrate_type      = a['GasflowrateType'][0],
            g_flowrate_unit      = a['GasflowrateUnit'][0],
            viscosity_type       = a['viscosity_'][0],
            viscosity_unit       = a['vis_units'][0],
            length_unit          = a['lengthUnit'][0],
            temperature_unit     = a['temperatureUnit'][0],
            trim_exit_velocity   = a['tev'][0],
            noise_limit          = a['noise_limit'][0],
        )

        try:
            db.session.add(new_project)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if 'unique' in str(e.orig).lower() or 'duplicate' in str(e.orig).lower():
                flash("Quote Number already exists!", 'failure')
            else:
                flash("Database error occurred. Please try again.", 'failure')
            return render_template(
                'home/project_details.html',
                metadata=metadata_, user=user#, item=item, proj_id=proj_id,
            )
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", 'failure')
            return render_template(
                'home/project_details.html',
                metadata=metadata_, user=user#, item=item, proj_id=proj_id,
            )

        # ── 3. Create first item ──────────────────────────────────────────
        add_item = _add_new_item(new_project, 1, 'A')

        # ── 4. Link company / engineer relationships ──────────────────────
        project_element = db.session.query(projectMaster).filter_by(quoteNo=proj_id).first()
        eng_element     = db.session.query(engineerMaster).filter_by(name=a['aEng'][0]).first()
        add_project_rels(
            cname     = a['cname'][0],
            cnameE    = a['cnameE'][0],
            address   = a['address'][0],
            addressE  = a['addressE'][0],
            aEng      = eng_element.id,
            cEng      = a['cEng'][0],
            project   = project_element,
            operation = 'create',
        )

        flash('Project Added Successfully', 'success')

        # ── 5. Update session bucket to new project's range ──────────────
        last_project = new_project.quoteNo
        if last_project:
            prefix       = last_project[:3]          # e.g. "Q26"
            last_num     = int(last_project[3:])     # e.g. 123
            bucket_start = (last_num // 100) * 100   # e.g. 100
            bucket_end   = bucket_start + 99         # e.g. 199
            session['selected_bucket'] = (
                f"{prefix}{str(bucket_start).zfill(4)} - {prefix}{str(bucket_end).zfill(4)}"
            )

        return redirect(url_for('home.home', proj_id=add_item.projectID, item_id=add_item.id))

    # ── GET ───────────────────────────────────────────────────────────────
    return render_template(
        'home/project_details.html',
        metadata=metadata_, user=current_user#, item=item, proj_id=proj_id,
    )