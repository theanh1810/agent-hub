# Plan files: the run files, and reading either format
<Owner: agents/planner.md § Role>
<Read when: writing a plan; reading one task of a plan, or writing its `status` or `result`; checking that a plan's files agree with each other.>

---

A plan is one `plan.yaml` holding its tasks inline, plus an overview in the reply language when that is not English. The folder it sits in holds the fixed set of § Run files and nothing else.

## Where a plan lives

`{plan_dir}` is a plan's folder, the one change folder `{workspace_root}/docs/changes/{plan_id}/`; every rule names plan files from there. In a code workspace the plan is the spec: the spec delta sits in that same folder.

| The plan is for | `{plan_dir}` |
|---|---|
| every workspace, one sub-repo or several, with or without `docs/specs/README.md`; a rule tree such as `~/.claude` too (not a workspace root, `refs/artifact-layout.md § 19.0`) | `{workspace_root}/docs/changes/{plan_id}/`, and `{workspace_root}/docs/changes/archive/{YYYY-MM-DD}-{plan_id}/` once closed (an archive made before the date prefix keeps `{plan_id}`) |

Planner writes a new plan where this table points; orchestrator resolves `{plan_dir}` once and passes it in every spawn brief. A reader uses `agent-hub locate` to find exactly one `plan.yaml` across active and archived layouts; none or two is a stop (`needs_revision` naming the paths). Every writer takes the files named in § Run files from `{plan_dir}` too: they sit beside the plan files, so a closed change archives as one folder.

A change folder holds the files of § Run files, which include the change files of `refs/change-files.md` § Files (a legacy change keeps `deltas/<context>/UC-XXX-{kebab-name}.md`). § Agreement reads only `plan.yaml`, `plan.<lang>.md` and, in a legacy plan, `tasks/`. Closing: `SDD.md § 3.1`.

## Run files

The one list of what a run writes into `{plan_dir}`: eight files and two folders. Every other rule points here and repeats nothing.

| Path | When it exists | Written by |
|---|---|---|
| `proposal.md` | always | brainstorm |
| `design.md` | always | brainstorm |
| `design.yaml` | always | brainstorm |
| `plan.yaml` | always; tasks are inline, each with its `status` and `result` | planner, then each task's own agent |
| `plan.<lang>.md` | only when the reply language is not `en` | planner, rebuilt at wave write-back |
| `errors.yaml` | always | brainstorm `error-batch` |
| `review.md` | always; every review round is one section (`refs/review-trail.md § Trigger and location`) | reviewer, test |
| `change-map.md` | always, regenerated after each task result | `agent-hub change-map` |
| `evidence/` | only when test images must outlive the run | test, reviewer |
| `specs/` | only with a spec layer | brainstorm |

The change-map JSON and the review packets are throwaway: they go to `{workspace_root}/.cm-tmp/{plan_id}/` (`refs/artifact-layout.md § 19.2`), never into `{plan_dir}`. A run of ordinary size writes these eight files and `evidence/`.

**Legacy runs.** A plan written before this set has `tasks/`, `reviews/`, `change-map.json` or `plan.vi.md`. Readers still read them (§ Legacy layouts); no rule writes a new one, and a file of the legacy set is never copied into a plan that lacks it.

## Legacy layouts

Data a workspace has not migrated stays where it is, and no rule recreates its folders.

- Readers accept `{workspace_root}/docs/plan/{plan_id}/`, `{workspace_root}/docs/specs/changes/{plan_id}/` and `{workspace_root}/docs/specs/changes/archive/` beside `docs/changes/`. `agent-hub locate` finds the one `plan.yaml` in any of them, and the `{plan_dir}` of an existing plan is the folder it found; a new plan is always written at `docs/changes/{plan_id}/`.
- A legacy root is never recreated: every write path comes from the `{plan_dir}` of the brief, never from an old path field a legacy plan carries.
- Inside a legacy plan folder the readers accept `tasks/{wave}/{id}.yaml` task files, `reviews/`, `change-map.json` and `plan.vi.md`, read only.
- An old path that no longer exists (a workspace moved by `agent-hub docs-migrate`) resolves through `{workspace_root}/docs/changes/MIGRATION-MAP.tsv`: `agent-hub locate --resolve PATH`.

## Two formats

