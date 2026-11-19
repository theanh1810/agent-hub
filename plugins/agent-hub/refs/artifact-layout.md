# Artifact layout and cleanup

<Owner: rules/core.md § Load when, row "writing a file">
<Read when: writing any file, and again at the cleanup gate; every agent that writes>

---

## Where the workspace root is

Artifacts live at the **workspace root**, one level above the code: `{workspace_root}` = `CODE_ROOT` + **exactly one segment** (`~/Code/acme`, never `~/Code` itself, never a repo one level deeper). `CODE_ROOT` resolves **argument > `$CODE_ROOT` env > `$HOME/Code`** (`plugins/agent-hub-auditor/scripts/run_auditor.py`, `error_stats.py`).

`openspec/`, `docs/changes/`, `docs/brainstorm/`, `docs/reviews/`, the decision-record folder under `docs/`, `docs/errors/`, `docs/audits/`, `docs/devops/` and `.cm-tmp/` all resolve from `{workspace_root}`; `openspec/changes/{plan_id}/` is `{plan_dir}`, a change's one folder, and `{plan_id}` is its name. Code and `docs/CODE-STYLE.md` stay in the sub-repo they describe. `openspec/specs/` is a product's whole spec layer, shared by its sub-repos; a bare `specs/…` in any rule file names `{workspace_root}/openspec/specs/…`.

**cwd outside `~/Code`** → ask the user **once**, proposing the parent of the nearest git root, and record the answer in `~/.claude/memory/MEMORY.md`. Never ask twice.

**`~/.claude` is not a workspace root**: its plans, reviews and analyses live under `~/.claude/docs/`, which no row below covers, so the `artifact_litter` signal of § Reviewer is the last net does not fire there; every other section binds there too.

**Paths stay flat.** A product with several repos does not nest: the repo name becomes a prefix (`plan_id` `acme-fe-aggregator-ws-refactor`, baseline `{repo}-{route_slug}`, the `{slug}` of `docs/brainstorm/` and `docs/changes/adhoc/`); a plan spanning repos takes the product as its prefix. Existing `plan_id`s are never renamed.

**Writing above cwd** runs with no prompt under `permissions.defaultMode: "auto"`; under `plan`, `acceptEdits` or `default` it needs `"additionalDirectories": ["<CODE_ROOT>"]` in the user's `settings.json` (not enabled by default).

## Where writing is allowed

Every path below resolves from `{workspace_root}` (§ Where the workspace root is) unless the row names another root. The seven that do not (two of them, `openspec/glossary.md` and `openspec/_debt.md`, resolve from the repo `openspec/` root): `docs/CODE-STYLE.md` belongs to the sub-repo it describes, `docs/design-library/` is pinned globally under `~/.claude/`, `~/.claude/logs/` holds the fleet's machine-wide logs, `templates/thresholds/` holds the master threshold file (global, one copy for every project), and `~/.claude-backups/` sits outside every workspace root on purpose (§ Ephemeral output).

