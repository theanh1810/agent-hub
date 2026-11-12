---
paths:
  - "**/*.py"
---
# Python

Mechanics only. Comments: `_discipline.md` §5. Naming, function shape, structure: `agents/implement.md`. The repo's `docs/CODE-STYLE.md` overrides anything here.

**Check for `pyproject.toml`, `setup.cfg` or `.ruff.toml` first.** Where a formatter is configured it owns layout.

---

## Layout and imports

PEP 8 unless the repo says otherwise; run `black` or `ruff format` on the touched files only. Import order: stdlib → third-party → local, a blank line between groups, no wildcard imports (`from .models import *` never). Import modules rather than every symbol when the module name adds context. **No import-time side effects**: a module that opens a connection or reads a file on import cannot be tested.

## Types

- Annotate public function signatures; skip obvious locals.
- Add `Optional[T]` (or `T | None`) only where the `None` is real and handled, never to silence a checker.
- Prefer `dataclass` (or `pydantic` where the repo uses it) over a dict with known keys.
- Run whatever checker the repo configures; do not introduce `mypy` in an unrelated task.

## Errors

- Raise a specific exception, never bare `Exception`; define the module's own class once and export it.
- `except Exception:` needs a reason and must not swallow: log with context and re-raise, or handle a named failure. Bare `except:` also catches `KeyboardInterrupt` and is forbidden.
- `raise ... from err` when re-raising, so the original traceback survives. Clean up with a context manager, not hand-written `try/finally`.

## Mutable state

- **No mutable default argument** (`def f(items=[])` shares one list across calls): use `None` and build inside.
- Return a new list or dict; mutate a caller's only when the function name says it does.
- A module-level mutable global is shared state; where the repo has none, pass the state as an argument instead of introducing the first.

## Async

Do not mix `asyncio` with blocking calls: a blocking `requests` call inside `async def` stalls the loop. Use the async client the repo has, or run it in an executor and say why.

## Tests

- `pytest`, files `test_*.py` under `tests/unit/` mirroring the package, or the repo's recorded layout (`code-style/README.md` § Test layout).
- Names state behaviour (`test_returns_none_when_value_is_empty`, not `test_1`); `pytest.mark.parametrize` for boundary tables (it makes `_discipline.md` §2 cheap); fixtures over `setUp`; no network and no real database in a unit test.
- Where the task has an AC, the test name or its docstring carries both ids — `UC-042 / AC-2`.

## Untrusted input

- `yaml.safe_load`, never `yaml.load` with the default loader.
- Parse data from a file, request or another process with a data-only format (`json`, `yaml.safe_load`); never `pickle.loads`, `eval` or `exec` on it.
- `subprocess` takes a list of args with `shell=False` (the default), never a string built from input with `shell=True`.

## Resources

Open files, sockets and connections with `with`. Test membership on a `set` or `dict`, not a `list`, when the lookup runs in a loop.

## Scripts

A script reading a secret takes it from the environment and **fails closed** when missing (a default credential is how a key reaches a repository):

```python
key = os.environ.get("SERVICE_KEY")
if not key:
    raise SystemExit("SERVICE_KEY not set")
```

Fail on a missing key as above; never `os.environ.get("SERVICE_KEY", "sk-...")`.
