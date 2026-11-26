---
description: "Internal reference read by /spec check (commands/spec.md) — not a standalone command; run /spec instead."
disable-model-invocation: true
---

# /spec check — scenario coverage from three sources, and Trace Ratio
<Owner: commands/spec.md § check>
<Read when: `/spec check` runs. Paths resolve as the opening paragraph of `commands/spec.md` states.>

---

**Mandatory step 0**: read the adoption block at the top of `openspec/scope.md` for `sdd_adopted`, `scope`, `modules_in_scope[]`.

No such block: print `N/A` for both metrics and suggest `/spec init`. Never print `0%`: an old repo with unnamed tests reads 0%, easily misread as "no tests".

Run directly: read-and-count work, no agent.

### Scenario coverage — three sources, read in order

A plan declares tests at planning time: every task's `Covers:` line names scenarios (`tasks.md`, `refs/plan-lane.md`). Read the plans first and the test directory second; the other way round under-measures a test that does not carry the scenario name yet.

| Priority | Source | What a hit means |
|---|---|---|
| 1 | test's `ac_coverage[]` recorded in the change's reviews | the test ran and was written back: the most trustworthy source |
| 2 | `{workspace_root}/openspec/changes/**/tasks.md` (archive included): the `Covers:` lines | this scenario was planned to be covered |
| 3 | Scenario names in test names in the source tree | a named test exists, but nobody wrote it back |

No source hits **and** the test directory is empty → **Missing test**. No source hits **but** the test directory has files → **Not measurable**.

```bash
# cwd = {workspace_root}. REPOS = every sub-repo with .git, or "." when the workspace root is the repo.
REPOS=$( { [ -e .git ] && echo .; for r in */; do [ -e "$r.git" ] && echo "${r%/}"; done; } | tr '\n' ' ')
echo "repos scanned: ${REPOS:-<no git repo>}"

# 1. adoption block
sed -n '1,12p' openspec/scope.md

# 2. requirements and scenarios in the live specs
grep -rc '^#### Scenario:' openspec/specs/ 2>/dev/null

# 3. priority source 2: the Covers lines of every plan, archive included
echo "plans scanned at: $(pwd)/openspec/changes/"
grep -rh '^ *Covers:' openspec/changes 2>/dev/null | sort -u

# 4. discover the test dirs of every repo BEFORE grepping; never hardcode tests/
TEST_PATHS=$(for r in $(echo $REPOS); do (cd "$r" && ls -d tests test spec __tests__ src 2>/dev/null | sed "s|^|$r/|"); done | tr '\n' ' ')
echo "scanned: ${TEST_PATHS:-<no test directory found>}"

# 5. tests exist but are unnamed → tell "Missing test" apart from "Not measurable"
find $(echo "$TEST_PATHS") -type f \( -name '*.test.*' -o -name '*.spec.*' -o -name '*_test.*' -o -name 'test_*' \) 2>/dev/null | wc -l

# 6. Trace Ratio: numerator and denominator, summed over every repo; the task id sits in the commit's `Refs:` line
for r in $(echo $REPOS); do git -C "$r" log --since="<sdd_adopted>" --pretty=%B | grep -cE "^Refs: .+ / .+"; done | paste -sd+ - | bc
for r in $(echo $REPOS); do git -C "$r" log --since="<sdd_adopted>" --oneline | wc -l; done | paste -sd+ - | bc
```

`$TEST_PATHS` reaches grep and find as `$(echo "$TEST_PATHS")` because zsh splits a command substitution but not an unquoted parameter. Always print the `scanned:` line.

Print a table of the two metrics, each with its numerator, denominator and one sentence reading out what it means: scenario coverage in three states, **Tested** / **Missing test** / **Not measurable** (the denominator is the scenarios of `modules_in_scope[]`; `rules/SDD.md § 8.2`), and Trace Ratio (step 6). No threshold is set, so print no pass or fail.
