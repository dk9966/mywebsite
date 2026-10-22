"""Render the restored upper gallery using the same inspection views."""
from pathlib import Path
import sys
P=Path(__file__).resolve().parent
source=(P.parent/'upper-gallery-half-light/render_check.py').read_text()
source=source.replace("half-light-cutaway.png","restored-cutaway.png").replace("half-light-review.png","restored-in-cave.png")
exec(compile(source,str(P/'render_review.py'),'exec'))
