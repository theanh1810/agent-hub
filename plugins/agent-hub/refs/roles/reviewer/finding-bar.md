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
- What a claim carries: a contract, the `api_impact` result; a spec rule, the scenario name; performance, a number and its origin; duplication, the path already doing it; a severity, the rule that sets it. An absence claim lists what was checked (files, commands, patterns) or is dropped.
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
- **Spec silent on a behaviour**: report "spec missing" and ask (`needs_user_input`); reviewer does not decide a business rule (`rules/core.md § Ask, never guess`).
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

- A 🔴 or 🟠 finding carries `repro`: the shortest command or test sketch that fails on the current code, written from reading and run only when the brief carries `repro: true`. The fix round turns it into its failing test (`refs/roles/implement/sources.md § Fix round`).
- Every round after a fix (`round` 1 and later; the first pass is `round` 0) reviews only the fix's diff plus one hop from it (the direct callers and callees of each changed symbol): each earlier finding is ADDRESSED or NOT ADDRESSED, plus anything newly broken in that reach.
- The brief of such a round carries `triaged_findings[]`, every finding an earlier round already settled (fixed, deferred or rejected, with the reason); raise one again only with evidence the earlier round did not have, and name that evidence.
- A finding outside that reach is debt at any severity: it is written to the review file under `Out of diff` with its severity and returned as a `minor[]` line opening `[out-of-diff 🔴|🟠|🟡]`, so the ledger files it and no fix round opens; the user sees it at the final gate.
- A 🟡 minor goes to the run's ledger (`deferred_errors[]` of `errors.yaml`, written by `agent-hub ledger` with no brainstorm spawn); it never enters a fix round and never blocks close; the user sees the ledger once at the final gate.
- The review file carries every finding: each 🔴 and 🟠 in full and every 🟡 as one line (`file:line — what — fix`), none left out. The return carries each 🔴 and 🟠 in full and the 🟡 ones in `minor[]`, at most 10 lines: the 10 with the most impact when there are more, with the number left out and the review file's path stated in `summary`. A `security`-category finding of any severity and an `[out-of-diff]` line are always returned and stay outside that count.

## Review shape

The review opens with the verdict (user, 2026-10-26), not a preamble.

- Each line is a verdict, a finding with `file:line`, or something checked. No lead-in, no process narration, no closing summary.
- Right after the verdict a `Not checked` line names what could not be read or run. Nothing to fix: "All fine, nothing to fix" plus one line on what was checked.
- Input: the diff arrives as one file (commit list, stats, full diff with context), read once; do not rerun git. Open code outside the diff only to check a named risk, and state the risk and what was checked. The start point recorded before the work went to implement is the diff base, never `HEAD~1` (it truncates multi-commit tasks).

## The review file

