# -*- mode: python ; coding: utf-8 -*-


import os

# 1. Get the base application directory (where the spec file lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Pinpoint your nested entry script
entry_script = os.path.join(BASE_DIR, 'mamestates', 'gui.py')

# 3. Explicitly map items inside the directory directly to the internal root
collected_datas = []
for item in os.listdir(BASE_DIR):
    item_path = os.path.join(BASE_DIR, item)

    # Skip build folders and version control to avoid infinite loops
    if item in ['.git', '.github', 'build', 'dist', '__pycache__']:
        continue

    if os.path.isdir(item_path):
        # By setting the target to item, PyInstaller copies the folder's
        # *contents* into a matching folder inside _internal, keeping structural integrity
        collected_datas.append((item_path, item))
    else:
        # Files are dumped right at the root level of _internal
        collected_datas.append((item_path, '.'))

a = Analysis(
    [entry_script],
    pathex=[BASE_DIR],
    binaries=[],
    datas=collected_datas,  # Flat maps the base directory contents straight to _internal
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.datas = [x for x in a.datas if '.git' not in x[0]]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gui',
)
