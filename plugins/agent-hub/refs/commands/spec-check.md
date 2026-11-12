---
description: "Internal reference read by /spec check (commands/spec.md) — not a standalone command; run /spec instead."
disable-model-invocation: true
---

# /spec check — the four metrics, and AC Coverage from three sources
<Owner: commands/spec.md § check>
<Read when: `/spec check` runs. Paths resolve as the opening paragraph of `commands/spec.md` states.>

---

**Mandatory step 0**: read the YAML block at the top of `specs/README.md` for `sdd_adopted`, `scope`, `modules_in_scope[]`.

No such block: print `N/A` for all 4 metrics and suggest `/spec init`. Print `N/A` instead of `0%`; never print `0%`: an old repo with unlabelled test names reads 0%, easily misread as "no tests".

Run directly: read-and-count work, no agent.

### AC Coverage — three sources, read in order

The plan declares tests at planning time: every task carries `test_cases[].covers_acceptance` as `UC-XXX/AC-N` (`plan.yaml`, or the task files of a split plan, `refs/plan-files.md`). Read the plan first and the test directory second; the other way round under-measures a test file that does not carry the UC-ID in its name yet.

| Priority | Source | What a hit means |
|---|---|---|
| 1 | The `Test mapping` table in the legacy UC | the agent wrote it back after the test ran — the most trustworthy source |
| 2 | `{workspace_root}/docs/changes/**/plan.yaml` and `…/tasks/*/*.yaml` (archive included), then, in a workspace on the legacy layout, `docs/specs/changes/` and `docs/plan/*/` the same way → `test_cases[].covers_acceptance` | this AC was planned to be covered |
| 3 | Test names in the source tree | a labelled test exists, but nobody wrote it back into the UC |

No source hits **and** the test directory is empty → **Missing test**.
No source hits **but** the test directory has files → **Not measurable** (tests exist, not labelled).

```bash
# cwd = {workspace_root} (commands/spec.md). REPOS = every sub-repo with .git, or "." when the workspace root is the repo.
REPOS=$( { [ -e .git ] && echo .; for r in */; do [ -e "$r.git" ] && echo "${r%/}"; done; } | tr '\n' ' ')
echo "repos scanned: ${REPOS:-<no git repo>}"

# misplaced spec root: a specs/ directory inside a repo is in the wrong place; the spec root is {workspace_root}/docs/specs/ (refs/artifact-layout.md § 19.0)
for r in $(echo $REPOS); do if [ -d "$r/specs" ]; then echo "MISPLACED: $r/specs/ — specs must live in $(pwd)/docs/specs/"; fi; done

# 1. adoption baseline
sed -n '1,12p' docs/specs/README.md

# 2. UCs that already have Acceptance criteria
grep -rlE "^## (Acceptance criteria|Điều kiện nghiệm thu)" docs/specs/use-cases/ 2>/dev/null | wc -l  # scrub-allow: legacy UC heading read when present

# 3. priority source 2 — ACs the plans declare as covered by a test: change folders under docs/changes (archive included), then the legacy docs/specs/changes and docs/plan
echo "plans scanned at: $(pwd)/docs/changes/ (and docs/specs/changes/, docs/plan/ when the workspace still has the old layout)"
find docs/changes docs/specs/changes docs/plan \( -path '*/tasks/*/*.yaml' -o -name plan.yaml \) -exec grep -hoE "UC-[0-9]+ ?/ ?AC-[0-9]+" {} + 2>/dev/null | sort -u

# 4. priority source 3 — discover the test dirs of every repo BEFORE grepping; do not hardcode `tests/`
TEST_PATHS=$(for r in $(echo $REPOS); do (cd "$r" && ls -d tests test spec __tests__ src 2>/dev/null | sed "s|^|$r/|"); done | tr '\n' ' ')
echo "scanned: ${TEST_PATHS:-<no test directory found>}"    # print it so we know where we measured
grep -rhoE "UC-[0-9]+ ?/ ?AC-[0-9]+" $(echo "$TEST_PATHS") 2>/dev/null | sort -u

# 5. tests exist but are unlabelled → tell "Missing test" apart from "Not measurable"
find $(echo "$TEST_PATHS") -type f \( -name '*.test.*' -o -name '*.spec.*' -o -name '*_test.*' -o -name 'test_*' \) 2>/dev/null | wc -l

# 6. Trace Ratio — needs BOTH numerator and denominator, summed over every repo
for r in $(echo $REPOS); do git -C "$r" log --since="<sdd_adopted>" --pretty=%s | grep -cE "\(UC-[0-9]+\)"; done | paste -sd+ - | bc   # numerator
for r in $(echo $REPOS); do git -C "$r" log --since="<sdd_adopted>" --oneline | wc -l; done | paste -sd+ - | bc                      # denominator
```

`$TEST_PATHS` reaches grep and find as `$(echo "$TEST_PATHS")` because zsh splits a command substitution but not an unquoted parameter, so each test dir is its own argument. Always print the `scanned:` line; never hardcode `tests/`.

Print every `MISPLACED:` line of the counting script first, verbatim, even when step 0 found no adoption block: a spec written inside a repo instead of `{workspace_root}/docs/specs/` is reported and left in place by `/spec check`, never moved — moving it is the user's call. Then print a table of the 4 metrics + denominator + threshold + one sentence reading out what it means. AC Coverage must be split into three states: **Tested** / **Missing test** / **Not measurable**. Thresholds and how to read them: `${CLAUDE_PLUGIN_ROOT}/rules/SDD.md` §8.1–8.3.
