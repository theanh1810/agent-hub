---
name: codestyle
description: Use at the start of work on an unfamiliar repo, or when output style has drifted between sessions, to derive the repo's actual code conventions into docs/CODE-STYLE.md by measuring the codebase.
disable-model-invocation: false
argument-hint: [subpath to scope the measurement, e.g. src/services | debt | audit]
---

# /codestyle

Write `docs/CODE-STYLE.md` in the repo at cwd with measured conventions, so every session writes the same dialect. Precedence and loading: `${CLAUDE_PLUGIN_ROOT}/rules/code-style/README.md`; baselines: `${CLAUDE_PLUGIN_ROOT}/rules/code-style/<language>.md`.

## Rule (HARD)

Every output line is a count or a citation. "Prefer async/await" is an opinion and stays out; "async/await in 212 files, `.then()` in 3 (`file:line` x3): async/await is the convention, the three are drift" is a measurement. A genuinely split repo gets both counts under **Unresolved**; never pick a winner. A convention the code does not follow is left out, never written in.

## Steps

1. **Scope**: `$ARGUMENTS` if given, else the source root (`src/`, `lib/`, `app/`, or repo root). Exclude `node_modules`, `dist`, `build`, `vendor`, `coverage`, `.venv`, `__pycache__`, generated and migration directories; say what was excluded.
2. **Languages**: count files per extension; under 5% is listed, not profiled.
3. **Per language, with counts**:
   - module system (`require` vs `import`), import grouping and order from the 5 largest files, export style (named vs default, bottom statement vs scattered)
   - error types thrown (`grep -hoE "throw new [A-Za-z]+" | sort | uniq -c`), async style (`await` vs `.then()`)
   - casing per kind (files, directories, functions, classes, constants)
   - test location, naming and framework from real paths; an existing `Test layout:` line is the user's decision (`code-style/README.md` § Test layout): copy it verbatim
   - file length (median, 90th percentile, the 3 longest) and function length (median, count over 80 lines)
   - comments as a list, never a density: for each comment in the 5 largest files record `file:line` and its category of `${CLAUDE_PLUGIN_ROOT}/rules/code-style/_discipline.md` § Comments; one matching no category is drift, named under **Unresolved**, not counted
   - formatter and linter config, and which rules are off: a config that disables `no-unused-vars` enforces almost nothing
4. **Architecture in force**: layer rules from any `README.md` in the source tree, `docs/architecture/` or ADRs, verbatim with `file:line`; a HARD rule keeps its HARD label. In a TypeScript repo note whether module boundaries are machine-enforced (for example dependency-cruiser: internals hidden in subfolders, entered only through the package root file).
5. **Domain vocabulary**: from `specs/entities/` when it exists, else recurring nouns in model and schema files.
6. **Write `docs/CODE-STYLE.md`** in the shape below: prose in the user's language, English identifiers.
7. **Report** the path, languages profiled and every **Unresolved** split. Leave `docs/CODE-STYLE.md` for the user to commit.

## Output shape

```markdown
# CODE-STYLE — <repo>

Measured automatically on <YYYY-MM-DD> from <scope>, commit <sha>. Every line below is a **measurement**, not a preference. General guidance: `${CLAUDE_PLUGIN_ROOT}/rules/code-style/`. This file wins when the two differ. Re-run: `/codestyle`.

## Scope
Measured: … · Excluded: … · Total: N files
## Languages
| Language | Files | % |
## <Language> — measured conventions
| Item | Convention | Evidence |
|---|---|---|
| Module system | CommonJS | `module.exports` 290 file · `export` 0 |
## Architecture in force
- <rule, verbatim> — `<path>/README.md:12` — **HARD**
## Domain vocabulary
| Concept | Name used in code | Do not use |
## Inconsistent (Unresolved)
- <item>: A in N files, B in M files. Needs a human decision.
## What the linter really catches
- <rule that is off and its consequence>
```

## Argument `debt`

Collect comments marked `shortcut:` into a debt ledger with a "revisit" column; one stating no upgrade path or return condition is labelled `no-trigger` (those rot). End with "N marks, M without a revisit point". Writes only the ledger.

## Argument `audit`

One-shot, report-only: changes nothing, writes no flag file; the report is saved to a file only after asking.

## Forbidden

- A rule with no count or citation behind it; picking a side on a genuine split.
- Editing source, config or lint rules: the command writes only `docs/CODE-STYLE.md` (or the ledger of `debt`, or a report the user approved).
- Copying `${CLAUDE_PLUGIN_ROOT}/rules/code-style/*.md` into the output; committing; running a formatter.
