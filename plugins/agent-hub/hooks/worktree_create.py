"""WorktreeCreate hook: print the path of an isolated agent worktree.

A git repo gets a real `git worktree` (detached at HEAD, uncommitted work carried over); anything else
gets a plain copy of the source tree. node_modules is cloned per OS only when every lockfile matches.
"""
import filecmp
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _common  # noqa: E402
from _paths import config_dir  # noqa: E402

LOCKFILES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb")
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", ".nuxt", "coverage", ".turbo", ".cache"}
NOT_CLONED = "worktree-create: node_modules not cloned (%s); run the lockfile install"


def warn(msg):
    sys.stderr.write(msg + "\n")


def worktree_root():
    return config_dir() / "worktrees"


def git(cwd, *args, **kw):
    return subprocess.run(["git", "-C", str(cwd)] + list(args), capture_output=True, **kw)


def is_git_repo(path):
    try:
        return git(path, "rev-parse", "--git-dir").returncode == 0
    except OSError:
        return False


def find_node_modules(root, maxdepth=4):
    """node_modules directories under root, not descending into them, at most maxdepth levels like `find`."""
    found = []
    root = str(root)
    for cur, dirs, _files in os.walk(root):
        depth = 0 if cur == root else cur[len(root):].count(os.sep)
        if "node_modules" in dirs:
            if depth + 1 <= maxdepth:
                found.append(os.path.join(cur, "node_modules"))
            dirs.remove("node_modules")
        if depth + 1 >= maxdepth:
            dirs[:] = []
    return found


def clone_command(src, dst, system=None):
    """The per-OS copy argv, or None where the copy is done in Python (Windows and unknown systems)."""
    import platform
    system = system or platform.system()
    if system == "Darwin":
        return ["cp", "-c", "-R", src, dst]
    if system == "Linux":
        return ["cp", "--reflink=auto", "-R", src, dst]
    return None


def clone_dir(src, dst):
    """Copy one node_modules tree; True on success, False after cleaning a partial copy."""
    argv = clone_command(src, dst)
    try:
        if argv is None:
            shutil.copytree(src, dst, symlinks=True)
        else:
            proc = subprocess.run(argv, capture_output=True, text=True)
            if proc.returncode != 0:
                raise OSError(proc.stderr.strip() or "copy command failed")
        return True
    except (OSError, shutil.Error) as exc:
        warn("worktree-create: %s" % exc)
        shutil.rmtree(dst, ignore_errors=True)
        return False


def lockfiles_match(root, target, modules):
    dirs = {Path(nm).parent for nm in modules} | {Path(root)}
    for d in dirs:
        rel = d.relative_to(root)
        for lf in LOCKFILES:
            a = d / lf
            if a.exists() and not (Path(target) / rel / lf).exists():
                return False
            if a.exists() and not filecmp.cmp(a, Path(target) / rel / lf, shallow=False):
                return False
    return True


def clone_modules(root, target):
    modules = find_node_modules(root)
    if not lockfiles_match(root, target, modules):
        warn(NOT_CLONED % "lockfile differs")
        return
    for nm in modules:
        rel = os.path.relpath(nm, root)
        dst = Path(target) / rel
        if not dst.parent.is_dir() or dst.exists():
            continue
        if not clone_dir(nm, str(dst)):
            warn(NOT_CLONED % "copy failed")


def sweep_markers_and_cap(base, name, project):
    """Delete orphan markers, then refuse (return False) when the cap of live worktrees is reached."""
    for m in base.glob(".*.complete"):
        if not (base / m.name[1:-len(".complete")]).is_dir():
            m.unlink(missing_ok=True)
    raw = os.environ.get("CLAUDE_WORKTREE_CAP", "3")
    if raw.isdigit():
        cap = int(raw)
    else:
        warn("worktree-create: CLAUDE_WORKTREE_CAP=%s is not a whole number; using 3" % raw)
        cap = 3
    live = [d for d in sorted(base.iterdir())
            if d.is_dir() and d.name != name and (d / ".git").exists() and (base / ("." + d.name + ".complete")).exists()]
    if len(live) >= cap:
        warn("worktree-create: refusing a new worktree, %d exist (cap %d):" % (len(live), cap))
        for d in live:
            warn("  %s" % d)
        warn("run: python3 %s --apply --repo %s --orphans %s"
             % (_common.plugin_root() / "scripts" / "worktree-sweep.py", project, base))
        return False
    return True


def carry_uncommitted(root, target):
    patch = git(root, "diff", "HEAD", "--binary").stdout
    if patch:
        res = git(target, "apply", "--whitespace=nowarn", input=patch)
        if res.returncode != 0:
            warn("worktree-create: could not apply uncommitted tracked changes; worktree is at HEAD.")
    listing = git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        f = os.fsdecode(raw)
        if f.endswith("/"):
            warn("worktree-create: skipped untracked directory %s" % f)
            continue
        try:
            dst = Path(target) / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            src = Path(root) / f
            if src.is_symlink():
                os.symlink(os.readlink(src), dst)
            else:
                shutil.copy2(src, dst)
        except OSError:
            warn("worktree-create: could not copy untracked %s" % f)


def archive_copy(src, target):
    Path(target).mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target, dirs_exist_ok=True, symlinks=True,
                    ignore=shutil.ignore_patterns(*SKIP_DIRS))


def main():
    base = worktree_root()
    src = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    raw = _common.read_stdin_json().get("name")
    if raw:
        name = _common.worktree_name(raw)
        if name is None:
            warn("worktree-create: refusing unsafe name '%s'" % raw)
            return 1
    else:
        name = "agent-%s-%d" % (time.strftime("%Y%m%d-%H%M%S"), os.getpid())
    target = base / name
    done = base / ("." + name + ".complete")
    if base.is_dir() and not sweep_markers_and_cap(base, name, src):
        return 1
    base.mkdir(parents=True, exist_ok=True)
    if Path(os.path.realpath(target)).parent != Path(os.path.realpath(base)):
        warn("worktree-create: refusing unsafe name '%s'" % raw)
        return 1
    if target.is_dir():
        if done.exists():
            print(target)
            return 0
        git(src, "worktree", "remove", "--force", str(target))
        shutil.rmtree(target, ignore_errors=True)

    if is_git_repo(src):
        root = Path(git(src, "rev-parse", "--show-toplevel", text=True).stdout.strip())
        add = git(root, "worktree", "add", "-q", "--detach", str(target), "HEAD", text=True)
        if add.returncode == 0:
            carry_uncommitted(root, target)
            clone_modules(root, target)
            done.touch()
            print(target)
            return 0
        warn("worktree-create: git worktree add failed (sandbox or permissions?); falling back to a copy.")

    archive_copy(src, target)
    done.touch()
    print(target)
    return 0


if __name__ == "__main__":
    _common.utf8_stdio()
    sys.exit(main())
