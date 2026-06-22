"""Resolve bundled-asset paths in both the dev source tree and the frozen py2app bundle.

In development, assets live at the repo root (``…/W1/assets``). In a py2app bundle they are
copied to ``…/W1.app/Contents/Resources/assets``. ``resource_dir()`` returns the right parent
of ``assets/`` for whichever context the app is running in.
"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_dir() -> Path:
    """Directory that contains the ``assets/`` tree (frozen-bundle aware)."""
    if getattr(sys, "frozen", False):
        # py2app: executable is …/Contents/MacOS/<name>; resources are …/Contents/Resources.
        return Path(sys.executable).resolve().parent.parent / "Resources"
    return Path(__file__).resolve().parents[2]
