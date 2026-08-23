# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

# On essaie de localiser le modèle dans le dossier courant ou dans le cache
# Pour le build CI, on s'assure qu'il est téléchargé avant.
model_name = "Michelhe/everycli-minilm-ft-boosted"

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
# SAUF si on est en mode LITE
if os.path.exists(model_name) and os.environ.get('EVERYCLI_LITE') != '1':
    datas.append((model_name, f'models/{model_name}'))
    print("--- Mode FULL : Modèle IA inclus ---")
else:
    print("--- Mode LITE : Modèle IA exclu (sera téléchargé au premier run) ---")

a = Analysis(
    ['everycli/everycli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        'nvidia', 'nvidia-cuda-nvrtc-cu12', 'nvidia-cuda-runtime-cu12',
        'nvidia-cuda-cupti-cu12', 'nvidia-cudnn-cu12', 'nvidia-cublas-cu12',
        'nvidia-cufft-cu12', 'nvidia-curand-cu12', 'nvidia-cusolver-cu12',
        'nvidia-cusparse-cu12', 'nvidia-npp-cu12', 'nvidia-nvjitlink-cu12',
        'nvidia-nvtx-cu12', 'triton', 'tensorrt'
    ],
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
