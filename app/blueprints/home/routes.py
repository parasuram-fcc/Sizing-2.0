"""
routes.py — Home blueprint routes.

Routes:
  GET /home
  GET /home/proj-<proj_id>/item-<item_id>
  GET /load_projects
  GET /load_testcase_projects
"""

from flask import render_template, request, session, flash, jsonify
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
    use_quote_order = False
    suffix = year = None

    # =========================================================
    # 1. BUILD PROJECT QUERY
    # =========================================================
    if user.fccUser:
        user_ids_subq = get_fcc_user_ids()
        last_Q26 = get_last_Q26()
        last_Q25 = get_last_Q25()

        if not user.projType:
            user.projType = 1

        if user.projType == 1:
            getLatestFccLiveProject('last')

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
            use_quote_order = not obsolete

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
    search_type  = request.args.get('search_type')
    search_value = request.args.get('search_value')
    row_type     = request.args.get('type')

    if row_type == 'project' and search_type and search_value:
        query_ = apply_project_search(query_, search_type, search_value)

    if use_quote_order:
        all_projects = query_.order_by(year.desc(), suffix.desc()).all()
    else:
        all_projects = query_.order_by(projectMaster.id.desc()).all()

    if not all_projects:
        flash('No projects to display', 'failure')

    # =========================================================
    # 3. RESOLVE SELECTED PROJECT
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
    # 4. ITEMS
    # =========================================================
    project_id_for_items = (
        selected_project.id if selected_project
        else (int(proj_id) if proj_id else None)
    )

    items_list    = []
    item_element  = None

    if project_id_for_items:
        item_query = build_item_query(
            project_id_for_items,
            search_type if row_type == 'item' else None,
            search_value if row_type == 'item' else None,
        )
        items_list   = item_query.order_by(itemMaster.itemNumber.asc()).all()
        item_element = items_list[0] if items_list else None

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
    proj_ref = selected_project.projectRef if selected_project else ''

    return render_template(
        'home/dashboard.html',
        random_data=random_data,
        user=current_user,
        selected_bucket=selected_bucket,
        projects=all_projects,
        item=item_element,
        f_projId=all_projects[0].id if all_projects else None,
        f_itemId=items_list[0].id if items_list else None,
        items_len=len(items_list),
        page='home',
        proj_rev=proj_rev,
        item_rev=item_rev,
        all_buckets=all_buckets,
        proj_ref=proj_ref,
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
            last_Q26 = get_last_Q26()
            last_Q25 = get_last_Q25()

            quote_range = request.args.get('quote_range')
            if quote_range:
                session['selected_bucket'] = quote_range
                selected_bucket = quote_range
            elif session.get('selected_bucket'):
                selected_bucket = session['selected_bucket']
            else:
                if last_Q26:
                    last_num     = int(last_Q26[3:])
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