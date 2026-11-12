"""Where the plugin lives and where the user's config lives, so no script assumes ~/.claude."""
import os
from pathlib import Path


def plugin_root():
    """The plugin folder: the parent of scripts/, wherever Claude Code installed it."""
    return Path(__file__).resolve().parents[1]


def config_dir():
    """The Claude Code config dir: CLAUDE_CONFIG_DIR when set and non-empty, else ~/.claude."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def lib_path():
    """The vendored pure-Python libraries (PyYAML), put on sys.path ahead of site-packages."""
    return plugin_root() / "lib"
