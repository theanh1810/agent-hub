"""WorktreeRemove hook: remove a worktree this hook family created; refuse any path outside the worktree root (exit 2)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _common  # noqa: E402
from _paths import config_dir  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd)] + list(args), capture_output=True, text=True)


def refuse(name):
    sys.stderr.write("worktree-remove: refusing unsafe name '%s'; remove it by hand if it is yours.\n" % name)
    return 2


def rmtree(path):
    def onerr(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    shutil.rmtree(path, onerror=onerr)


def pin_head(target, name):
    """Save a HEAD no branch or backup ref contains, so the forced removal loses nothing."""
    if git(target, "for-each-ref", "--contains", "HEAD", "refs/heads", "refs/backup/wt").stdout.strip():
        return
    sha = git(target, "rev-parse", "HEAD").stdout.strip()
    ref = "refs/backup/wt/" + name
    if git(target, "rev-parse", "-q", "--verify", ref).returncode == 0:
        ref = "%s-%s" % (ref, sha[:7])
    git(target, "update-ref", ref, sha)


def main():
    path = _common.read_stdin_json().get("worktree_path")
    if not path:
        sys.stderr.write("worktree-remove: no worktree_path on stdin\n")
        return 0
    base = config_dir() / "worktrees"
    raw = os.path.basename(os.path.normpath(path))
    if os.path.realpath(os.path.dirname(os.path.normpath(path))) != os.path.realpath(base):
        return refuse(path)
    name = _common.worktree_name(raw)
    if name is None or name != raw:
        return refuse(raw)
    marker = base / ("." + name + ".complete")
    target = base / name
    if not os.path.lexists(target):
        marker.unlink(missing_ok=True)
        return 0
    try:
        real_base = Path(os.path.realpath(base))
        real_target = Path(os.path.realpath(target))
    except OSError:
        return refuse(name)
    if real_target == real_base or real_base not in real_target.parents:
        return refuse(name)

    if (target / ".git").exists():
        pin_head(target, name)
        common = git(target, "rev-parse", "--git-common-dir").stdout.strip() or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if git(target, "worktree", "remove", "--force", str(target)).returncode == 0:
            marker.unlink(missing_ok=True)
            return 0
        rmtree(real_target)
        git(common, "worktree", "prune")
    else:
        rmtree(real_target)
    marker.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main())
