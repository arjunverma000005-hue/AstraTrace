"""Vercel entrypoint module for AstraTrace FastAPI backend."""
import os
import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent.parent

for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Preload bundled Linux shared libraries (e.g. libexpat.so.1 for rasterio/GDAL on AL2023)
for lib_dir in (BACKEND_DIR / "app" / "lib", BACKEND_DIR / "lib"):
    if lib_dir.exists():
        try:
            import ctypes
            expat_lib = lib_dir / "libexpat.so.1"
            if expat_lib.exists():
                ctypes.CDLL(str(expat_lib), mode=ctypes.RTLD_GLOBAL)
        except Exception:
            pass

# Create virtual package aliases for `apps` and `apps.backend`
# so that all existing absolute imports (`from apps.backend.app...`) resolve seamlessly
# when Vercel deploys `apps/backend` as its own service root.
if "apps" not in sys.modules:
    apps_mod = types.ModuleType("apps")
    apps_mod.__path__ = [str(BACKEND_DIR.parent)]
    sys.modules["apps"] = apps_mod

if "apps.backend" not in sys.modules:
    backend_mod = types.ModuleType("apps.backend")
    backend_mod.__path__ = [str(BACKEND_DIR)]
    backend_mod.__file__ = str(BACKEND_DIR / "__init__.py")
    sys.modules["apps.backend"] = backend_mod

from app.main import app

__all__ = ["app"]
