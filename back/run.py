"""Arranque local del backend: `python3 back/run.py` (sirve también el front)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aulalista.server import main  # noqa: E402

if __name__ == "__main__":
    main()
