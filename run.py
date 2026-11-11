"""Atalho de execução a partir do código-fonte: `python run.py` (equivale a `finserve serve`)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

if __name__ == "__main__":
    from finserve.cli import main

    raise SystemExit(main(["serve", *sys.argv[1:]]))
