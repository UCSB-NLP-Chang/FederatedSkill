#!/usr/bin/env python3
"""Helper script to set up openpyxl in a virtual environment."""

import subprocess
import sys
import os

VENV_PATH = '/tmp/excel_venv'

def ensure_venv():
    """Create venv and install openpyxl if not exists."""
    if not os.path.exists(VENV_PATH):
        print(f"Creating virtual environment at {VENV_PATH}...")
        subprocess.run([sys.executable, '-m', 'venv', VENV_PATH], check=True)
        
        pip_path = os.path.join(VENV_PATH, 'bin', 'pip')
        print("Installing openpyxl...")
        subprocess.run([pip_path, 'install', 'openpyxl', '-q'], check=True)
        print("Done.")
    return os.path.join(VENV_PATH, 'bin', 'python3')

if __name__ == '__main__':
    python_path = ensure_venv()
    print(f"Use this interpreter: {python_path}")
