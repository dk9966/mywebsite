"""Build the current interior-only scene (the thick shell was superseded)."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('build_interior_cavern.py')),run_name='__main__')
