"""
Electron desktop app entry point — bundled by PyInstaller.

Responsibilities:
  1. Resolve the correct base path (frozen bundle vs. dev)
  2. Find a free local port
  3. Write that port to %APPDATA%/ValveSizing/port.txt so Electron can connect
  4. Upgrade the SQLite database on every launch:
       - Create any new tables  (db.create_all)
       - Add any new columns    (ALTER TABLE ADD COLUMN patches)
       - Sync new master data   (INSERT OR IGNORE from bundled seed.db)
  5. Start Flask on 127.0.0.1:<port> with threading enabled
"""

import os
import sys
import socket
import shutil
import sqlite3

# ---------------------------------------------------------------------------
# Path resolution — must happen before any app imports
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Running inside a PyInstaller bundle; _MEIPASS is the temp extraction dir
    _base = sys._MEIPASS
    os.chdir(_base)
else:
    _base = os.path.dirname(os.path.abspath(__file__))

if _base not in sys.path:
    sys.path.insert(0, _base)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_USER_DATA = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'ValveSizing'
)
_DB_PATH   = os.path.join(_USER_DATA, 'valvesizing.db')
_SEED_PATH = os.path.join(_base, 'data', 'seed.db')

# ---------------------------------------------------------------------------
# Master tables — only these are synced from seed.db on upgrade.
# Transactional tables (projects, sizing records, etc.) are never touched.
# Order matters for FK constraints: parents before children.
# ---------------------------------------------------------------------------
_MASTER_TABLES = [
    # Utility / test
    'newCol', 'stemSize', 'Test',
    # Organisation reference
    'companyMaster', 'departmentMaster', 'designationMaster',
    'industryMaster', 'regionMaster',
    'engineerMaster', 'notesMaster',
    # Valve configuration lookups
    'fluidState', 'designStandard', 'ratingMaster', 'materialMaster',
    'applicationMaster',
    # Valve component dropdowns
    'valveStyle',
    'endConnection', 'endFinish', 'bonnetType', 'packingType',
    'trimType', 'bodyFFDimension', 'flowCharacter', 'flowDirection',
    'seatLeakageClass', 'bonnet', 'nde1', 'nde2',
    'shaftRotary', 'shaft', 'plug', 'disc', 'seal', 'seat',
    'packing', 'balanceSeal', 'studNut', 'gasket', 'cageClamp', 'balancing',
    # Validation tables
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
    # Pricing / configuration
    'project_number_ranges',
    'bodyPriceMaster', 'bonnetPriceMaster', 'testingPriceMaster',
    'castingPriceMaster', 'forgingPriceMaster',
    # Organisation (FKs to companyMaster)
    'addressMaster',
]