| Format | Recognised by | Written for |
|---|---|---|
| single-file | no `tasks/` directory | every plan written under § Run files: tasks inline in `plan.yaml` |
| split (legacy) | `{plan_dir}/tasks/` exists | plans written before § Run files; read, never written new |

The `tasks/` directory is the only test, never a date, `plan_id` or file size. A legacy split plan is never converted, even when it moves. A **task record** is where one task's keys live: its block in `plan.yaml` (in a legacy split plan, its task file); a rule naming a task's `status`, `result`, `test_cases[]` or `review_checkpoint` means its task record.

## The plan layout

Nothing but the files of § Run files belongs in the folder (no amend-patch, `.bak` or version copy: a re-plan edits in place, `refs/roles/brainstorm/modes.md` § change-design, **Living files**). Task ids do not change. A subtask (`W1-T1a`) stays in its parent's task entry.

### The plan file

`plan.yaml` carries every top-level key of `templates/plan/plan-template.yaml`. Its `tasks:` is one entry per task: `id`, `wave` and `depends_on` first, then every other key of `templates/plan/task-template.yaml`, `status` and `result` included; the closeout entry carries `depends_on: [ALL]` (`skills/planning-dag/SKILL.md § Wave rules`). The plan-level keys change only on a re-plan before the plan gate (`Edit plan`: brainstorm `mode=change-design`, then planner); after approval only a task's `status` and `result` are written, each into its own entry. The closeout entry differs from the template only as that template's CLOSEOUT note says. A key added later beside `agent` (the adaptive-effort `tier`) goes into the task entry.

### How planner writes a design

`change_design.plan` (`refs/roles/brainstorm/modes.md § change-design`) carries each task's decisions, `depends_on` included. Planner copies the plan-level keys, writes one inline entry per task, then runs § Agreement and `agent-hub check plan` before returning.

### The legacy split layout

A legacy plan's `plan.yaml` is an index: `tasks:` entries carry exactly `id`, `wave`, `file`, `depends_on`, with `file` set to `tasks/{wave}/{id}.yaml`, and each task file holds the other keys. Readers take such a task from its file; nothing writes a new task file.

## Reading one task

| Format | Read |
|---|---|
| single-file | the task's block of `plan.yaml`, extracted with the lines below |
| split (legacy) | the task's index entry, for `depends_on`; then its task file, whole: the file is the task |

A spawn with several `task_ids` reads each in its turn; a task outside `task_ids[]` is never read. A missing task file, an index entry with no file, or a file with no entry is a stop (`needs_revision` naming the path); never fall back to the other format or read a neighbouring task.

The single-file read takes one block, not the whole plan (62-68% of a plan file is `result` blocks written after their task ran):

```bash
P={plan_dir}/plan.yaml
START=$(grep -nE "^( {2})?- id: {task_id}$" "$P" | cut -d: -f1)
IND=$(sed -n "${START}p" "$P" | sed -E 's/- id: .*//')
END=$(awk -v s="$START" -v i="$IND- id: " 'NR>s && (index($0, i)==1 || /^[a-zA-Z_]/){print NR-1; exit}' "$P")
sed -n "${START},${END}p" "$P"
```

**The indent is read, not assumed**: a template plan puts task entries at two spaces, a PyYAML dump at column 0; `IND` is the START line's indent, and the block ends at the next `- id:` at exactly that indent or the next top-level key (a task nests its own `- id:` entries deeper). **The `$` is load-bearing**: `- id:` also opens `waves`, `contracts` and `approach_variants`, so only the exact `task_id` anchored to end-of-line identifies a task. **START empty or multiple, or a block not ending at the START indent, is a stop**: another agent may be replacing the file, so re-read. This is a line read, not a parse, so it works on a plan failing `yaml.safe_load`.

## Writing status and result

A task's `status` and `result` go into its task record only; the mirror's `status`, step ticks and `Result` block are rebuilt from it in the wave write-back (`refs/closeout.md § Who writes it, and when`: who, when, which lock). In a legacy split plan the index is never part of the write. The `Result` block: `refs/closeout.md § The result in the mirror`; the record stays the only source of `result`.

## Agreement

