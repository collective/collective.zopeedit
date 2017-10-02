# -*- mode: python -*-
# For use with pyinstaller (pyinstaller.org)
a = Analysis(['collective\\zopeedit\\zopeedit.py'],
             pathex=['collective\\zopeedit'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='zopeedit.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=False,
               name='ZopeEdit')
