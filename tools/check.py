#!/usr/bin/env python3
"""check: the package repo's one check command.

usage: tools/check.py ruleset           run tools/check-ruleset.sh over plugins/agent-hub (needs bash; Windows: Git Bash or WSL)
       tools/check.py plan PLAN [args]  run the plugin's plan-check.py
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "agent-hub"


def main(argv):
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in ("ruleset", "plan"):
        print(__doc__.strip(), file=sys.stderr if argv and argv[0] not in ("-h", "--help") else sys.stdout)
        return 2 if not argv or argv[0] not in ("-h", "--help") else 0
    env = dict(os.environ, PYTHONPATH=str(PLUGIN / "lib") + os.pathsep + os.environ.get("PYTHONPATH", ""))
    if argv[0] == "ruleset":
        cmd = ["bash", str(REPO / "tools" / "check-ruleset.sh")] + argv[1:]
    else:
        cmd = [sys.executable, str(PLUGIN / "scripts" / "plan-check.py")] + argv[1:]
    return subprocess.run(cmd, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
