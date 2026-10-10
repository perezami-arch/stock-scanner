"""Windowless launcher for stop_night.ps1 (the 08:00 task runs this with pythonw so no console flashes)."""
import os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, "stop_night.ps1")],
               cwd=HERE, creationflags=0x08000000, timeout=300)