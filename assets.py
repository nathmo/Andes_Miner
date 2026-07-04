"""
assets.py — sprite loader with graceful placeholder fallback.

Real art can be dropped into ./assets later (e.g. assets/worker.png,
assets/miner_s.png, assets/oven.png). Until a file exists, get_sprite() returns
None and the renderer draws a geometric placeholder. This lets us ship now and
swap in sprites without touching render logic.
"""

import os
import sys
import pygame


def _base_dir():
    """Folder that holds the ``assets/`` directory.

    Under a PyInstaller bundle the data files are unpacked to ``sys._MEIPASS``;
    otherwise they sit next to this source file.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


_ASSET_DIR = os.path.join(_base_dir(), "assets")
_cache = {}


def get_sprite(key):
    """Return a Surface for `key` if assets/<key>.png exists, else None."""
    if key in _cache:
        return _cache[key]
    surf = None
    for ext in (".png", ".webp", ".jpg"):
        path = os.path.join(_ASSET_DIR, key + ext)
        if os.path.isfile(path):
            try:
                surf = pygame.image.load(path).convert_alpha()
            except Exception:
                surf = None
            break
    _cache[key] = surf
    return surf


def clear_cache():
    _cache.clear()
