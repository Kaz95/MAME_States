# -*- mode: python ; coding: utf-8 -*-
import os
import glob

# 1. Safely resolve the true base directory regardless of nested runner paths
SPEC_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Correctly pinpoint your nested script relative to the spec location
# This resolves to "D:\a\MAME_States\mamestates\gui.py"
entry_script = os.path.join(SPEC_DIR, 'mamestates', 'gui.py')

# 3. Manually collect files to avoid wildcard matching issues inside actions
collected_datas = []

# This loops through files inside the repository root
for item in os.listdir(SPEC_DIR):
    item_path = os.path.join(SPEC_DIR, item)

    # Exclude common build artifacts to prevent infinite compile loops
    if item in ['.git', '.github', 'build', 'dist', '__pycache__']:
        continue

    if os.path.isdir(item_path):
        # Format: (Source filesystem path, Target subfolder name inside _internal)
        collected_datas.append((item_path, item))
    else:
        # Format: (Source file path, Root of _internal)
        collected_datas.append((item_path, '.'))

a = Analysis(
    [entry_script],          # Solves the "D:\a\MAME_States\mamestates\gui.py" problem
    pathex=[SPEC_DIR],
    binaries=[],
    datas=collected_datas,    # Safely injects the true repository files into _internal
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
