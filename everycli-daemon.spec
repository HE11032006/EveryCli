# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

# On essaie de localiser le modèle dans le dossier courant ou dans le cache
# Pour le build CI, on s'assure qu'il est téléchargé avant.
model_name = "paraphrase-multilingual-MiniLM-L12-v2"

# Collecte automatique pour les grosses librairies complexes
datas = [('everycli/data/commands/*.yaml', 'everycli/data/commands')]
binaries = []
hiddenimports = [
    'everycli.core', 'everycli.infra', 'rich', 'typer', 'yaml', 
    'sklearn', 'rank_bm25', 'pick', 'torch', 'sentence_transformers', 
    'transformers', 'huggingface_hub'
]

# Cette fonction magique de PyInstaller va trouver tout ce qu'il faut pour sentence_transformers
tmp_ret = collect_all('sentence_transformers')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# On ajoute le modèle s'il existe localement (téléchargé par le workflow)
if os.path.exists(model_name):
    datas.append((model_name, f'models/{model_name}'))

a = Analysis(
    ['everycli/everycli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='everycli-daemon',
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
