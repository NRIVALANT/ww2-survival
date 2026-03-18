# ww2survival.spec — PyInstaller bundle pour main_client.py
# Usage : pyinstaller ww2survival.spec
#
# Compatible PyInstaller 6.x+

a = Analysis(
    ['main_client.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'websockets',
        'websockets.legacy',
        'websockets.legacy.client',
        'websockets.legacy.protocol',
        'websockets.extensions',
        'websockets.extensions.permessage_deflate',
        'websockets.http11',
        'asyncio',
        'asyncio.selector_events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'main',
        'main_server',
        'server_headless',
        'status_api',
        'tkinter',
        'unittest',
        'pydoc',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ww2survival',
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
    icon=None,
)
