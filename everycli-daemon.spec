from pathlib import Path
# -*- mode: python ; coding: utf-8 -*-

model_path = str(Path.home() / '.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2')

a = Analysis(
    ['everycli/everycli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('everycli/data/commands/*.yaml', 'everycli/data/commands'),
        ('.env/lib/python3.14/site-packages/sentence_transformers', 'sentence_transformers'),
        (str(Path.home()) + '/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2', 'models/paraphrase-multilingual-MiniLM-L12-v2'),
    ],
    hiddenimports=[
        'everycli.core',
        'everycli.infra',
        'rich',
        'typer',
        'yaml',
        'sklearn',
        'rank_bm25',
        'pick',
        'torch',
        'sentence_transformers',
        'transformers',
        'huggingface_hub',
    ],
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
