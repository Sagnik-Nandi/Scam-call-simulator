import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ALLOW_TEXT_TURN", "1")   # tests drive the API with typed text, no audio or credits
