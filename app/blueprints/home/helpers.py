"""
helpers.py — Home blueprint helper functions.

All database access lives here so that routes.py stays thin.
Each function has a single responsibility and typed parameters.
"""

from __future__ import annotations

import time

from sqlalchemy import Integer, cast, func, distinct
from sqlalchemy.orm import joinedload, selectinload, load_only, contains_eager

from app.extensions import db
from app.models.master import (
    industryMaster,
    regionMaster,
    addressMaster,
    engineerMaster,
    companyMaster,
)
from app.models.transactional import (
    projectMaster,
    itemMaster,
    userMaster,
    projectRevisionTable,
    itemRevisionTable,
    valveDetailsMaster,
    caseMaster,
    addressProject,
    engineerProject,
)


# ---------------------------------------------------------------------------
# Internal SQL expression builders
# ---------------------------------------------------------------------------

def _quote_suffix(col=projectMaster.quoteNo):
    """Rightmost 5 digits of quoteNo cast to Integer (e.g. 00123)."""
    return func.right(col, 5).cast(Integer)


def _quote_year(col=projectMaster.quoteNo):
    """2-digit year embedded in quoteNo cast to Integer (position 2, length 2)."""
    return func.substr(col, 2, 2).cast(Integer)


# ---------------------------------------------------------------------------
# Task 1a — FCC user ID subquery
# ---------------------------------------------------------------------------

def get_fcc_user_ids():
    """
    Return a subquery of userMaster.id for all FCC users.

    Using a subquery instead of a Python list avoids loading IDs into
    memory and lets the DB engine handle the IN-filter natively.

    Returns:
        sqlalchemy.sql.selectable.Subquery
    """
    return db.session.query(userMaster.id).filter_by(fccUser=True).subquery()


# ---------------------------------------------------------------------------
# Task 1b — Core project list query (FCC projType == 1 live projects)
# ---------------------------------------------------------------------------

_PROJECT_LOAD_ONLY = [
    projectMaster.id,
    projectMaster.projectId,
    projectMaster.quoteNo,
    projectMaster.enquiryRef,
    projectMaster.receiptDate,
    projectMaster.bidDueDate,
    projectMaster.status,
    projectMaster.workOderNo,
    projectMaster.createdById,
    projectMaster.projectRef,
]


def build_project_query(
    user_ids_subq,
    selected_bucket: str | None,
    obsolete: bool,
    show_all: bool,
):
    """
    Build the SQLAlchemy Query for FCC live projects (projType == 1).

    Defines suffix/year SQL expressions ONCE and returns them alongside
    the query so order_by in the route can reuse the same expressions.

    Args:
        user_ids_subq:   Subquery from get_fcc_user_ids().
        selected_bucket: Bucket string like 'Q26000 - Q26099', 'All', or 'Obsolete'.
        obsolete:        True when selected_bucket == 'Obsolete'.
        show_all:        True when selected_bucket == 'All'.

    Returns:
        tuple[Query, suffix_expr, year_expr]
    """
    suffix = _quote_suffix()
    year = _quote_year()

    base_options = [
        load_only(*_PROJECT_LOAD_ONLY),
        selectinload(projectMaster.region).load_only(regionMaster.name),
        selectinload(projectMaster.industry).load_only(industryMaster.name),
        selectinload(projectMaster.user).load_only(userMaster.email, userMaster.fccUser),
    ]

    base_filter = [
        projectMaster.createdById.in_(user_ids_subq),
        projectMaster.projectRef != 'TESTCASES',
    ]

    if show_all:
        query = (
            db.session.query(projectMaster)
            .options(*base_options)
            .filter(
                *base_filter,
                # .op('~') is PostgreSQL-only; .regexp_match() is dialect-agnostic
                # projectMaster.quoteNo.regexp_match('^Q[0-9]{7}$'),
                projectMaster.quoteNo.op('~')('^Q[0-9]{7}$'),
            )
        )

    elif obsolete:
        query = (
            db.session.query(projectMaster)
            .options(*base_options)
            .filter(
                *base_filter,
                (projectMaster.quoteNo.is_(None) | (projectMaster.quoteNo == '')),
            )
        )

    else:
        # Bucket range: parse 'Q26000 - Q26099' → low/high year+num
        parts = [p.strip() for p in selected_bucket.split('-', 1)]
        if len(parts) != 2:
            raise ValueError(f"Invalid bucket format: {selected_bucket!r}")
        low_id, high_id = parts[0].strip(), parts[1].strip()

        low_year = int(low_id[1:3])
        low_num = int(low_id[3:])
        high_year = int(high_id[1:3])
        high_num = int(high_id[3:])

        query = (
            db.session.query(projectMaster)
            .options(*base_options)
            .filter(
                *base_filter,
                # .op('~') is PostgreSQL-only; .regexp_match() is dialect-agnostic
                # projectMaster.quoteNo.regexp_match('^Q[0-9]{7}$'),
                projectMaster.quoteNo.op('~')('^Q[0-9]{7}$'),
                year.between(low_year, high_year),
                suffix.between(low_num, high_num),
            )
        )

    return query, suffix, year


# ---------------------------------------------------------------------------
# Task 1c — Search filter application
# ---------------------------------------------------------------------------

def apply_project_search(query, search_type: str | None, search_value: str | None):
    """
    Apply project-level search filters to an existing Query.

    Keeps all join/filter branching in one place.
    No new joins are added unless the search_type requires it.
    All string comparisons use ilike() for case-insensitive matching.

    Args:
        query:        Existing projectMaster Query.
        search_type:  One of 'quote', 'engineer', 'region', 'customer'.
        search_value: Raw value from the request.

    Returns:
        Query (may be the original if search_type is None/unsupported).
    """
    if not search_type or not search_value:
        return query

    sv = f"%{search_value}%"

    if search_type == 'quote':
        query = query.filter(projectMaster.quoteNo.ilike(sv))

    elif search_type == 'engineer':
        query = (
            query
            .join(projectMaster.project_engineer)
            .join(engineerProject.engineer)
            .filter(
                engineerMaster.name.ilike(f"{search_value}%"),
                engineerProject.isApplication == False,  # noqa: E712
            )
        )

    elif search_type == 'region':
        query = (
            query
            .join(projectMaster.region)
            .filter(regionMaster.name.ilike(sv))
        )

    elif search_type == 'customer':
        query = (
            query
            .join(projectMaster.project_address)
            .join(addressProject.address)
            .join(addressMaster.company)
            .filter(
                addressProject.isCompany.is_(True),
                companyMaster.name.ilike(f"{search_value}%"),
            )
        )

    return query


# ---------------------------------------------------------------------------
# Task 1d — Item list query (for route context — minimal columns)
# ---------------------------------------------------------------------------

def build_item_query(project_id: int, search_type: str | None, search_value: str | None):  # unused
    """
    Build the item Query for a given project with minimal column loading.

    Uses joinedload (not outerjoin+joinedload) to avoid duplicate joins.
    When search_type == 'tagNo', uses join() + contains_eager() so the
    filter applies correctly and the join is not duplicated.

    Args:
        project_id:   PK of the project.
        search_type:  Optional search type ('tagNo' supported here).
        search_value: Raw search value.

    Returns:
        sqlalchemy.orm.Query  (call .all() after all filters are chained)
    """
    if search_type == 'tagNo' and search_value:
        # For tagNo filter we need an explicit join so the WHERE clause lands
        # on the join, not as a post-filter. Use contains_eager so SA knows
        # the relationship is already loaded.
        query = (
            db.session.query(itemMaster)
            .join(itemMaster.valve)
            .options(
                contains_eager(itemMaster.valve).load_only(
                    valveDetailsMaster.valveModelNo,
                    valveDetailsMaster.tagNumber,
                ),
                joinedload(itemMaster.case).load_only(
                    caseMaster.valveSize,
                    caseMaster.revision,
                ),
                load_only(itemMaster.itemNumber, itemMaster.cur_revno),
            )
            .filter(
                itemMaster.projectID == project_id,
                valveDetailsMaster.tagNumber.ilike(f"{search_value}%"),
            )
        )
    else:
        query = (
            db.session.query(itemMaster)
            .options(
                joinedload(itemMaster.valve).load_only(
                    valveDetailsMaster.valveModelNo,
                    valveDetailsMaster.tagNumber,
                ),
                joinedload(itemMaster.case).load_only(
                    caseMaster.valveSize,
                    caseMaster.revision,
                ),
                load_only(itemMaster.itemNumber, itemMaster.cur_revno),
            )
            .filter(itemMaster.projectID == project_id)
        )

    return query


