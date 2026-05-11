# -*- mode: python ; coding: utf-8 -*-


import os
import sys

# Detects the directory where the .spec file is located
BASE_DIR = os.path.dirname(os.path.abspath(spec_file))

a = Analysis(
    [os.path.join(BASE_DIR, 'src', 'nested_folder', 'my_script.py')], # Points to your script
    pathex=[os.path.join(BASE_DIR, 'src')],
    binaries=[],
    datas=[('.', '.')],
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
