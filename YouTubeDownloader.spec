# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['vlc']
# accessible_output2 contiene DLLs para lectores de pantalla (NVDA, JAWS, etc.)
tmp_ret = collect_all('accessible_output2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Catálogos de traducción de wxWidgets (soporte de idioma español)
import wx
wx_locale_dir = os.path.join(os.path.dirname(wx.__file__), 'locale')
if os.path.exists(wx_locale_dir):
    datas.append((wx_locale_dir, os.path.join('wx', 'locale')))



a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'yt_dlp',
        'static_ffmpeg',
        'pip',
        'setuptools',
        'distutils',
        'tkinter',
        'test',
        'unittest',
    ],
    noarchive=False,
    optimize=0,
)

# Excluir librerías de runtime C++ de la carpeta temporal _MEI...
# Esto obliga a Windows y a los hooks de JAWS (AceHook.dll) a usar las DLLs del sistema (System32),
# evitando bloqueos y errores de 'Failed to remove temporary directory' al salir.
a.binaries = [x for x in a.binaries if not x[0].upper().startswith(('MSVCP140', 'VCRUNTIME140'))]

pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YouTubeDownloader',
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
)
