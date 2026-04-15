# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Valve Sizing Electron desktop backend.
#
# Build command (run from project root):
#   pyinstaller electron.spec
#
# Output: dist/ValveSizingBackend/  (folder bundle)

block_cipher = None

# ---------------------------------------------------------------------------
# Data files — (source, dest_in_bundle)
# ---------------------------------------------------------------------------
added_datas = [
    ('app/templates',  'app/templates'),
    ('app/static',     'app/static'),
    ('app/utils',      'app/utils'),
    ('config.py',      '.'),
    ('.env',           '.'),
    ('env.json',       '.'),
]

# Include data/ folder only if it exists and has content
import os
if os.path.isdir('data') and os.listdir('data'):
    added_datas.append(('data', 'data'))

# Bundle the pre-seeded SQLite database for first-run copy
if os.path.isfile('data/seed.db'):
    added_datas.append(('data/seed.db', 'data'))

# ---------------------------------------------------------------------------
# Hidden imports — modules that PyInstaller's static analysis may miss
# ---------------------------------------------------------------------------
hidden = [
    # Flask ecosystem
    'flask', 'flask.templating', 'flask_sqlalchemy', 'flask_login',
    'flask_mail', 'flask_migrate', 'flask_wtf', 'flask_bootstrap',
    'flask_restx',
    # Auth
    'authlib', 'authlib.integrations.flask_client',
    # SQLAlchemy + SQLite dialect
    'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext.declarative',
    'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.sqlite.pysqlite',
    # Forms
    'wtforms', 'wtforms.validators', 'email_validator',
    # Data / export
    'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
    'xlsxwriter', 'reportlab', 'reportlab.pdfgen', 'reportlab.lib',
    'pandas', 'numpy', 'PIL', 'pdfplumber',
    # Utilities
    'dotenv', 'requests', 'werkzeug', 'jinja2', 'markupsafe',
    # App package
    'app', 'app.extensions',
    'app.models.master', 'app.models.transactional',
    # Blueprints
    'app.blueprints.auth',        'app.blueprints.auth.routes',
    'app.blueprints.home',        'app.blueprints.home.routes',
    'app.blueprints.home.helpers',
    'app.blueprints.project',     'app.blueprints.project.routes',
    'app.blueprints.project.helpers', 'app.blueprints.project.helpers_import',
    'app.blueprints.valve_sizing','app.blueprints.valve_sizing.routes',
    'app.blueprints.actuator',    'app.blueprints.actuator.routes',
    'app.blueprints.noise',       'app.blueprints.noise.routes',
    'app.blueprints.specsheet',   'app.blueprints.specsheet.routes',
    'app.blueprints.admin',       'app.blueprints.admin.routes',
    'app.blueprints.customer',    'app.blueprints.customer.routes',
    'app.blueprints.pricing',     'app.blueprints.pricing.routes',
    # Services
    'app.services.liquid_sizing', 'app.services.gas_sizing',
    'app.services.twophase_sizing', 'app.services.actuator_sizing',
    'app.services.exports.excel', 'app.services.exports.pdf',
    'app.services.noise.gas_noise', 'app.services.noise.liquid_noise',
    # Forms
    'app.forms.auth', 'app.forms.project', 'app.forms.valve',
]

a = Analysis(
    ['electron_backend.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy/unused packages to keep bundle size down
    excludes=['psycopg2', 'psycopg2-binary', 'gunicorn', 'playwright',
              'matplotlib', 'tkinter', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ValveSizingBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window when launched by Electron
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ValveSizingBackend',
)