# ---------------------------------------------------------------------------
# Task 1e — Revision loader
# ---------------------------------------------------------------------------

def load_revisions(proj_id: int, item_id: int):  # unused
    """
    Load project and item revisions in one function.

    Uses with_entities() to select only the columns the template needs.
    distinct() is kept because (projectId, projectRevision) has no unique
    constraint — duplicate rows are possible.

    Args:
        proj_id:  Project PK.
        item_id:  Item PK.

    Returns:
        tuple[list, list]  — (proj_rev rows, item_rev rows)
    """
    proj_rev = (
        db.session.query(
            distinct(projectRevisionTable.projectRevision),
            projectRevisionTable.projectRevision,
            projectRevisionTable.prepared_by,
        )
        .filter_by(projectId=proj_id)
        .all()
    )

    item_rev = (
        db.session.query(
            distinct(itemRevisionTable.itemRevisionNo),
            itemRevisionTable.itemRevisionNo,
            itemRevisionTable.status,
            itemRevisionTable.prepared_by,
        )
        .filter_by(itemId=item_id)
        .all()
    )

    return proj_rev, item_rev


# ---------------------------------------------------------------------------
# Task 1f — Selected project resolver
# ---------------------------------------------------------------------------

def resolve_selected_project(proj_id, all_projects: list):  # unused
    """
    Return the projectMaster object matching proj_id from all_projects.

    Uses O(1) dict lookup instead of O(n) next() scan.

    Args:
        proj_id:      String or int project PK from URL (may be None).
        all_projects: List returned by the project query.

    Returns:
        projectMaster | None
    """
    if not proj_id:
        return None
    project_map = {p.id: p for p in all_projects}
    return project_map.get(int(proj_id))


# ---------------------------------------------------------------------------
# Task 1g — Item display list builder (single-pass)
# ---------------------------------------------------------------------------

def build_item_display_lists(items_list: list):
    """
    Build valve_list, model_list, valve_size_list in a single pass.

    Each list is parallel-indexed to items_list.
    Does not use items_list.index() — O(1) per element.

    Args:
        items_list: List of itemMaster ORM objects (with valve/case loaded).

    Returns:
        tuple[list, list, list]  — (valve_list, model_list, valve_size_list)
    """
    valve_list = []
    model_list = []
    valve_size_list = []

    for item in items_list:
        valve = item.valve[0] if item.valve else None
        if valve:
            case = next(
                (c for c in item.case if c.revision == item.cur_revno),
                None,
            )
            valve_list.append(valve)
            model_list.append(valve.valveModelNo)
            valve_size_list.append(case.valveSize if case else None)
        else:
            valve_list.append(None)
            model_list.append(None)
            valve_size_list.append(None)

    return valve_list, model_list, valve_size_list


# ---------------------------------------------------------------------------
# Task 4d — Item serializer + get_items_only query
# ---------------------------------------------------------------------------