A plan's files agree when the checks below hold. For a single-file plan: every task entry carries `id`, `wave` and `depends_on`, ids are unique, and item 4 holds against `plan.<lang>.md` when that file exists. For a legacy split plan all five hold. Planner runs this before returning (`agents/planner.md § Pre-write validation` row 8); auditor on every plan it reads.

1. every index entry's `file` exists and is `tasks/{wave}/{id}.yaml`;
2. every file under `tasks/` has exactly one index entry, and its `id` equals its file stem;
3. no task file carries `wave` or `depends_on`;
4. `plan.<lang>.md` names the same waves, task ids, subtask ids, statuses, acceptance criteria and test case ids as the index and task files — a wave whose write-back has not run may show older statuses and ticks, never newer;
5. every index entry carries exactly `id`, `wave`, `file`, `depends_on`.

```bash
python3 - {plan_dir} <<'PY'
import sys, os, glob, yaml
d = sys.argv[1]
idx = yaml.safe_load(open(f'{d}/plan.yaml'))['tasks']
have = {os.path.relpath(p, d) for p in glob.glob(f'{d}/tasks/**', recursive=True) if os.path.isfile(p)}
want = [e.get('file') for e in idx]
bad = [f'no file: {f}' for f in want if f not in have]
bad += [f'no entry: {f}' for f in sorted(have) if want.count(f) != 1]
for e in idx:
    if set(e) != {'id', 'wave', 'file', 'depends_on'}:
        bad.append(f"index keys: {e.get('id')}")
    if e.get('file') != f"tasks/{e.get('wave')}/{e.get('id')}.yaml":
        bad.append(f"path: {e.get('id')} -> {e.get('file')}")
    elif e['file'] in have:
        t = yaml.safe_load(open(f"{d}/{e['file']}"))
        if t.get('id') != e.get('id') or {'wave', 'depends_on'} & set(t):
            bad.append(f"keys: {e['file']}")
print(bad or 'agree')
PY
```

The script prints items 1-3 and 5; item 4 is read against `plan.<lang>.md`. A disagreement is a fix before planner returns and a finding for auditor, never a warning.

**Steps and checklist, gated**. `tools/check ruleset (package repo only)` `plan_steps_shape` runs the step part of item 4 on every plan outside its frozen list of the 25 pre-`steps[]` folders: each task record carries a non-empty `steps[]` with the step keys of `templates/plan/task-template.yaml`, an `action` of `edit`, `create`, `delete` or `run`, and an `expect` opening `exit N` or `rc=N` on every `run` step; `plan.<lang>.md` carries one `### n. <task_id> · ` heading per task and one `- [ ] n.m` or `- [x] n.m` line per step (`[x]` only where `done` is true); a legacy split plan's mirror also carries its proposal and design sections.

## Task sections of plan.<lang>.md

A **logic task** is one whose `touches` holds `screen`, `logic`, `api` or `state`. Its block shows all ten sections below; any other task shows A1, A2, A2b, A3, A7 and A10, plus A8 and A9 when its record has them. Planner renders each section from the key named and adds no fact. The labels below are the English names; the mirror renders them in the reply language.

| Id | Label | From the task record | Shown |
|---|---|---|---|
| A1 | `What changes` | `what`, and the `path` of each `files[]` entry | always |
| A2 | `Why` | `purpose`, and the ids in `covers_uc` and `covers_requirements` | always |
| A2b | `Out of scope` | `out_of_scope[]`, one line each; `None` when the key is absent or empty | always |
| A3 | `Before / After` | `before_after[]`, one row per aspect | always |
| A4 | `Changed logic` | `logic[]`, numbered | logic task |
| A5 | `Chosen approach and reason` | `approach`: `chosen`, `why`, and `cost` as what is given up | logic task |
| A6 | `Rejected alternatives` | `alternatives_rejected[]`: `option` and `why_not`, or `none_because` | logic task |
| A7 | `How it is checked` | `acceptance_criteria`, `test_cases`, `verification` | always |
| A8 | `New user-visible rules` | `user_visible_rules[]`: `rule` and its `ac` | when present |
| A9 | `Risks and open points` | `risks[]` | when present |
| A10 | `Steps` | `steps[]`: `file` and `why`, one tick line each; a step that creates a file over 100 lines lists one sentence per function | always |

After a task finishes, its outcome appears under that block in the mirror's `Result` section, shaped by `refs/closeout.md § The result in the mirror`.
