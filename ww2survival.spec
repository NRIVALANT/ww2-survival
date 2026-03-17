# ww2survival.spec — PyInstaller bundle pour main_client.py
# Usage : pyinstaller ww2survival.spec
#
# Génère dist/ww2survival.exe (Windows) ou dist/ww2survival (Linux/macOS).
# Le binaire est autonome : aucune installation Python requise chez le joueur.

block_cipher = None

a = Analysis(
    ['main_client.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # websockets internals non détectés par l'analyse statique
        'websockets',
        'websockets.legacy',
        'websockets.legacy.client',
        'websockets.legacy.protocol',
        'websockets.extensions',
        'websockets.extensions.permessage_deflate',
        'websockets.http11',
        # asyncio backends
        'asyncio',
        'asyncio.selector_events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclure tout ce qui est serveur — inutile dans le client
    excludes=[
        'main',
        'main_server',
        'server_headless',
        'status_api',
        'deploy',
        'tkinter',
        'unittest',
        'email',
        'html',
        'http',
        'xml',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zlib_archive, cipher=block_cipher)

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
    console=False,      # pas de fenêtre console (mode fenêtré)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # remplacer par 'assets/icon.ico' si tu en as une
)