def serialize_item(item: itemMaster) -> dict:
    """
    Convert a single itemMaster ORM object (with valve/case pre-loaded)
    to the JSON dict consumed by the JS updateItemsList() function.

    All keys must exactly match what the JS expects — do not add or remove.
    """
    valve = item.valve[0] if item.valve else None
    case = None
    if valve and item.case:
        case = next((c for c in item.case if c.revision == item.cur_revno), None)

    return {
        "itemId":      item.id,
        "itemNo":      item.itemNumber,
        "itemalt":     item.alternate,
        "tagNo":       valve.tagNumber if valve and valve.tagNumber is not None else 'N/A',
        "series":      valve.valveSeries if valve and valve.valveSeries is not None else 'N/A',
        "sizes":       case.valveSize if case and case.valveSize is not None else 'N/A',
        "models":      valve.valveModelNo if valve and valve.valveModelNo is not None else 'N/A',
        "type":        valve.style.name if valve and valve.style else 'N/A',
        "rating":      valve.rating.name if valve and valve.rating else 'N/A',
        "material":    valve.material.name if valve and valve.material else 'N/A',
        "unit":        "N/A",
        "qty":         valve.quantity if valve and valve.quantity is not None else 'N/A',
        "totalprice":  "N/A",
        "cur_status":  item.cur_status,
        "revision":    item.revision,
        "draft_status": item.draft_status,
        "print":       "",
    }


def serialize_project(project) -> dict:
    """
    Convert a projectMaster ORM object (with project_address, project_engineer,
    region, and industry pre-loaded) to the JSON dict consumed by
    updateProjectsList() in dashboard.js.

    All keys must exactly match what the JS expects.
    """
    has_engineer = bool(project.project_engineer)
    return {
        "id":           project.id,
        "quoteNo":      "TBA" if project.quoteNo is None else project.quoteNo,
        "customerName": project.customer_name or "N/A",
        "enquiryRef":   project.enquiryRef or "",
        "receiptDate":  str(project.receiptDate.date()) if has_engineer and project.receiptDate else "N/A",
        "dueDate":      str(project.bidDueDate.date()) if has_engineer and project.bidDueDate else "N/A",
        "region":       project.region.name if has_engineer and project.region else "N/A",
        "industry":     project.industry.name if has_engineer and project.industry else "N/A",
        "engineerName": project.engineer_name or "N/A",
        "status":       project.status or "",
        "workOrderNo":  project.workOderNo or "",
        "projectRef":   project.projectRef or "",
    }


def get_items_for_project(project_id: int, search_type: str | None = None,
                          search_value: str | None = None) -> list:
    """
    Query itemMaster with ALL columns needed for serialization.

    Always runs its own query so serialize_item() never triggers lazy loads.
    Used by both the AJAX route and the get_items_only endpoint.

    Args:
        project_id:   Project PK (int).
        search_type:  Optional 'tagNo' to narrow results.
        search_value: Raw search string.

    Returns:
        list[itemMaster]
    """
    if search_type == 'tagNo' and search_value:
        query = (
            db.session.query(itemMaster)
            .join(itemMaster.valve)
            .options(
                contains_eager(itemMaster.valve)
                .joinedload(valveDetailsMaster.style),
                contains_eager(itemMaster.valve)
                .joinedload(valveDetailsMaster.rating),
                contains_eager(itemMaster.valve)
                .joinedload(valveDetailsMaster.material),
                joinedload(itemMaster.case).load_only(
                    caseMaster.valveSize,
                    caseMaster.revision,
                ),
                load_only(
                    itemMaster.itemNumber,
                    itemMaster.alternate,
                    itemMaster.cur_revno,
                    itemMaster.cur_status,
                    itemMaster.revision,
                    itemMaster.draft_status,
                ),
            )
            .filter(
                itemMaster.projectID == project_id,
                valveDetailsMaster.tagNumber.ilike(f"{search_value}%"),
            )
        )
    else:
        query = (
            db.session.query(itemMaster)
            .options(
                joinedload(itemMaster.valve)
                .joinedload(valveDetailsMaster.style),
                joinedload(itemMaster.valve)
                .joinedload(valveDetailsMaster.rating),
                joinedload(itemMaster.valve)
                .joinedload(valveDetailsMaster.material),
                joinedload(itemMaster.case).load_only(
                    caseMaster.valveSize,
                    caseMaster.revision,
                ),
                load_only(
                    itemMaster.itemNumber,
                    itemMaster.alternate,
                    itemMaster.cur_revno,
                    itemMaster.cur_status,
                    itemMaster.revision,
                    itemMaster.draft_status,
                ),
            )
            .filter(itemMaster.projectID == project_id)
        )

    return query.order_by(itemMaster.itemNumber.asc()).all()


