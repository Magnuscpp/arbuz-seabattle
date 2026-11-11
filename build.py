"""Сборка автономного Windows-приложения."""
from pathlib import Path
import subprocess
import sys
import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(ROOT / "make_ui_assets.py")], check=True)

PyInstaller.__main__.run([
    str(ROOT / "main.py"),
    "--name=SeaBattle",
    "--onefile",
    "--windowed",
    "--clean",
    f"--add-data={ROOT / 'assets' / 'ui'};assets/ui",
    f"--add-data={ROOT / 'web'};web",
    "--collect-all=dearpygui",
    "--exclude-module=numpy",
    "--exclude-module=scipy",
    "--exclude-module=matplotlib",
    "--exclude-module=cryptography",
    "--exclude-module=tkinter",
    "--exclude-module=tcl",
    "--exclude-module=tk",
    "--exclude-module=unittest",
    "--exclude-module=pydoc",
    "--exclude-module=pydoc_data",
    "--exclude-module=setuptools",
    "--exclude-module=distutils",
    "--exclude-module=pip",
    "--exclude-module=pygame",
    "--exclude-module=PIL._avif",
    "--exclude-module=PIL._tkinter_finder",
    "--exclude-module=sqlite3",
    "--exclude-module=test",
    f"--distpath={ROOT / 'dist'}",
    f"--workpath={ROOT / 'build'}",
    f"--specpath={ROOT}",
])
