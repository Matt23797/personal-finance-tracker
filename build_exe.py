import os
import subprocess
import sys
from PIL import Image

def convert_favicon():
    print("Converting favicon.png to favicon.ico...")
    static_dir = os.path.join(os.getcwd(), 'static')
    png_path = os.path.join(static_dir, 'favicon.png')
    ico_path = os.path.join(static_dir, 'favicon.ico')
    
    if os.path.exists(png_path):
        img = Image.open(png_path)
        # Standard ICO sizes
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, sizes=icon_sizes)
        print(f"Icon saved to {ico_path}")
        return ico_path
    else:
        print(f"Error: {png_path} not found.")
        return None

def build_exe():
    ico_path = convert_favicon()
    
    # Use pyinstaller from the same venv or install location
    if os.name == 'nt':
        # On Windows, look for pyinstaller.exe in the Scripts folder relative to python.exe
        pyinstaller_bin = os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pyinstaller.exe')
        # If not there (e.g. system install), try just 'pyinstaller'
        if not os.path.exists(pyinstaller_bin):
            pyinstaller_bin = 'pyinstaller'
    else:
        pyinstaller_bin = os.path.join(os.path.dirname(sys.executable), 'pyinstaller')
    
    # Use ':' for non-Windows, ';' for Windows
    sep = ':' if os.name != 'nt' else ';'
    
    cmd = [
        pyinstaller_bin,
        "--noconsole",
        "--name=FinanceTracker",
        f"--add-data=templates{sep}templates",
        f"--add-data=static{sep}static",
        "--hidden-import=flask",
        "--hidden-import=flask_sqlalchemy",
        "--hidden-import=flask_migrate",
        "--hidden-import=flasgger",
        "--hidden-import=cryptography",
        "--hidden-import=sqlalchemy.sql.functions",
        "app.py"
    ]
    
    if ico_path:
        cmd.extend(["--icon", ico_path])
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build_exe()
