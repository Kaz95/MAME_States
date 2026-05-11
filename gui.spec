# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_ROOT = PROJECT_ROOT = Path(__file__).resolve().parent

# Scan the root directory and explicitly exclude build artifacts and git files
excluded_names = {'build', 'dist', '.git', '.github', '__pycache__', 'gui.spec'}

data_files = []
for path in PROJECT_ROOT.iterdir():
    if path.name not in excluded_names:
        if path.is_dir():
            # (source_directory, destination_subfolder_in_bundle)
            data_files.append((str(path), path.name))
        else:
            # (source_file, destination_root_in_bundle)
            data_files.append((str(path), '.'))

a = Analysis(
    [str(PROJECT_ROOT / 'mamestates' / 'gui.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=data_files,
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
