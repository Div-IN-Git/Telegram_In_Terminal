# PyInstaller entry-point placeholder:
# pyinstaller scripts/build_cli.spec

a = Analysis(["bits_cli/main.py"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, name="bits")
