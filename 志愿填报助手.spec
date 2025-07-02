# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['score_analyzer.py'],
    pathex=[],
    binaries=[],
    datas=[('3年高考位次.csv', '.'), ('3年高考人数变化与高校计划招生变化.csv', '.')],
    hiddenimports=['rich'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='志愿填报助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