| Path | Who | Lifetime |
|---|---|---|
| `{plan_dir}/proposal.md`, `design.md`, `tasks.md`, `specs/<capability>/spec.md`, `plan.vi.md` (`refs/plan-lane.md`) | brainstorm; implement ticks `tasks.md` | with the change; **exactly these**, living files edited in place, no `.bak` or version copy; `openspec archive` moves the folder under `archive/` |
| `{plan_dir}/approval.md` | main thread (`agent-hub stamp plan`) | with the change; the scope stamp and the user's words |
| `{plan_dir}/design.yaml` | brainstorm | machine record (`agents/brainstorm.md` § Artifact layout), moved here from `docs/brainstorm/{slug}.yaml` when `plan-write` assigns the id. Living |
| `{plan_dir}/diagrams/<n>-<slug>.html` | brainstorm; implement at closeout | one flow drawing (`refs/diagram.md`), rewritten in place, never copied; `openspec archive` moves it with the folder |
| `{plan_dir}/errors.yaml` | any | with the change; byte-exact, never compressed |
| `{plan_dir}/questions.md` | brainstorm | each clarify round's questions and the user's answers, written before brainstorm returns |
| `{plan_dir}/review.md` | reviewer · test | one file, one section per review round, earlier rounds kept (`refs/review-trail.md § Trigger and location`) |
| `{plan_dir}/reviews/annex-<n>.md` | main thread | a second opinion's result, beside `review.md` (`refs/gates.md`) |
| `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/reviews/annex-<n>.md` | main thread | a second opinion's result of a run with no plan, beside its `independent.md` (`refs/gates.md`) |
| `{plan_dir}/evidence/` | reviewer · test | only when images or logs must outlive the run: **at most 3 files** per task, only what a finding cites |
| `.cm-tmp/{plan_id}/` | implement · devops | throwaway outputs of a run: the review packets built by `agent-hub review-packet` as closeout's last command, fetched server logs; swept by the `after_approve` spawn (§ The cleanup gate) |
| `openspec/glossary.md` (else `docs/glossary.md`) | brainstorm | the project's terms, one file, living |
| `openspec/_debt.md` (else `docs/spec-debt.md`) | brainstorm · implement | spec debt, one file, living |
| `docs/reviews/baselines/{repo}-{route_slug}/{viewport}.png` | test | the only test output that survives; updated only after a green run |
| `docs/reviews/INDEX.md` | reviewer · implement | one appended row per review: reviewer with no plan, else the `after_approve` spawn |
| `docs/changes/<id>/` of the `.claude` workspace | brainstorm | the L-cfg design record: design and numbered steps, no plan files (`refs/lanes.md § L-cfg no-plan`) |
| `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/record.md` | implement (L1: main thread) · reviewer · test | the record of a run with no plan; `{slug}` starts with the repo name. Implement writes; reviewer appends `mode=task`, test its exploratory cases (`refs/roles/test/explore.md` § Results). Template: `templates/adhoc/adhoc-record-template.md` |
| `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/independent.md` | reviewer | own file: the adhoc record holds implement's six answers the independent layer never reads |
| `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/assets/` | reviewer · test | **at most 3 files**, only what a finding cites |
| `docs/changes/adhoc/{YYYY-MM-DD}-{slug}/diagrams/<n>-<slug>.html` | implement | the flow drawing of an L2 run (`refs/diagram.md`); outside `binding_scope`, as `record.md` |
| `docs/adr/` <!-- scrub-allow: product path --> | devops | with the workspace; only where there is no OpenSpec, otherwise a decision goes in the change's `design.md` |
| `docs/devops/` | devops | whole folder (`SERVER-INFO.md` and what it references) |
| `docs/brainstorm/{slug}.yaml` | brainstorm | the inbox, work with no change id: the record, `docs/brainstorm/{slug}/` for its extra files, rejected requests in `docs/brainstorm/rejected-requests.md`. Living files |
| `{plan_dir}/design/{slug}/DESIGN.md` | designer | **exactly one file**, images in `assets/`; with no change id, `docs/brainstorm/{slug}/design/DESIGN.md` |
| `{plan_dir}/design/{slug}/assets/` | designer | only the images `DESIGN.md` cites |
| `~/.claude/docs/design-library/{lib}/` | designer · implement | **global**; never copied per product or repo |
| `docs/audits/{YYYY-MM-DD}.md` | auditor | one per day |
| `docs/errors/{session_id}.yaml` | any | only when there is no change folder |
| `docs/deferred-backlog.md` | implement | written only by the `after_approve` spawn; with the workspace; one line appended per `deferred_errors[]` entry of a run on `Approve`, never rewritten; the user picks items into a new plan later |
| `{sub_repo}/docs/CODE-STYLE.md` | `/codestyle` · brainstorm · implement | with the sub-repo; style precedence #1 (`refs/code-standards.md`). Implement writes only its `Test layout:` line (+ heading and note if it creates the file, `code-style/README.md` § Test layout) |
| `~/.claude/logs/` | any | **global**; the cleanup gate does **not** touch it |
| `templates/thresholds/thresholds.yaml` | implement | **global**; the master copy of every vendor number this ruleset cites, grouped, each with its source; read per `refs/thresholds.md`, copied into a project only as `docs/thresholds.yaml` |
| `docs/thresholds.yaml` | implement | the project copy of the master: written at closeout when absent, each approved group stamped (`refs/thresholds.md`); with the workspace, edited in place |
| `.cm-tmp/{task_id}/` | any | **ephemeral**: deleted when the task closes, swept by the `after_approve` spawn |
| `~/.claude-backups/{plan_id}/{task_id}/` | any | **global, outside every workspace root**; the pre-edit copy and the review packet's no-git base, deleted by the `after_approve` spawn (L1: at its closeout); a fix round's copies of its `fix_list[].files[]` are `~/.claude-backups/{plan_id}/fix-r{round}/` |