# ---------------------------------------------------------------------------
# Bucket helpers (kept from original, no logic change)
# ---------------------------------------------------------------------------

def make_project_groups(last_id: str, first_id: str, bucket_size: int = 100) -> list[str]:
    """
    Generate fixed-size bucket label strings like 'Q26000 - Q26099'.

    No logic change from original — preserved exactly.
    """
    if not (last_id and first_id):
        return []

    prefix = last_id[0]
    first_year = int(first_id[1:3])
    last_year = int(last_id[1:3])

    num_width = 5
    first_num = int(first_id[3:].zfill(num_width))
    last_num = int(last_id[3:].zfill(num_width))
    max_num = 10 ** num_width - 1

    # --- OLD: N COUNT queries (one DB round-trip per bucket) ---
    # buckets = []
    # cur_year = first_year
    # cur_num = first_num
    # while True:
    #     start_num = cur_num
    #     end_num = min(cur_num + bucket_size - 1, max_num)
    #     start_id = f"{prefix}{cur_year:02d}{start_num:0{num_width}d}"
    #     end_id = f"{prefix}{cur_year:02d}{end_num:0{num_width}d}"
    #     is_exists = db.session.query(projectMaster).filter(projectMaster.quoteNo.between(start_id, end_id)).count()
    #     if is_exists:
    #         buckets.append(f"{start_id} - {end_id}")
    #     if cur_year > last_year or (cur_year == last_year and end_num >= last_num):
    #         break
    #     if end_num == max_num:
    #         cur_year += 1
    #         cur_num = 0
    #     else:
    #         cur_num = end_num + 1
    # return buckets
    # --- END OLD ---

    # NEW: single query → bucket in Python with O(1) set lookup per iteration.
    # Fetches all quoteNos in [first_id, last_id] in one DB round-trip, then
    # maps each to its bucket key (2-digit year, bucket_start_num).
    # Assumes first_num == 0 so bucket boundaries align to multiples of bucket_size.
    rows = (
        db.session.query(projectMaster.quoteNo)
        .filter(projectMaster.quoteNo.between(first_id, last_id))
        .all()
    )

    occupied: set[tuple[int, int]] = set()
    for (qno,) in rows:
        if qno and len(qno) >= 8:
            try:
                yr = int(qno[1:3])
                num = int(qno[3:])
                occupied.add((yr, (num // bucket_size) * bucket_size))
            except ValueError:
                pass

    buckets = []
    cur_year = first_year
    cur_num = first_num

    while True:
        start_num = cur_num
        end_num = min(cur_num + bucket_size - 1, max_num)

        if (cur_year, start_num) in occupied:
            start_id = f"{prefix}{cur_year:02d}{start_num:0{num_width}d}"
            end_id = f"{prefix}{cur_year:02d}{end_num:0{num_width}d}"
            buckets.append(f"{start_id} - {end_id}")

        if cur_year > last_year or (cur_year == last_year and end_num >= last_num):
            break

        if end_num == max_num:
            cur_year += 1
            cur_num = 0
        else:
            cur_num = end_num + 1

    return buckets


# Module-level cache for getLatestFccLiveProject('last') — avoids a DB query
# on every page load. TTL of 60 s is short enough to reflect new projects quickly.
_latest_fcc_cache: dict = {'value': None, 'ts': 0.0}
_LATEST_FCC_TTL = 60  # seconds


def getLatestFccLiveProject(res_type: str) -> str | None:
    """
    Return quoteNo of the latest (or near-latest) FCC live project.

    The 'last' result is cached for 60 seconds to avoid a DB round-trip on
    every dashboard page load.
    """
    global _latest_fcc_cache

    now = time.monotonic()
    if (
        res_type == 'last'
        and _latest_fcc_cache['value'] is not None
        and now - _latest_fcc_cache['ts'] < _LATEST_FCC_TTL
    ):
        return _latest_fcc_cache['value']

    quote_format = r"^Q\d{2}\d+$"
    year = cast(func.substr(projectMaster.quoteNo, 2, 2), Integer)
    suffix = cast(func.right(projectMaster.quoteNo, 5), Integer)

    base_query = (
        db.session.query(projectMaster.quoteNo)
        .join(userMaster, projectMaster.createdById == userMaster.id)
        .filter(
            userMaster.fccUser.is_(True),
            projectMaster.projectRef != 'TESTCASES',
            projectMaster.quoteNo.isnot(None),
            projectMaster.quoteNo != '',
            # .op("~") is PostgreSQL-only; .regexp_match() is dialect-agnostic
            # projectMaster.quoteNo.regexp_match(quote_format),
            projectMaster.quoteNo.op("~")(quote_format),
        )
        .order_by(year.desc(), suffix.desc())
    )

    if res_type == "last":
        result = base_query.limit(1).scalar()
        _latest_fcc_cache = {'value': result, 'ts': now}
        return result

    return base_query.offset(99).limit(1).scalar()


def get_last_Q26() -> str:
    """Return the highest quoteNo matching Q26xxxxx (non-testcase). Fallback 'Q2600000'."""
    try:
        year = cast(func.substr(projectMaster.quoteNo, 2, 2), Integer)
        suffix = cast(func.right(projectMaster.quoteNo, 5), Integer)

        row = (
            db.session.query(projectMaster.quoteNo)
            .filter(
                projectMaster.quoteNo.like('Q26%'),
                ~projectMaster.quoteNo.like('Q26TC%'),
                projectMaster.projectRef != 'TESTCASES',
            )
            .order_by(year.desc(), suffix.desc())
            .first()
        )
        return row[0] if row else 'Q2600000'
    except Exception as exc:
        print(f'get_last_Q26 error: {exc}')
        return 'Q2600000'


def get_last_Q25() -> str:
    """Return the highest quoteNo matching Q25xxxxx (non-testcase). Fallback 'Q2500000'."""
    try:
        year = cast(func.substr(projectMaster.quoteNo, 2, 2), Integer)
        suffix = cast(func.right(projectMaster.quoteNo, 5), Integer)

        row = (
            db.session.query(projectMaster.quoteNo)
            .filter(
                projectMaster.quoteNo.like('Q25%'),
                ~projectMaster.quoteNo.like('Q25TC%'),
                projectMaster.quoteNo.isnot(None),
                projectMaster.quoteNo != '',
                projectMaster.projectRef != 'TESTCASES',
            )
            .order_by(year.desc(), suffix.desc())
            .first()
        )
        return row[0] if row else 'Q2500000'
    except Exception as exc:
        print(f'get_last_Q25 error: {exc}')
        return 'Q2500000'


def resolve_project_bucket(request, session, last_project: str | None) -> str:
    """
    Determine which bucket is selected, persisting to Flask session.

    Priority: query arg → session → default derived from last_project.
    No logic change from original.
    """
    if last_project:
        prefix = last_project[:3]
        last_num = int(last_project[3:])
        bucket_start = (last_num // 100) * 100
        bucket_end = bucket_start + 99
        default_bucket = (
            f"{prefix}{str(bucket_start).zfill(4)} - "
            f"{prefix}{str(bucket_end).zfill(4)}"
        )
    else:
        default_bucket = "Obsolete"

    selected_bucket = request.args.get('set-projects')
    if selected_bucket:
        session['selected_bucket'] = selected_bucket
    elif session.get('selected_bucket'):
        selected_bucket = session['selected_bucket']
    else:
        selected_bucket = default_bucket
        session['selected_bucket'] = selected_bucket

    return selected_bucket
