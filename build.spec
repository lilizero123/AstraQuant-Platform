# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
使用方法: python -m PyInstaller build.spec
"""

import os
import sys
import akshare
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

project_root = Path(os.getcwd()).resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

akshare_data_dir = os.path.join(os.path.dirname(akshare.__file__), "file_fold")
ui_submodules = collect_submodules('ui')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('resources', 'resources'),
        (akshare_data_dir, 'akshare/file_fold'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'pandas',
        'numpy',
        'akshare',
    ] + ui_submodules,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='星衡量化平台',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/astra_icon.ico',
)