Anything outside this table is not created unless the user named it. A decision record is 1-3 sentences and exists only when the decision is hard to reverse, surprising without its context, and a real trade-off. Template and numbering: `refs/rule-authoring.md` § ADRs.

Write each file in a folder the table above names. **Absolutely forbidden**: any file at a **sub-repo root**, or at `{workspace_root}` outside the folders above · a new top-level folder (`qa/`, `evidence/`, `tmp/`, `screenshots/`) · images, logs or dumps under `docs/changes/**` beyond the files listed · an invented path under `docs/`. Test code is not an artifact: `tests/` at a sub-repo root is where `code-style/README.md` § Test layout puts it.

## Ephemeral output

Screenshots, video, traces, HTML snapshots, network and console dumps, build and test logs, `playwright-report/`, `test-results/`, `coverage/` all go to `{workspace_root}/.cm-tmp/{task_id}/`.

A spawn with no `task_id` reads `{task_id}` in every `.cm-tmp/` and `evidence/` path as `{plan_id}-{wave_id}-{agent}` (`{agent}` its role, its `mode` for a missing `{wave_id}`); with no plan, `{session_id}-gate-{agent}`. No spawn builds a path from an empty or null id.

**Plan-scope runs.** The `test` and `reviewer` spawns after the last wave carry the round: `{plan_id}-r{round}-test`, `-test-heavy`, `-reviewer`, `-independent` (`refs/error-loop.md`). Each run deletes its own folder once every case or finding has a result, the `after_approve` sweep takes any left, and no round writes into another's.

**Checkpoint runs.** The `test` spawn of a checkpoint (`mode=script`, after a wave whose checkpoint the design names) writes under `{plan_id}-{wave_id}-checkpoint`; kept while its gate is RED (brainstorm `error-batch` reads it), deleted by the run whose gate is GREEN; one still present at `cap_reached` is deleted by the `after_approve` sweep.

**`.gitignore`.** Where the workspace root is inside a git repo, the first agent to create `.cm-tmp/` adds it to that repo's `.gitignore` (checking for a duplicate); where no git root sits at the workspace root, add the entry only in a sub-repo whose tree would show it.

**A pre-edit backup goes outside the tree it protects (HARD).** With no git history (`~/.claude`), copy a file to `~/.claude-backups/{plan_id}/{task_id}/` before editing, never into `.cm-tmp/`: a copy inside the tree answers `grep -r` and a citation lands on it (`rules/core.md § No invented rule`). The `after_approve` spawn deletes it (in L1, main thread at closeout step 5; `refs/closeout.md § End of a run`); left behind after that it is `artifact-litter`. With git, a parallel run uses a `git worktree`.

## The cleanup gate (HARD)

A task is **not done** until:

