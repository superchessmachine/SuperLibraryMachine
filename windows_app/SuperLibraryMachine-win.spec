# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

_spec_path = Path(globals().get("__file__", sys.argv[0])).resolve()
ROOT = _spec_path.parents[1]


datas = [
    (str(ROOT / "web" / "templates"), "web/templates"),
    (str(ROOT / "web" / "__init__.py"), "web"),
    (str(ROOT / "web" / "app.py"), "web"),
    (str(ROOT / "web" / "rag_server.py"), "web"),
]

example_dbs = ROOT / "exampleDBs"
if example_dbs.exists():
    datas.append((str(example_dbs), "exampleDBs"))


hiddenimports = (
    collect_submodules("flask")
    + collect_submodules("werkzeug")
    + ["web.rag_server"]
)


a = Analysis(
    [str(ROOT / "mac_app" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="SuperLibraryMachine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SuperLibraryMachine",
)
