"""
Seed a SQLite database with master/reference data from PostgreSQL.

Usage:
    # Build mode — outputs to data/seed.db for bundling with PyInstaller
    python scripts/seed_sqlite.py

    # Legacy mode — seeds the live user database in %APPDATA%\ValveSizing
    python scripts/seed_sqlite.py --appdata

Prerequisites:
    1. Flask app must be importable (project root in sys.path).
    2. The SQLite schema is created automatically by this script via db.create_all().

Environment variables (all optional, defaults match dev setup):
    DATABASE_URL   — PostgreSQL source  (default: postgresql://postgres:postgres@localhost/ValveSizing_Dev)
    APPDATA        — Windows %APPDATA%  (used in --appdata mode)
"""

import json
import os
import sys

# Allow imports from the project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from sqlalchemy import create_engine, inspect, text

# ---------------------------------------------------------------------------
# Source (PostgreSQL) connection string
# ---------------------------------------------------------------------------
PG_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost/ValveSizing_Dev'
)

# ---------------------------------------------------------------------------
# Target SQLite path
#   Default (build mode):  data/seed.db  — gets bundled into the .exe
#   --appdata mode:        %APPDATA%\ValveSizing\valvesizing.db
# ---------------------------------------------------------------------------
_appdata_mode = '--appdata' in sys.argv

if _appdata_mode:
    _user_data = os.path.join(
        os.environ.get('APPDATA', os.path.expanduser('~')),
        'ValveSizing'
    )
    os.makedirs(_user_data, exist_ok=True)
    SQLITE_PATH = os.path.join(_user_data, 'valvesizing.db')
else:
    _data_dir = os.path.join(_PROJECT_ROOT, 'data')
    os.makedirs(_data_dir, exist_ok=True)
    SQLITE_PATH = os.path.join(_data_dir, 'seed.db')

SQLITE_URL = 'sqlite:///' + SQLITE_PATH

# ---------------------------------------------------------------------------
# Schema bootstrap — create all tables in the target SQLite before seeding
# ---------------------------------------------------------------------------
def _create_schema() -> None:
    """Run db.create_all() against the SQLite target using ElectronConfig."""
    # Temporarily point ElectronConfig at our target path
    os.environ['SQLITE_SEED_PATH'] = SQLITE_PATH
    from app import create_app
    from app.extensions import db

    # Patch ElectronConfig URI to use our resolved path
    from config import ElectronConfig
    ElectronConfig.SQLALCHEMY_DATABASE_URI = SQLITE_URL

    app = create_app('electron')
    with app.app_context():
        db.create_all()
    print(f'Schema created at: {SQLITE_PATH}')


# ---------------------------------------------------------------------------
# Master table names (exact __tablename__ values from app/models/master.py)
# Order matters for FK constraints: parents before children.
# ---------------------------------------------------------------------------
MASTER_TABLES = [
    # Utility / test
    'newCol', 'stemSize', 'Test',
    # Organisation reference (no FKs to other masters)
    'companyMaster', 'departmentMaster', 'designationMaster',
    'industryMaster', 'regionMaster',
    'engineerMaster', 'notesMaster',
    # Valve configuration lookups (no cross-master FKs)
    'fluidState', 'designStandard', 'ratingMaster', 'materialMaster',
    'applicationMaster',
    # Valve component dropdowns
    'valveStyle',
    'endConnection', 'endFinish', 'bonnetType', 'packingType',
    'trimType', 'bodyFFDimension', 'flowCharacter', 'flowDirection',
    'seatLeakageClass', 'bonnet', 'nde1', 'nde2',
    'shaftRotary', 'shaft', 'plug', 'disc', 'seal', 'seat',
    'packing', 'balanceSeal', 'studNut', 'gasket', 'cageClamp', 'balancing',
    # Validation tables (reference valveStyle)
    'valveDataSeriesValidation', 'valveDataffValidation', 'valveDataBonnetValidation',
    # Engineering lookup tables
    'pipeArea', 'baffleTable',
    'cvTable', 'cvValues',
    'refCvTable', 'refCvValues',
    'fluidProperties', 'valveDataNoise', 'caseWarningMaster',
    # Actuator reference
    'volumeTankSize', 'actuatorClearanceVolume',
    # GA / drawing reference
    'gaMasterKey', 'endConnectionStandard', 'gadAutomationMaster',
    # Pressure / temperature rating
    'pressureTempRating',
    # Trim noise lookup
    'trimNoiseLiquid' if False else None,   # include if table exists in PG
    'trimNoise'       if False else None,   # include if table exists in PG
    # Help system
    'helpFolders', 'helpFiles',
    # Mechanical / strength lookups
    'yieldStrength', 'packingFriction', 'packingTorque',
    'seatLoadForce', 'seatingTorque',
    # Accessories catalogue
    'positioner', 'afr', 'volumeBooster', 'limitSwitch', 'solenoid',
    'cleaning', 'paintCerts', 'paintFinish', 'certification', 'positionerSignal',
    # Flow / area tables
    'valveAreaTb', 'valveArea', 'portArea', 'hwThrust', 'knValue',
    'twoPhaseCorrectionFactor', 'kcTable', 'multiHoleDJ', 'unbalanceAreaTb',
    # Noise trim lookup (separate table)
    # Pricing / configuration
    'project_number_ranges',
    'bodyPriceMaster', 'bonnetPriceMaster', 'testingPriceMaster',
    'castingPriceMaster', 'forgingPriceMaster',
    # Organisation (FKs to companyMaster)
    'addressMaster',
]

