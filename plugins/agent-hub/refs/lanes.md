# Lanes
<Owner: rules/core.md § Routing>
<Read when: picking a lane, checking the fast-lane conditions or a review exemption, or adding an add-on spawn>

---

The lane table is in `rules/core.md § Routing`; this file holds the detail it cannot. Main thread takes the first lane that fits and never weighs two. A blocking status preempts any spawn order (`refs/gates.md`). An approved plan runs straight through: only the gates and a blocking status stop it.

## L0 answer

Nothing outside the conversation is touched: reading back what was said, asking the user, or a teaching, thinking or interview conversation the user asks for. Main thread answers.

## L1 fast

Main thread sends the request straight to `implement` only when all four hold: (1) at most 5 files; (2) the user's message already says what to change; (3) nothing `rules/core.md § Ask, never guess` lists as must-ask (business rule, end-user copy, deleting data, migration, production deploy, secret); (4) no shared route, schema or contract changes. One in doubt: the normal route. Implement runs a light check (syntax or type check of the changed files), appends one bypass record `pattern: fast-lane` (`refs/gates.md § Bypass record`) and writes the adhoc record from `templates/adhoc/adhoc-record-template.md`. No brainstorm, review or test; main thread edits nothing itself.

## L2 small

A feature or bug of at most 6 files with no contract or shared-symbol change: brainstorm, implement (`mode=simplify` as its last step), then `reviewer` and `test` in parallel over one frozen state, then the final gate (order and owners: `refs/closeout.md § End of a run`). No plan files and no approval gate unless brainstorm raises `approval_required`. A bug starts at brainstorm (root cause); implement applies the analysed fix and diagnoses nothing. After `Approve`, on the user's word, `devops` pushes the branch and opens the MR; the user merges.

## L-cfg no-plan

The lane row is in `rules/core.md § Routing`. Brainstorm returns the design and numbered steps in its record under `docs/changes/<id>/` of the `.claude` workspace; scope travels as `binding_scope`, rulings in the handoff and the ledger. No plan files, plan gate or stamp. The approval gate fires for a structural change only. Structural means the change adds, removes, renames or merges a file under `agents/`, `skills/`, `commands/`, `hooks/`, `refs/`, `rules/` or a store row; or changes who does what (a role's duty, a lane row, a gate, a status, a `needs_*` flag, a spawn order); or adds, removes or inverts a must / must not / only when sentence. Wording that keeps the meaning, a pointer or path, a number a check verifies, an example, or a duplicate cut to a pointer is not structural.

## L3 planned

Every other project: complex, more than 6 files, cross-system, or a contract, route or schema change. Brainstorm runs clarify, candidates, the approval gate, then writes the plan (`refs/plan-lane.md`). Before the plan gate only machines read it: `agent-hub check plan openspec/changes/<change>`, which runs `openspec validate --strict` itself (`refs/plan-lane.md § Checks before the gate`); no reviewer reads a plan. Then the end-of-run sequence of `refs/closeout.md § End of a run`: implement per wave, one `implement mode=simplify` that ends with the closeout, `test` and one `reviewer` pass blind to the plan, the final gate, archive after `Approve`.

## L-inv

A question, lookup or root-cause only; no file edit. Brainstorm, with `scout` per `recommend_scan[]` entry; the synthesising brainstorm runs in a later wave than the scan wave.

## L-ops

Anything leaving the working tree goes to `devops`, whatever the size: SSH, deploy, rollback, restart, `docker`/`kubectl` on a host, host logs, DNS, certificates, a migration against a deployed database; at a plan's end, branch integration, the PR and worktree cleanup. An implement run that needs a deploy returns `needs_devops`. The user's yes comes before each irreversible step.

# Spawning

Parallel when `depends_on` is empty, all in one message; sequential otherwise.

**No-spawn fallback.** `Agent` unavailable, or a session started with AGENT_HUB_DIRECT=1: main thread does the work and records the limitation under `Risk`. Never invent a worker's output.

# Add-ons

| Flag | Effect |
|---|---|
| `needs_design` | a `designer` wave, then brainstorm `mode=design-followup`. FE only: a new screen, flow or component, a layout or visible-behaviour change, a design-system migration. Copy of at most 2 strings, internal state logic and a CSS bug with no design decision go to implement; designer states an API constraint, brainstorm fixes the shape |
| `recommend_scan[]` | one scout per entry, then brainstorm again with `scout_results_refs[]` |
| `needs_repro` | the stated command is run by `test mode=script`, output passed back verbatim |
| `needs_prototype` | implement in a throwaway worktree, then brainstorm; no gate, at most one per change |
| `second_opinion_request[]` | specialists and/or Codex, one spawn each (`refs/roles/reviewer/second-opinion.md`) |
| a red result | brainstorm `error-batch`, implement, retest (`refs/error-loop.md`) |

# Reviewer exemptions

Every run with an `implement` spawn gets one code review beside `test`, after the last implement spawn. Three exemptions, none inferred: (1) `skip_review: true`, set by brainstorm from the kind of edit; in `~/.claude` only for at most 3 changed lines (python `difflib`, each non-equal opcode counting max(removed, added)) that are a spelling fix, a path, a pointed-to line number or a number `python3 tools/check.py ruleset` (agent-hub repo only) checks; a change to who does what, must / must not / only when, or a rule added or removed is reviewed at any size; (2) docs-only with no code surface (in `~/.claude`, files under `docs/`); (3) a hotfix where the user said "ship without review", phrase verbatim. A taken exemption is a bypass record.

# Edge cases

- **Partly green wave:** run the next wave for tasks that do not depend on the failed one; a failed task that wrote a shared contract, schema, route or migration stops the whole wave. A run with a red task closes `partial`.
- **Reviewer and implement disagree:** one exchange with evidence, then `needs_user_decision`; a `security` finding stands until the user clears it.
- **A contract across repos:** brainstorm covers every consumer; one change, tasks tagged per repo; the tolerant side ships first (consumer, producer, consumer drops the old shape).
- **Hotfix:** cap of 1 loop; a second smoke failure stops with `hotfix_breaker: true`, rollback first. Devops names the rollback before the first patch ships.
- **Returns:** read each parallel return and the conflicts between them; read "done with concerns" first; resume `in_progress` from `remaining_task_ids[]`, never restart.
