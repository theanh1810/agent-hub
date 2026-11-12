"""Puts the plugin's scripts and vendored lib on sys.path so the suites import them directly."""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / 'plugins' / 'agent-hub'
for sub in ('scripts', 'lib'):
    p = str(PLUGIN / sub)
    if p not in sys.path:
        sys.path.insert(0, p)