# Remove None placeholders (tables skipped above)
MASTER_TABLES = [t for t in MASTER_TABLES if t]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise_row(row_dict: dict) -> dict:
    """Convert any list values (PostgreSQL ARRAY) to JSON strings."""
    result = {}
    for k, v in row_dict.items():
        if isinstance(v, (list, tuple)):
            result[k] = json.dumps(list(v))
        else:
            result[k] = v
    return result


def seed() -> None:
    # Ensure schema exists before copying data
    _create_schema()

    print(f'Source : {PG_URL}')
    print(f'Target : {SQLITE_URL}')
    print()

    pg_engine  = create_engine(PG_URL)
    sq_engine  = create_engine(SQLITE_URL)

    pg_insp = inspect(pg_engine)
    sq_insp = inspect(sq_engine)

    pg_tables = set(pg_insp.get_table_names())
    sq_tables = set(sq_insp.get_table_names())

    ok = skipped = errors = 0

    with pg_engine.connect() as pg_conn, sq_engine.connect() as sq_conn:
        for table in MASTER_TABLES:
            # ── Skip if missing from either database ─────────────────────
            if table not in pg_tables:
                print(f'  SKIP  {table!r:<35} (not in PostgreSQL)')
                skipped += 1
                continue
            if table not in sq_tables:
                print(f'  SKIP  {table!r:<35} (not in SQLite — run db.create_all first)')
                skipped += 1
                continue

            try:
                # Find columns common to both DBs (handles schema drift)
                pg_cols = {c['name'] for c in pg_insp.get_columns(table)}
                sq_cols = {c['name'] for c in sq_insp.get_columns(table)}
                cols    = sorted(pg_cols & sq_cols)

                if not cols:
                    print(f'  SKIP  {table!r:<35} (no common columns)')
                    skipped += 1
                    continue

                col_sql  = ', '.join(f'"{c}"' for c in cols)
                rows = pg_conn.execute(
                    text(f'SELECT {col_sql} FROM "{table}"')
                ).fetchall()

                # Wipe SQLite target first to avoid PK conflicts on re-seed
                sq_conn.execute(text(f'DELETE FROM "{table}"'))

                if rows:
                    placeholders = ', '.join(f':{c}' for c in cols)
                    insert_sql   = (
                        f'INSERT OR REPLACE INTO "{table}" ({col_sql}) '
                        f'VALUES ({placeholders})'
                    )
                    for row in rows:
                        sq_conn.execute(
                            text(insert_sql),
                            _serialise_row(dict(zip(cols, row)))
                        )

                sq_conn.commit()
                print(f'  OK    {table!r:<35} {len(rows):>6} rows')
                ok += 1

            except Exception as exc:
                sq_conn.rollback()
                print(f'  ERROR {table!r:<35} {exc}')
                errors += 1

    print()
    print(f'Done — {ok} seeded, {skipped} skipped, {errors} errors.')


if __name__ == '__main__':
    seed()