Vietnamese, per `refs/review-trail.md`: a task diff of 50+ lines always gets a file; a conformance review carries the per-AC table (the reviewer's own judgement after opening the evidence, not a copy of `result`) and a per-hunk explanation of changes (default on: high-risk files in detail, the rest summarised); `learning: true` adds `## What was learned` with 1-3 sourced bullets; `INDEX.md` gets one row per review (a run of 🟠 means quality is slipping). Location: `agents/reviewer.md` Workflow step 6; a plan's reviews are the `## Round {n} · {kind}` sections of the change folder's `review.md` (`refs/review-trail.md § Trigger and location`), a round is appended and never rewritten, and a later round lists only what the fix round touched; a legacy plan's `reviews/` folder is read only. Red findings go to brainstorm `mode=error-batch`, never `errors.yaml` directly. Where a recurring pattern is saved: `skills/review-checklist/SKILL.md`.

## Additions from other packs

<!-- vendored:begin id=as-n6 src=addyosmani/agent-skills@39b723ceebf81474d0557c1fecd01eddab585563:skills/code-review-and-quality/SKILL.md#L88-L101 licence=MIT -->
## Structural Remedies

When you flag a structural problem, propose the move — not just the problem. A review that only says "this is complex" leaves the author guessing. Reach for a named restructuring:

- **Replace a chain of conditionals** with a typed model or an explicit dispatcher.
- **Collapse duplicate branches** into a single clearer flow.
- **Separate orchestration from business logic** so each reads on its own.
- **Move feature-specific logic** out of a shared module into the package that owns the concept.
- **Reuse the canonical helper** instead of a bespoke near-duplicate.
- **Make a type boundary explicit** so downstream branching disappears.
- **Delete a pass-through wrapper** that adds indirection without clarifying the API.
- **Extract a helper, or split a large file** into focused modules.

Prefer the remedy that removes moving pieces over one that spreads the same complexity around.
<!-- vendored:end id=as-n6 -->

<!-- vendored:begin id=as-n7 src=addyosmani/agent-skills@39b723ceebf81474d0557c1fecd01eddab585563:skills/code-review-and-quality/SKILL.md#L273-L281 licence=MIT -->
## Honesty in Review

When reviewing code — whether written by you, another agent, or a human:

- **Don't rubber-stamp.** "LGTM" without evidence of review helps no one.
- **Don't soften real issues.** "This might be a minor concern" when it's a bug that will hit production is dishonest.
- **Quantify problems when possible.** "This N+1 query will add ~50ms per item in the list" is better than "this could be slow."
- **Push back on approaches with clear problems.** Sycophancy is a failure mode in reviews. If the implementation has issues, say so directly and propose alternatives.
- **Accept override gracefully.** If the author has full context and disagrees, defer to their judgment. Comment on code, not people — reframe personal critiques to focus on the code itself.
<!-- vendored:end id=as-n7 -->

The phrase "no case, no finding" below is the one the finding bar above already uses, credited here. A shortcut marker follows `refs/roles/implement/close-task.md` § Shortcuts.

<!-- vendored:begin id=pt-n12 src=DietrichGebert/ponytail@96608e078b2d5ea607c5c3b8b5a54d1c1fba6846:skills/ponytail-review/SKILL.md#L30-L67 licence=MIT -->
## 2. Look for

1. **Bug:** wrong result, crash, missed edge case (empty, zero, last item,
   rounding, time zones), a caller broken by the change, a fix applied in one
   caller while the shared function stays broken.
2. **Risk:** security holes (injection, weak randomness, secrets, missing
   checks on input from users), data loss (errors swallowed, writes in the
   wrong order, no transaction).
3. **Scale:** fine for one user, wrong for many: check-then-write races, the
   same work done by every process, memory or lists that only grow, a query
   per item, O(n^2) on big input, per-process state that must be shared.
4. **Missing test:** risky new logic (a branch, a parser, money, security,
   data writes, a bug fix) with no test that fails when it breaks. One good
   test, not coverage.
5. **Speed:** big slowdowns are problems. Small wins (work repeated in a hot
   loop) are suggestions; some software counts every millisecond.
6. **Lean:** code that should not exist or should be smaller.
   - delete: dead code, unused options, speculative features
   - reuse: the repo already has this helper (name the path)
   - stdlib / native: the standard library or platform already does it; a
     new dependency for a few lines
   - yagni: abstraction with one implementation, config nobody sets
   - merge: near-copies that must change together
   - split: one function doing several unrelated jobs, so it is hard to read
     or test. Split by job, never by line count, and never into helpers that
     exist only to make a function shorter.

## 3. Check before you report

- Every finding needs a concrete case: "this input or situation leads to this
  wrong result". No case, no finding.
- Re-read the lines and confirm: the caller exists, the value can really be
  empty, the code really is unused.
- A shortcut marked with a `shortcut:` (or older `ponytail:`) comment that names its limit is a
  decision, not a finding, unless the expected load already crosses it.
- Propose the smallest fix that works. Prefer fixes that delete code. Never
  add layers, frameworks or config the problem does not need.
- No style taste, no "consider", no vague worries.
<!-- vendored:end id=pt-n12 -->
