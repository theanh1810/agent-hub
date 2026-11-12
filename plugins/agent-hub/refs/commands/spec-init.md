---
description: "Internal reference read by /spec init (commands/spec.md) — not a standalone command; run /spec instead."
disable-model-invocation: true
---

# /spec init — detect, ask, then hand the writes to brainstorm
<Owner: commands/spec.md § init>
<Read when: `/spec init` runs, or `/spec scope` step 2 re-runs the detection of step 1 below. Paths resolve as the opening paragraph of `commands/spec.md` states.>

---

**Principle: Claude detects first, then asks with ready-made options; the user never types paths.**

Detection (step 1) and questions (step 3) run on main thread: read-only plus `AskUserQuestion`. Every write into `specs/` goes to `Agent(subagent_type="agent-hub:brainstorm")` with `mode=spec-init` and the user's answers; brainstorm owns behaviour specs and change files (`refs/change-files.md`, `SDD.md § Spec Layer`, `agents/brainstorm.md` § Artifact layout), and a business-rule answer is durable only once written into a file. Steps 2, 4, 5 and 6 inherit this.

1. **Detect before asking** (never ask before there is data):

```bash
# cwd = {workspace_root}. REPOS = every sub-repo with .git, or "." when the workspace root is the repo itself.
REPOS=$( { [ -e .git ] && echo .; for r in */; do [ -e "$r.git" ] && echo "${r%/}"; done; } | tr '\n' ' ')
echo "repos scanned: ${REPOS:-<no git repo>}"
# hot modules — paths that have a directory, prefixed with their repo so two repos never share a module name
for r in $(echo $REPOS); do git -C "$r" log --since=6.months.ago --name-only --pretty=format: | grep -v '^$' | grep '/' \
  | cut -d/ -f1-2 | sed "s|^|$r/|"; done | sort | uniq -c | sort -rn | sed -n '1,10p'
# flat repo (its line above returns nothing) → back off one segment
for r in $(echo $REPOS); do git -C "$r" log --since=6.months.ago --name-only --pretty=format: | grep -v '^$' \
  | cut -d/ -f1 | sed "s|^|$r/|"; done | sort | uniq -c | sort -rn | sed -n '1,10p'
for r in $(echo $REPOS); do ls -d "$r"/*/ "$r"/src/*/ 2>/dev/null; done | head -20   # directory structure
for r in $(echo $REPOS); do echo "$r $(git -C "$r" log -1 --format=%cd --date=short)"; done   # is each repo still alive
```

2. Create `specs/business-requirements/`, `specs/use-cases/`, `specs/entities/`, `specs/diagrams/`.

3. Ask via `AskUserQuestion`, where **the options are the real modules just detected**, each with its 6-month change count:

   - **Question 1 — "what is this product?"** Options: `New project` · `Existing system, still in development` · `Existing system, mostly maintenance`.
   - **Question 2 — "where to start?"** `multiSelect: true`. Options = the 3-4 hottest modules, each option stating its path + 6-month commit count + a guess at its business role. Add a `Whole product` option with a warning in `description`: a large denominator from day one means the metrics stay low for a long time and progress is hard to see.
   - Question 2 follows CLAUDE.md §17: every option states its consequence (the measurement denominator, the volume of spec to be written), not just the module name.

   New repo (`New project`): skip Question 2 and set `scope: full`; there is no git history, and the greenfield target is about 100% of the MVP.

4. Create `specs/README.md` from `${CLAUDE_PLUGIN_ROOT}/templates/spec/README-template.md`, filling in the adoption-baseline block from the answers:

```yaml
---
sdd_adopted: <today>
naming_convention_from: <today>
scope: partial            # or full
modules_in_scope:
  - <module the user chose>   # <sub_repo>/<path> as detected, workspace-relative
---
```

   Include an empty index table **and** a "Not yet specified" section — without that section the index lies about coverage.

5. **Pre-fill "Not yet specified"** with the hot modules not chosen in Question 2, each with its 6-month commit count: the counterweight against a narrow scope, so a module left out still shows evidence that it changes often.

6. Copy `_debt-template.md` → `specs/_debt.md`.

7. Existing system → suggest `/spec reverse <the module just chosen>` to reverse-engineer specs, instead of building specs for the whole product.

Create no UC at all during init.
