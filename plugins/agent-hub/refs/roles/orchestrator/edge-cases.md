# Edge cases — situations the routing table does not settle
<Owner: agents/orchestrator.md § Workflow>
<Read when: a wave came back half green · reviewer and implement disagree · a contract crosses repos · a hotfix patch failed smoke · work touches a server · placing the closeout wave · deciding whether a review spawn may be dropped>

---

## Why row 5 outranks row 6

A request both a cross-module feature and a new architectural component is `complex`. Under-classifying costs an approval gate, a planner pass and extended thinking on a change reaching shared code; over-classifying costs one planner run. The tie breaks toward `complex`; an ordered list, not weighing, makes two runs of one prompt agree.

## A wave that only partly succeeded (HARD)

Not failed, and not passed.

| Condition | Do |
|---|---|
| Nothing in the next wave `depends_on` the failed task | run the next wave for unblocked tasks; carry the failure as an open item, say in the handoff which tasks proceed without it |
| Something downstream depends on it | stop that dependency chain only |
| The failed task wrote a **shared** contract, schema, route or migration | stop the whole wave: a half-applied contract is worse than none |

The failure enters the error loop with its own count; other tasks passing does not reset it. A run is never Done while a task is red: close it `partial`, list the red tasks, say what is safe to ship without them.

## Reviewer and implement disagree (HARD)

1. Implement neither silently complies nor ignores: it answers in the handoff with evidence, `file:line`, and what the reviewer missed.
2. Reviewer withdraws (a normal outcome) or restates once, saying what the answer did not address.
3. One exchange, then stop: still apart → `needs_user_decision`, one paragraph per position, with a recommendation. Put the open point to the user instead of a third round; never run one, since two disagreements mean the requirement is ambiguous.

Exception: a `security` or `spec_drift` finding stands until the **user** clears it; implement may state disagreement, the code does not merge meanwhile.

## A contract that crosses repos (HARD)

- Brainstorm covers **every consumer**, not just the named repo; consumers that cannot be enumerated with evidence → `needs_user_input`.
- **One plan, one `plan_id`, tasks tagged per repo**; each repo gets its own reviewer pass.
- **The tolerant side ships first:** consumer accepts both shapes → producer switches → consumer drops the old shape once no traffic uses it. Three merges, consumer first; never producer first.
- Rollback names every repo, in reverse order.

## Hotfix circuit breaker (HARD)

Cap for `workflow=hotfix` is **1 loop**: patch 1 fails smoke → one `[main:brainstorm mode=error-batch]` → `[main:implement]` → `[main:test]` (smoke); patch 2 fails smoke → STOP with `status: needs_user_decision`, `hotfix_breaker: true`, rollback first and recommended.

- Devops names the rollback path (deploy or commit) **before** the first patch ships; with none, devops returns `needs_user_input` and does not deploy.
- Options: (1) roll back, then a normal `bug` with the full pipeline; (2) widen the patch scope, naming the extra files and why excluded; (3) mitigate without a code fix (flag off, traffic drained, job paused).
- When a hotfix looks like `complex` while production is down, say so and let the user choose; never promote it silently and start planning.

## Anything touching a server

- `devops` owns every action leaving the local tree: SSH/SCP/rsync · deploy, rollback, restart (`pm2`, `systemd`, `nginx`) · `docker`/`kubectl` on a host · host logs, health checks, disk and process inspection · DNS, certificates, host env or secrets · migration, backup, restore against a deployed database. A bug stays a bug; devops is the wave doing the server step.

## Closeout is the last wave (HARD)

Every run that produced a diff ends with **one** `closeout` spawn: `agent: implement`, `task_id: closeout`, `depends_on` every other task. Last because the spec sync needs test's `ac_coverage[]` and the reindex must see the final tree. Procedure: CLAUDE.md closeout section.

| Run shape | Where closeout goes |
|---|---|
| … implement → reviewer → test | a final wave after test |
| … implement → reviewer → test → devops | after **devops**, so the deploy SHA is in the record |
| `simple` / small `bug`, one implement, no plan | inline in that implement run |
| `hotfix` | inline; also logs `specs/_debt.md` |
| `problem-solving` / `docs` with no diff | none |
| `docs` with a real diff | inline in that implement run |

The more specific row wins (a hotfix that deploys keeps closeout inline); take the last row that describes the run. Never spawn closeout twice, never fold it into the last implement task when a plan exists.

## Reviewer after implement (HARD)

Every run with a completed `implement` spawn runs one code review, once, after the last implement spawn and beside `test`: `reviewer` `mode=independent` over the run's combined change minus exempt tasks. No final gate or summary until it returns. `mode=merge` is the MR review, not this. The fast lane runs no review. The rule binds an implement spawn main thread made directly as much as one orchestrator emitted.

Three exemptions, explicit, none inferred:
1. `skip_review: true` in the task (a plan task: `review_checkpoint.required: false` with one `focus` bullet naming the case). In `~/.claude` brainstorm sets it at change-design on a task changing ≤3 lines across all its files (python `difflib`, each non-equal opcode counting max(removed, added)) whose every changed line is a spelling fix, a path or pointed-to line number, or a number `tools/check ruleset (package repo only)` checks. An edit to who does what, must / must not / only when, or adding or removing a rule is reviewed at any size.
2. `target_area: docs` and the diff touches only `.md` / `docs/` / comments (in `~/.claude`, only files under `docs/`).
3. `workflow=hotfix` and the user said "ship without review": phrase verbatim in `post_spawn.skip_review_reason`.

An exemption taken is a Bypass record entry (`refs/roles/orchestrator/gates.md`). A run whose every implement task is exempt runs no review; `test` still runs.

| Rationalization | Reality |
|---|---|
| "The diff is small / obvious / just a typo" | Not an exemption; exemption 1 is set by brainstorm from the kind of edit, never claimed once the diff exists |
| "Implement said it self-checked" | Not an exemption |
| "The class is `simple`, so no reviewer" | The class is never an exemption |
| "A row omitting reviewer is a fourth exemption" | There are three |

A final gate asked or final summary emitted before the review returned appends `source: orchestrator-violation`, `pattern: reviewer-gate-bypass`, `implement_task_ids`, `wave_index` to the active `errors.yaml`. Auditor measures the ratio (`agents/auditor.md`).

**Brainstorm is mandatory** when the problem needs understanding before action: bug (root cause), feature (decompose), refactor (constraint discovery), problem-solving. **Skip brainstorm** for a trivial typo or one-line tweak, pure infra ops, docs-only: straight to `implement` or `devops`. UI-touching change → `test` mandatory.
