"""
routes.py — Home blueprint routes.

Routes:
  GET /home
  GET /home/proj-<proj_id>/item-<item_id>
  GET /load_projects
  GET /load_testcase_projects
"""

from flask import render_template, request, session, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import selectinload, load_only

from app.blueprints.home import bp
from app.extensions import db
from app.models.master import (
    industryMaster,
    regionMaster,
    addressMaster,
    companyMaster,
    engineerMaster,
)
from app.models.transactional import (
    itemMaster,
    projectMaster,
    userMaster,
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
from config import Config
from datetime import datetime


# ---------------------------------------------------------------------------
# /home — Dashboard
# ---------------------------------------------------------------------------

@bp.route('/home', defaults={'proj_id': None, 'item_id': None})
@bp.route('/home/proj-<int:proj_id>/item-<int:item_id>', methods=['GET'])
@login_required
def home(proj_id, item_id):
    """
    Main dashboard route.

    Resolves the bucket list for FCC users (projType == 1) and renders the
    dashboard shell. Project rows and item rows are populated client-side via
    /load_projects and /project/get_items_only AJAX calls, so no heavy
    project/item/revision queries are fired here.
    """
    user = current_user
    selected_bucket = None
    all_buckets = []

    # =========================================================
    # 1. BUCKET LIST — FCC projType==1 only
    # =========================================================
    if user.fccUser:
        if not user.projType:
            user.projType = 1

        if user.projType == 1:
            last_project = getLatestFccLiveProject('last')
            selected_bucket = resolve_project_bucket(request, session, last_project)
            from_year = datetime.today().year - int(Config.QOUTE_RANGE)
            all_buckets = make_project_groups(last_project, f'Q{str(from_year)}00000', 100)[::-1]
            all_buckets += ["All", "Obsolete"]

    # =========================================================
    # 2. RANDOM DATA FLAG
    # =========================================================
    random_data = 'no' if proj_id else 'yes'
    if request.args.get('reload_source') == 'project_dropdown':
        random_data = 'yes'

    # =========================================================
    # 3. AJAX DISPATCH — items only (projects go via /load_projects)
    # =========================================================
    row_type     = request.args.get('type')
    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if row_type == 'item' and proj_id:
            items = get_items_for_project(proj_id, search_type, search_value)
            if items:
                return jsonify({"items": [serialize_item(i) for i in items]})
        return jsonify({"output": "no data"})

    # =========================================================
    # 4. PROJ_REF — single-column query only when a project is selected
    #    (JS re-fetches the full project/item lists via /load_projects
    #     and /project/get_items_only, so we don't load them here)
    # =========================================================
    if proj_id:
        proj_ref = (
            db.session.query(projectMaster.projectRef)
            .filter_by(id=proj_id)
            .scalar() or ''
        )
    else:
        proj_ref = ''

    # =========================================================
    # 5. FULL PAGE RENDER
    # =========================================================
    return render_template(
        'home/dashboard.html',
        random_data=random_data,
        user=current_user,
        selected_bucket=selected_bucket,
        all_buckets=all_buckets,
        proj_ref=proj_ref,
        page='home',
    )


# ---------------------------------------------------------------------------
# /load_projects — AJAX endpoint for dynamic project table
# ---------------------------------------------------------------------------

@bp.route('/load_projects', methods=['GET'])
@login_required
def load_projects():
    user = current_user
    use_quote_order = False
    suffix = year = None

    if user.fccUser:
        user_ids_subq = get_fcc_user_ids()

        if not user.projType:
            user.projType = 1

        if user.projType == 1:
            # last_Q26 = get_last_Q26()
            # last_Q25 = get_last_Q25()

            quote_range = request.args.get('quote_range')
            if quote_range:
                session['selected_bucket'] = quote_range
                selected_bucket = quote_range
            elif session.get('selected_bucket'):
                selected_bucket = session['selected_bucket']
            else:
                latest_proj = getLatestFccLiveProject()
                if latest_proj:
                    last_num     = int(latest_proj[3:])
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

    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')
    if search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

    query_ = query_.options(
        selectinload(projectMaster.project_address)
            .selectinload(addressProject.address)
            .selectinload(addressMaster.company)
            .load_only(companyMaster.name),
        selectinload(projectMaster.project_engineer)
            .selectinload(engineerProject.engineer)
            .load_only(engineerMaster.name),
    )

    if use_quote_order:
        projects = query_.order_by(year.desc(), suffix.desc()).all()
    else:
        projects = query_.order_by(projectMaster.id.desc()).all()

    return jsonify({"projects": [serialize_project(p) for p in projects]})


# ---------------------------------------------------------------------------
# /load_testcase_projects — AJAX endpoint for testcase project table (FCC only)
# ---------------------------------------------------------------------------

@bp.route('/load_testcase_projects', methods=['GET'])
@login_required
def load_testcase_projects():
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

    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')
    if search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

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