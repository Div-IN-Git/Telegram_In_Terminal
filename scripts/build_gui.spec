# PyInstaller entry-point placeholder:
# pyinstaller scripts/build_gui.spec

a = Analysis(["bits_gui/app.py"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, name="bits-gui", console=False)
