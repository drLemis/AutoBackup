# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['AutoBackup.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('strings/en.json', 'strings'),
        ('strings/ru.json', 'strings'),
    ],
    hiddenimports=['locale_util', 'version_check'],
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
    name='AutoBackup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
