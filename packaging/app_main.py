"""Bundle entry point for py2app — defers to the real menu-bar app.

Kept as a thin shim (not the package module) so py2app has a concrete script to wrap and the
import path is unambiguous inside the frozen bundle.
"""
from w1_macos.app import main

if __name__ == "__main__":
    raise SystemExit(main())
