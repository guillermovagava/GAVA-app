"""
GAVA Recruiting — Desktop Launcher
Starts the FastAPI server and opens the app in the default browser.

This file is the PyInstaller entry point.
"""
import sys
import os
import threading
import time
import webbrowser


def get_bundle_dir() -> str:
    """Where PyInstaller extracted bundled files (or the source dir in dev mode)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS          # _internal/ folder next to the .exe
    return os.path.dirname(os.path.abspath(__file__))


def get_exe_dir() -> str:
    """Directory that contains the .exe (or project root in dev mode)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_browser():
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    bundle_dir  = get_bundle_dir()
    backend_dir = os.path.join(bundle_dir, "backend")

    # Make backend modules importable
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

    print("=" * 48)
    print("  GAVA Recruiting — starting server...")
    print("  Opening http://127.0.0.1:8000")
    print("=" * 48)

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start FastAPI / uvicorn (blocks until Ctrl+C or window close)
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="warning")
