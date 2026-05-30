"""
Entry point — run this file to launch the application.
Usage: python run.py
"""

import sys
import os

# Add src/ to the path so all modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import tkinter as tk
from app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
