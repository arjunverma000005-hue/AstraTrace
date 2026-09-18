"""Vercel entrypoint module for AstraTrace FastAPI backend."""
import sys
from pathlib import Path

# Ensure repository root and apps/backend are in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent.parent

for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app

__all__ = ["app"]