# ---------------------------------------------------------------------------
# Column patches — add new columns here when you add fields to any model.
# These are applied on every launch (safe: skipped if column already exists).
#
# Format: ('table_name', 'column_name', 'SQL type + default')
#
# Example:
#   ('projectMaster', 'priority',   'TEXT DEFAULT NULL'),
#   ('valveStyle',    'is_rotary',  'INTEGER DEFAULT 0'),
# ---------------------------------------------------------------------------
_COLUMN_PATCHES = [
    # v1.x patches go here
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _free_port() -> int:
    """Bind to port 0 and let the OS pick a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _write_port(port: int) -> None:
    """Write chosen port to a file so the Electron main process can read it."""
    os.makedirs(_USER_DATA, exist_ok=True)
    with open(os.path.join(_USER_DATA, 'port.txt'), 'w') as fh:
        fh.write(str(port))


# ---------------------------------------------------------------------------
# Database upgrade — runs on every launch
# ---------------------------------------------------------------------------
def _step1_new_tables(app) -> None:
    """Create any tables that exist in models but not yet in the user DB."""
    from app.extensions import db
    with app.app_context():
        db.create_all()
    print('[DB] Step 1: new tables checked')


def _step2_new_columns() -> None:
    """Apply ALTER TABLE ADD COLUMN for any new fields added since last install.
    Silently skips columns that already exist.
    """
    if not _COLUMN_PATCHES:
        print('[DB] Step 2: no column patches')
        return

    conn = sqlite3.connect(_DB_PATH)
    cur  = conn.cursor()

    for table, column, definition in _COLUMN_PATCHES:
        try:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')
            print(f'[DB] Step 2: added column {table}.{column}')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                pass  # already exists — skip silently
            else:
                print(f'[DB] Step 2: WARNING — {table}.{column}: {e}')

    conn.commit()
    conn.close()
    print('[DB] Step 2: column patches done')


def _step3_sync_master_data() -> None:
    """Merge new master data rows from the bundled seed.db into the user DB.

    Uses SQLite ATTACH so everything runs in-process without SQLAlchemy.
    - INSERT OR IGNORE  → adds rows that don't exist yet (new master entries)
    - UPDATE            → refreshes existing rows with latest values from seed
                          (safe: master tables are lookup data, not user data)
    Transactional tables are never touched.
    """
    if not os.path.exists(_SEED_PATH):
        print('[DB] Step 3: seed.db not found — skipping master data sync')
        return

    conn = sqlite3.connect(_DB_PATH)
    cur  = conn.cursor()

    # Attach the bundled seed database as a read-only source
    cur.execute(f"ATTACH DATABASE '{_SEED_PATH}' AS seed")

    # Get tables present in both databases
    cur.execute("SELECT name FROM seed.sqlite_master WHERE type='table'")
    seed_tables = {row[0] for row in cur.fetchall()}

    cur.execute("SELECT name FROM main.sqlite_master WHERE type='table'")
    user_tables = {row[0] for row in cur.fetchall()}

    synced = skipped = 0

    for table in _MASTER_TABLES:
        if table not in seed_tables:
            skipped += 1
            continue
        if table not in user_tables:
            skipped += 1
            continue

        try:
            # Get column names common to both (handles any schema drift)
            cur.execute(f'PRAGMA main.table_info("{table}")')
            user_cols = {row[1] for row in cur.fetchall()}

            cur.execute(f'PRAGMA seed.table_info("{table}")')
            seed_cols = {row[1] for row in cur.fetchall()}

            cols     = sorted(user_cols & seed_cols)
            col_list = ', '.join(f'"{c}"' for c in cols)

            # Add new rows (skip if primary key already exists)
            cur.execute(
                f'INSERT OR IGNORE INTO main."{table}" ({col_list}) '
                f'SELECT {col_list} FROM seed."{table}"'
            )

            # Update existing rows with latest values from seed
            # (refreshes changed lookup data — e.g. renamed valve styles, new Cv values)
            set_clause = ', '.join(f'"{c}" = excluded."{c}"' for c in cols)
            cur.execute(
                f'INSERT INTO main."{table}" ({col_list}) '
                f'SELECT {col_list} FROM seed."{table}" '
                f'ON CONFLICT DO UPDATE SET {set_clause}'
            )

            synced += 1

        except sqlite3.OperationalError as e:
            print(f'[DB] Step 3: WARNING — {table}: {e}')

    conn.commit()
    cur.execute("DETACH DATABASE seed")
    conn.close()
    print(f'[DB] Step 3: master data synced ({synced} tables, {skipped} skipped)')


def _setup_database(app) -> None:
    """Full database setup — safe to run on every launch.

    First install:  copies bundled seed.db to user data dir.
    Every launch:   runs all 3 upgrade steps so the DB stays current.
    """
    os.makedirs(_USER_DATA, exist_ok=True)

    if not os.path.exists(_DB_PATH):
        # ── First install ──────────────────────────────────────────────────
        if os.path.exists(_SEED_PATH):
            shutil.copy2(_SEED_PATH, _DB_PATH)
            print(f'[DB] First install: database copied from seed')
        else:
            # Dev fallback — no seed.db present (running from source)
            _step1_new_tables(app)
            print(f'[DB] First install: empty schema created (dev mode)')
    else:
        # ── Existing install — upgrade ─────────────────────────────────────
        print(f'[DB] Existing database found — running upgrade checks')
        _step1_new_tables(app)    # new tables
        _step2_new_columns()      # new columns
        _step3_sync_master_data() # new/updated master rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = _free_port()
    _write_port(port)

    from app import create_app
    app = create_app('electron')

    _setup_database(app)

    app.run(
        host='127.0.0.1',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )