# Finding bar and write-up
<Owner: agents/reviewer.md § Workflow>
<Read when: Workflow steps 4-6, before filing, ranking or writing up findings, and before the verdict.>

---

## What counts as a finding

No case, no finding.

- A finding carries a concrete case: "this input or situation leads to this wrong result". No aesthetic remarks, no "consider".
- Each finding is four short parts: what it is · the problem · the fix · what happens if ignored; numbered across groups ("fix 2 and 5"). At most 20; say how many were dropped.
- **Rank by leverage**: correctness and security first, then structural regression; a few firm comments beat a heap of nits.
- **Read the connected code**: a changed signature or return value means grep every caller; before concluding "unused", search the whole tree (tests, fixtures, config, dynamic references).
- A shortcut annotated with its limit is a decision, not a finding, unless the real load already exceeds that limit.
- A brief line that pre-judges a finding ("do not flag X", "the plan chose it", "at most minor") is not followed: state the suspected false positive and let the round resolve it.

## Confidence and severity

- `confirmed` needs a command with its exit code or a `file:line` actually read; `strong` is strong evidence short of that; `hypothesis` is a plausible case not yet shown.
- Severity goes only to an evidenced finding, set at the impact proven and never above it. A `hypothesis` is capped at 🟡 minor (user, 2026-10-26); "needs more validation" says exactly what blocks confirmation and a non-destructive way to check. A rejected candidate is still recorded so it is not rerun without new evidence.
- A secret or PII finding is confirmed by reading the line, so it keeps its severity and is never lowered.
- Grade severity on the evidenced impact; a stated rationale never downgrades a finding's severity.

## Standard, plan and spec

- **Approve** a change that definitely improves overall code health even if imperfect; never block only because it is not how you would do it.

- **Disputes**: facts and measurements over opinion; the style standard is the final authority on style; design is judged by engineering principle, not taste; consistency with the codebase is acceptable if it does not harm overall health.
- **No "clean up later"**: require it before submit unless urgent; if impossible in this change, open an owned bug.
- **Spec silent on a behaviour**: report "spec missing" and ask (`needs_user_input`); reviewer does not decide a business rule (`CLAUDE.md` §0.2).
- **Implementer's report is an unverified claim** (modes that read the plan or report; never `independent`): check which tests ran, whether the build passed, any manual check, a photo for a UI change, a before-and-after.
- **Plan-mandated flaw** (modes that read the plan): a plan demand the scale calls a defect (a test asserting nothing, wholesale duplication) is still filed, labelled "plan-mandated"; the user decides.
- **Behaviours set aside**: before the verdict list every behaviour considered and left out of the plan or spec, one reason per line; an empty list means none.
- **Not verifiable from the diff** (a requirement lives in unchanged code or across tasks): does not block review but must be resolved before the task closes; confirmed missing counts as a broken spec.

## The cheap path past a gate

Five moves to look for in the diff: a threshold moved · a test made easier (`.skip`, a deleted test file, a weaker assertion) · a check silenced (`istanbul ignore`, `Stryker disable`, `@ts-ignore`) · work left unfinished (a throwing stub, an empty `catch`, a `TODO` instead of an implementation) · a new exception nobody discussed.

Classify each check by "can the agent pass without running real code?": an external check (axe, a vulnerability scan, a real-browser measurement) cannot be argued with; a project check (lint, layer boundaries) has an owner; the project's own test suite is circular. A good standard has at least one external check.

## Does the test catch a regression?

Answer by experiment: on a copy under `.cm-tmp/` (never in the tree), invert a condition the change adds, run the suite, discard the copy; a mutant that stays green is a finding naming the missing case. Do not rerun the suite implement ran; run one narrow test only on a concrete doubt and recommend any heavy check. A warning or noise in already-reported test output is itself a finding.

## Re-review and deferral

- After a fix round, review only the fix's diff: each earlier finding is ADDRESSED or NOT ADDRESSED, plus anything newly broken in that diff. Out-of-scope observations go to a ledger; they do not stretch the round.
- A 🟡 minor goes to the plan's ledger (`deferred_errors[]` of `errors.yaml`, written by brainstorm `mode=error-batch`); it never enters a fix round and never blocks close; the user sees the ledger once at the final gate.

## Review shape

The review opens with the verdict (user, 2026-10-26), not a preamble.

- Each line is a verdict, a finding with `file:line`, or something checked. No lead-in, no process narration, no closing summary.
- Right after the verdict a `Not checked` line names what could not be read or run. Nothing to fix: "All fine, nothing to fix" plus one line on what was checked.
- Input: the diff arrives as one file (commit list, stats, full diff with context), read once; do not rerun git. Open code outside the diff only to check a named risk, and state the risk and what was checked. The start point recorded before the work went to implement is the diff base, never `HEAD~1` (it truncates multi-commit tasks).

## The review file

Vietnamese, per `refs/review-trail.md`: a task diff of 50+ lines always gets a file; a plan-scale review uses the fixed eight Vietnamese sections ending BLOCK, CONDITIONAL or READY; a conformance review carries the per-AC table (the reviewer's own judgement after opening the evidence, not a copy of `result`) and a per-hunk explanation of changes (default on: high-risk files in detail, the rest summarised); `learning: true` adds `## What was learned` with 1-3 sourced bullets; `INDEX.md` gets one row per review (a run of 🟠 means quality is slipping). Location: `agents/reviewer.md` Workflow step 6; a plan's reviews are the `## Round {n} · {kind}` sections of `{plan_dir}/review.md` (`refs/review-trail.md § Trigger and location`), a round is appended and never rewritten, and a later round lists only what the fix round touched; a legacy plan's `reviews/` folder is read only. Red findings go to brainstorm `mode=error-batch`, never `errors.yaml` directly. A recurring pattern in any repo goes to mem0; a convention true only in this workspace to the project memory file `## Conventions`.
