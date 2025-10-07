# -*- mode: python ; coding: utf-8 -*-

import sys
import sysconfig
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

_spec_path = Path(globals().get('__file__', sys.argv[0])).resolve()
ROOT = _spec_path.parents[1]

datas = [
    (str(ROOT / "web" / "templates"), "web/templates"),
    (str(ROOT / "web" / "__init__.py"), "web"),
    (str(ROOT / "web" / "app.py"), "web"),
    (str(ROOT / "web" / "rag_server.py"), "web"),
]

icon_file = ROOT / "mac_app" / "SuperLibraryMachine.icns"
spec = importlib.util.find_spec("unstructured")
if spec and spec.origin:
    unstructured_root = Path(spec.origin).resolve().parent
    words_file = unstructured_root / "nlp" / "english-words.txt"
    if words_file.exists():
        datas.append((str(words_file), "unstructured/nlp"))

example_dbs = ROOT / "exampleDBs"
if example_dbs.exists():
    datas.append((str(example_dbs), "exampleDBs"))

lib_dir = sysconfig.get_config_var('LIBDIR') or ''
libpython_name = f"libpython{sys.version_info.major}.{sys.version_info.minor}.dylib"
libpython_path = Path(lib_dir) / libpython_name

binaries = []
if libpython_path.exists():
    binaries.append((str(libpython_path), '.'))

hiddenimports = (
    collect_submodules("flask")
    + collect_submodules("werkzeug")
    + ["web.rag_server"]
)

hiddenimports += collect_submodules("pipelinefiles")


faiss_datas, faiss_binaries, faiss_hiddenimports = collect_all("faiss")
datas.extend(faiss_datas)
binaries.extend(faiss_binaries)
hiddenimports.extend(faiss_hiddenimports)


a = Analysis(
    [str(ROOT / 'mac_app' / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=binaries,
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
    name='SuperLibraryMachine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
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
    name='SuperLibraryMachine'
)


app = BUNDLE(
    coll,
    name='SuperLibraryMachine.app',
    icon=str(icon_file) if icon_file.exists() else None,
    bundle_identifier='com.superlibrarymachine.app',
)
