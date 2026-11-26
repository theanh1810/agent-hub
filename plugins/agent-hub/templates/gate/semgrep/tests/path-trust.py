import json
import os
import sys
from pathlib import Path

BASE = Path("data").resolve()


def flagged_argv():
    name = sys.argv[1]
    # ruleid: agent-hub-path-trust-python
    with open(BASE / name) as fh:
        return fh.read()


def flagged_json(raw):
    target = Path(json.loads(raw)["path"])
    # ruleid: agent-hub-path-trust-python
    target.write_text("x")


def flagged_lexical_only():
    target = BASE / os.environ["NAME"]
    target.relative_to(BASE)
    # ruleid: agent-hub-path-trust-python
    target.unlink()


def clean_resolved():
    target = (BASE / sys.argv[1]).resolve()
    target.relative_to(BASE)
    # ok: agent-hub-path-trust-python
    with open(target) as fh:
        return fh.read()


def clean_is_relative_to(raw):
    target = (BASE / json.loads(raw)["path"]).resolve()
    if not target.is_relative_to(BASE):
        raise ValueError("outside base")
    # ok: agent-hub-path-trust-python
    target.write_text("x")


def flagged_reads_and_dirs():
    target = Path(sys.argv[1])
    # ruleid: agent-hub-path-trust-python
    target.read_text()
    # ruleid: agent-hub-path-trust-python
    target.read_bytes()
    # ruleid: agent-hub-path-trust-python
    target.mkdir()
    # ruleid: agent-hub-path-trust-python
    os.makedirs(sys.argv[1])
    # ruleid: agent-hub-path-trust-python
    os.mkdir(sys.argv[1])
    # ruleid: agent-hub-path-trust-python
    target.replace(BASE / "kept")


def clean_reads_and_dirs():
    target = (BASE / sys.argv[1]).resolve()
    target.relative_to(BASE)
    # ok: agent-hub-path-trust-python
    target.read_text()
    # ok: agent-hub-path-trust-python
    target.read_bytes()
    # ok: agent-hub-path-trust-python
    target.mkdir()
    # ok: agent-hub-path-trust-python
    os.makedirs(target)
    # ok: agent-hub-path-trust-python
    os.mkdir(target)
    # ok: agent-hub-path-trust-python
    target.replace(BASE / "kept")


def clean_str_replace():
    # ok: agent-hub-path-trust-python
    return os.environ.get("PATHS", "").replace(":", ",")


def flagged_rename_destination():
    # ruleid: agent-hub-path-trust-python
    Path(BASE / "a").replace(sys.argv[1])
    # ruleid: agent-hub-path-trust-python
    Path(BASE / "a").rename(os.environ["DEST"])


def clean_rename_destination():
    dest = (BASE / sys.argv[1]).resolve()
    dest.relative_to(BASE)
    # ok: agent-hub-path-trust-python
    Path(BASE / "a").replace(dest)
    # ok: agent-hub-path-trust-python
    Path(BASE / "a").rename(dest)


def flagged_dataframe_rename_is_a_known_false_positive(frame):
    mapping = json.loads(sys.argv[1])
    # ruleid: agent-hub-path-trust-python
    frame.rename(mapping)
    # ok: agent-hub-path-trust-python
    return frame.rename(mapping)  # nosemgrep: agent-hub-path-trust-python - a DataFrame label mapping, not a path


def clean_rename_that_cannot_move_a_path(frame):
    mapping = json.loads(sys.argv[1])
    # ok: agent-hub-path-trust-python
    frame.rename(columns=mapping)
    # ok: agent-hub-path-trust-python
    frame.rename(index=mapping)
    # ok: agent-hub-path-trust-python
    frame.rename(mapper=mapping)
    # ok: agent-hub-path-trust-python
    frame.rename(mapping, axis=1)
    # ok: agent-hub-path-trust-python
    frame.rename({"a": os.environ["DEST"]})
    # ok: agent-hub-path-trust-python
    frame.replace({"a": os.environ["DEST"]})


def flagged_rename_destination_of_a_path_variable():
    source = BASE / "a"
    # ruleid: agent-hub-path-trust-python
    source.rename(os.environ["DEST"])


def flagged_rename_destination_of_a_resolved_path():
    src = Path("a").resolve()
    # ruleid: agent-hub-path-trust-python
    src.rename(os.environ["DEST"])


def flagged_rename_destination_of_a_parameter(src: Path):
    # ruleid: agent-hub-path-trust-python
    src.rename(os.environ["DEST"])


def flagged_rename_destination_in_a_loop():
    for p in BASE.iterdir():
        # ruleid: agent-hub-path-trust-python
        p.rename(os.environ["DEST"])


def flagged_rename_destination_of_derived_paths():
    # ruleid: agent-hub-path-trust-python
    BASE.joinpath("a").rename(os.environ["DEST"])
    # ruleid: agent-hub-path-trust-python
    BASE.with_suffix(".bak").rename(os.environ["DEST"])
    # ruleid: agent-hub-path-trust-python
    BASE.rename(os.environ["DEST"])


class Staging:
    def flagged_rename_destination_of_an_attribute(self):
        # ruleid: agent-hub-path-trust-python
        self.tmp.rename(os.environ["DEST"])


def flagged_rename_destination_by_keyword():
    # ruleid: agent-hub-path-trust-python
    src.rename(target=os.environ["DEST"])
    # ruleid: agent-hub-path-trust-python
    src.replace(target=os.environ["DEST"])
