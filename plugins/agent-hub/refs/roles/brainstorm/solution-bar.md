# Solution bar — what a candidate must clear
<Owner: agents/brainstorm.md § References>
<Read when: about to emit `candidates[]` (`agents/brainstorm.md` § Workflow step 5), and again at step 7 when looping. An `error-batch` run proposes no candidate and needs none of this>

---

**Every candidate clears all three bars (HARD).** One failing any is not a candidate: say so and produce another; never put a weak option beside a strong one to make it look chosen. Each carries `approach`, `files_estimate`, `risk`, `effort`, `tradeoffs`, `confidence`; none without trade-offs outside `quick` mode.

- **Minimum scope.** No feature, abstraction or configuration beyond the request: written in 200 lines when 50 would do, choose the 50. "Minimum code that solves the problem. Nothing speculative."
- **Different for real.** On complex work, generate genuinely different candidates through lenses: invert it, drop one constraint, change the audience, combine, simplify tenfold.
- **Design it twice under named constraints.** Each candidate is designed under a different named constraint (for example 'smallest interface', 'fewest moving parts', 'built for the one case that hurts'), not as a variation of one idea; the proposal names each candidate's constraint. Brainstorm spawns no parallel agent for this.
- The proposal names the key assumptions, the minimum scope and an **Out of scope / Not doing** list (what was removed this round, one line of reason each). Those items never become tasks on their own and return only when the destination is redrawn; a task proven outside the destination is closed with one line there. "Say no to 1,000 things."

## 1. It actually solves the problem

The root cause is removed, not the symptom. State which part of the cause each candidate addresses; when one leaves part standing, say which and why that is acceptable now. A named trade-off is allowed ("fixes the duplicate alert, does not fix the shared `fieldKey`, which needs a migration"); "fixes the alert issue" hides whether the cause was removed or masked. Every trade-off lands in `tradeoffs`, not a footnote.

## 2. It holds under the design principles

For anything touching a shared surface answer each ("not applicable" is valid, silence is not):

| Property | The question |
|---|---|
| Availability | What is unavailable while this ships, and for how long? |
| Fault tolerance | Dependency down, slow or garbage: fail closed, fail open, or corrupt state? |
| Recovery | How is it reversed in production: a revert, a flag, a migration in both directions? |
| Backup and data safety | Does it touch data that cannot be regenerated? Is there a backup that restores? |
| Idempotency | Run twice: same result or double effect? Retries and redeliveries are normal |
| Observability | At 3am, what does the operator see: a log line, a metric, nothing? |
| Blast radius | Who else breaks: one screen, one service, every consumer of a contract? |

A candidate whose failure mode is "we find out from the user" is not ready to recommend.

## 3. It is sound in structure, algorithm and pattern

- **Structure.** Which layer, and does it keep that layer's boundary? Leaking business logic into a controller because the bug surfaced there buys today at tomorrow's expense: say so if proposed anyway.
- **Algorithm.** For a collection, stream or repeated call: time and space complexity in the real input size (`O(n²)` on 30 rows is fine, on 4,000 it is the bug); access pattern (round trips, N+1, whether an index covers the scan); behaviour at ten times the input; a better-known structure where one applies (hash lookup over linear scan, heap over full sort, set over repeated `includes`) with its readability cost. Compare candidates on this axis: "both work" is not an analysis.
- **Pattern.** Follow the codebase's pattern, cited `file:line`; a new pattern carries the cost of teaching it and must be justified.

## Design vocabulary for module work

- Use exactly: module, interface (invariants, ordering, error kinds, configuration included), depth, seam, adapter, leverage, locality. "Use these terms exactly: don't substitute "component," "service," "API," or "boundary.""
- **Deletion test:** imagine deleting the module; complexity vanishing means a pass-through, reappearing at N callers means it earns its place.
- No direction for an architecture improvement → look at hot spots in commit history (files that change often); scan wide only when changes are spread evenly.
- Each improvement candidate carries a recommendation level (strong, worth trying, speculative) and "no new interface proposed before you choose".
- A candidate contradicting an existing ADR is raised only when the friction is real enough to reopen it, flagged ("contradicts ADR-0007, but worth reopening because…"); do not list every refactor an ADR forbids.
- The user rejects a candidate for a weighty reason → ask whether to record it in `docs/brainstorm/rejected-requests.md` (not proposed again) and, for an architectural choice, as an ADR in the project's ADR folder (`<docs>/adr/`). Skip transient reasons ("not worth it right now").

## Removing an old system

- Only when a replacement runs in production. First answer: unique value left, how many places depend on it, is there a replacement, cost of each migration, cost of keeping it.
- Default advisory removal (warning, guidance, users migrate themselves); a compulsory deadline only for a vulnerability, a blocker or unaffordable cost, with a migration tool.
- The owner of the removed infrastructure carries the migration or compatibility: "The Churn Rule", no announcing deprecation and leaving others to cope.
- Migrate one consumer at a time: find every touch point, switch, check behaviour matches, drop the old reference, confirm no regression. Delete only at measured zero usage, with its tests, docs, configuration and deprecation notices.
- Patterns: old and new in parallel, shifting traffic in steps; a compatibility layer keeping the old interface; or users moved one by one behind a flag.
- "Ghost" code (no owner, many dependents: long without a commit, a broken test nobody fixes, a vulnerable dependency) is reported as a risk for the user to decide an owner or removal.