1. At most **3** cited images or logs are copied to `{plan_dir}/evidence/` with meaningful names (`alerts-empty-state.png`, never `dash-1.png`).
2. `shutil.rmtree` on the exact path `.cm-tmp/{task_id}`, while a `~/.claude-backups/{plan_id}/{task_id}` backup and its review snapshot stay until the `after_approve` spawn, in every lane with a final gate (`refs/closeout.md § End of a run`).
3. `git status --short` **inside each sub-repo this task changed, looping over them**, and the same for `detect_changes` (the workspace root is usually not a repo). Every `??` this task created is deleted, gitignored or deliberately committed.
4. The handoff says so: `cleanup: deleted N temp files, kept M at <path>`.

Skipping it is a workflow violation: log `pattern: artifact-litter`.

**Closeout sweep (HARD).** Deleted without asking, one `shutil.rmtree` per exact path (never a glob, so a lock directory survives): `{workspace_root}/.cm-tmp/{id}` for every task id and the `plan_id` of the closing change and every wave-end or round folder above; with no plan, every `implement`, `test` or `devops` spawn of the run plus `{session_id}-gate-test` and `{session_id}-gate-reviewer`. It runs only in the `after_approve` spawn, after the reviewer has read the packet and the user approved (`refs/closeout.md § End of a run`); in L1, which has no final gate, at closeout step 5. The same spawn deletes `~/.claude-backups/{plan_id}/<task id>` for every task id and `~/.claude-backups/{plan_id}/fix-r<round>` for every round, one exact path each. Kept, reason named: a folder holding a `*.lock` directory; a test folder holding `progress.yaml` (`refs/roles/test/resume.md` § Ending). `cleanup:` gives the count, the `du -sk` size before deleting, and each kept path.

**Worktree and litter sweep (HARD).** In the `after_approve` spawn (in L1, at closeout step 5), `agent-hub worktree-sweep --apply --repo <each changed sub-repo> --orphans ~/.claude/worktrees` removes a worktree only when its HEAD is reachable from a local branch or `refs/backup/wt/*` (a HEAD on neither is pinned there first), nothing uncommitted or ignored differs from the main worktree except build output, no process runs in it, and git removes it without force; it also deletes `.<name>.complete` markers of gone worktrees. Every `KEEP` line goes to `cleanup:` and the final reply; one kept for uncommitted files is named under `Risk`. Then `os.rmdir` an empty `.cm-tmp`, and delete the files under `.playwright-mcp/` the run modified (`os.rmdir` it when empty). No git: `worktrees: n/a - no git`.

This is the one cited exception to the must-ask on deleting data (`rules/core.md § Safety`): level 2, covering `.cm-tmp/` and a worktree passing the four conditions above. A `~/.claude-backups/{plan_id}/{task_id}` closeout did not make, and a branch, commit or worktree with unsaved work, stay level 1: list what would be lost and wait for the typed word.

## Naming and content

**Naming**: kebab-case, ASCII, no spaces, even when the contents are Vietnamese · the name describes the content, not the creation order (`login-form-validation-error.png`, not `test-3.png`) · **check the name after writing**: `$`, `{` or `}` means a variable never expanded, so delete, fix, rewrite · timestamps only when the file is one run (`YYYYMMDD-HHMMSS`; dates `YYYY-MM-DD`) · never `final`, `new`, `v2`, `latest`, `copy`, `backup`, `bak` or `test` as a version suffix (git keeps history) · a file belonging to a task is named for its `task_id`.

**Content**: one file, one purpose · where a template exists in `templates/`, read it rather than reconstructing it · files a person reads are Vietnamese with diacritics, machine-read and config files English; unaccented Vietnamese is a violation either way · every claim about code carries `file:line`, every figure its command · a long log or dump goes to its own file, referenced by path.

## Reviewer is the last net

Every review scans three signals, finding `artifact_litter`, 🟠: a new file outside § Where writing is allowed · an image, log or dump at a **sub-repo root**, at `{workspace_root}` (§ Where the workspace root is), or under `docs/changes/**` or `openspec/changes/**` · a filename containing `$`, `{`, `}`, or shaped `test-N` / `screenshot-N`.
