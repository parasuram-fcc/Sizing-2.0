"""
Valve Sizing — Desktop Build Script
====================================
Runs from the project root:

    python scripts/build.py            # full build (seed → PyInstaller → Electron)
    python scripts/build.py --backend  # seed + PyInstaller only
    python scripts/build.py --electron # Electron installer only (backend already built)
    python scripts/build.py --skip-seed  # skip seed step (use existing data/seed.db)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT      = Path(__file__).resolve().parent.parent   # e:\valvesizing_v2
ELECTRON  = ROOT / "electron"
SPEC      = ROOT / "electron.spec"
DIST_PY   = ROOT / "dist" / "ValveSizingBackend"
SEED_DB   = ROOT / "data" / "seed.db"
SEED_SCRIPT = ROOT / "scripts" / "seed_sqlite.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print('=' * 60)

def run(cmd: list, cwd: Path = ROOT) -> None:
    """Run a command, stream output, raise on failure."""
    print(f"  > {' '.join(str(c) for c in cmd)}\n")
    # shell=True required on Windows for .cmd tools like npm
    result = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def check(tool: str) -> str | None:
    """Return full path if tool is on PATH, else None."""
    return shutil.which(tool)


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
def check_prerequisites(need_node: bool) -> None:
    banner("Checking prerequisites")
    ok = True

    # Python
    py = check("python") or check("python3")
    if py:
        v = subprocess.check_output([py, "--version"], text=True).strip()
        print(f"  [OK] {v}")
    else:
        print("  [MISSING] Python — https://www.python.org/downloads/")
        ok = False

    # PyInstaller
    pi = check("pyinstaller")
    if pi:
        v = subprocess.check_output(["pyinstaller", "--version"], text=True).strip()
        print(f"  [OK] PyInstaller {v}")
    else:
        print("  [MISSING] PyInstaller — run:  pip install pyinstaller")
        ok = False

    # Node / npm  (only required for Electron step)
    if need_node:
        npm = check("npm")
        if npm:
            # v = subprocess.check_output(["npm", "--version"], text=True, shell=True).strip()
            v = subprocess.check_output(["npm", "--version"], text=True, shell=True).strip()

            print(f"  [OK] npm {v}")
        else:
            print()
            print("  [MISSING] Node.js / npm")
            print()
            print("  Node.js is only needed on YOUR machine to build the installer.")
            print("  End users do NOT need it.")
            print()
            print("  Install:")
            print("    1. https://nodejs.org/en/download  -> Windows Installer (LTS)")
            print("    2. Run the .msi with default options")
            print("    3. Open a NEW terminal and re-run this script")
            ok = False

    if not ok:
        sys.exit(1)

    print("\n  All prerequisites satisfied.")


# ---------------------------------------------------------------------------
# Build steps
# ---------------------------------------------------------------------------
def build_seed() -> None:
    banner("Seeding SQLite — building data/seed.db from PostgreSQL")
    run([sys.executable, str(SEED_SCRIPT)])
    if not SEED_DB.exists():
        print("[ERROR] data/seed.db was not created — check PostgreSQL connection and seed script output.")
        sys.exit(1)
    size_mb = SEED_DB.stat().st_size / (1024 * 1024)
    print(f"\n  Seed DB: {SEED_DB}  ({size_mb:.1f} MB)")


def build_backend() -> None:
    banner("PyInstaller — bundle Flask backend")
    run(["pyinstaller", str(SPEC), "--noconfirm"])
    if not DIST_PY.exists():
        print("[ERROR] Expected output not found:", DIST_PY)
        sys.exit(1)
    print(f"\n  Bundle: {DIST_PY}")


def build_electron() -> None:
    if not DIST_PY.exists():
        print(f"[ERROR] Backend bundle not found at {DIST_PY}")
        print("        Run with --backend first, or just run without flags for a full build.")
        sys.exit(1)

    banner("npm install — Electron dependencies")
    run(["npm", "install"], cwd=ELECTRON)

    banner("electron-builder — Windows installer")
    run(["npm", "run", "build:win"], cwd=ELECTRON)

    installer_dir = ROOT / "dist" / "electron"
    print(f"\n  Installer written to: {installer_dir}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Valve Sizing desktop build")
    parser.add_argument("--backend",    action="store_true", help="seed + PyInstaller only")
    parser.add_argument("--electron",   action="store_true", help="Electron installer only (backend already built)")
    parser.add_argument("--skip-seed",  action="store_true", help="skip seed step, use existing data/seed.db")
    args = parser.parse_args()

    do_backend  = args.backend  or (not args.backend and not args.electron)
    do_electron = args.electron or (not args.backend and not args.electron)
    do_seed     = do_backend and not args.skip_seed

    check_prerequisites(need_node=do_electron)

    if do_seed:
        build_seed()

    if do_backend:
        build_backend()

    if do_electron:
        build_electron()

    banner("Build complete")
    if do_electron:
        print(f"  Installer: {ROOT / 'dist' / 'electron'}")
    elif do_backend:
        print(f"  Bundle:    {DIST_PY}")


if __name__ == "__main__":
    main()