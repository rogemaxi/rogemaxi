# PyInstaller spec for ByrdWay Product Engineering Studio (one-folder build).
# Build on Windows with build_windows_exe.bat. Chromium for browser tests is NOT bundled;
# install it once with:  .venv\Scripts\python -m playwright install chromium
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

_keep = lambda m: '.tests' not in m and not m.endswith('.conftest')
hidden = [m for m in (collect_submodules('sympy') + collect_submodules('pymupdf') + collect_submodules('playwright')
          + collect_submodules('openai')) if _keep(m)] + ['keyring.backends.Windows']
datas = (collect_data_files('playwright') + collect_data_files('rapidocr_onnxruntime') + collect_data_files('spellchecker')
         + collect_data_files('onnxruntime') + [('samples', 'samples')])
binaries = collect_dynamic_libs('onnxruntime')

a = Analysis(['app.py'], pathex=['.'], hiddenimports=hidden + ['selftest', 'selftest_fixtures', 'imageread'] + collect_submodules('rapidocr_onnxruntime'),
             datas=datas, binaries=binaries,
             excludes=['tests', 'matplotlib', 'IPython', 'notebook'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ByrdWayStudio', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='ByrdWayStudio')
