# Root cause: the procedure brainstorm follows
<Owner: agents/brainstorm.md § References>
<Read when: brainstorm roots a bug (change-design Phases 3-5, per group in error-batch) or implement returns root_cause_unconfirmed>

---

A bug is root-caused here, in Phases 3-5 and per group in `error-batch`, never by `implement`. "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST." The same procedure runs when implement returns `root_cause_unconfirmed` after three failed attempts, starting from the attempts and failing output it quotes. `test` only reproduces.

1. **Start from evidence**: the error, log or repro verbatim (`errors.yaml`, a `test` evidence path, the user's text), not broad reading. A log only a host holds is a `devops` fetch (`refs/roles/brainstorm/devops-boundary.md`).
2. **A red-capable command first.** One command going red on exactly the reported symptom, run at least once, precedes any hypothesis; building a hypothesis from code without it is the signal to stop. None buildable: state what was tried, then ask the user for the environment or a secret-redacted artefact (HAR, log), never guess on. "I know what the bug is" is right about 70% of the time and the other 30% costs hours. Read the whole error and stack trace (line numbers, paths, codes); not reproducing reliably → gather more data.
3. **Map the trace**: each stack frame to its symbol with `mcp__gitnexus__context`; classify the error type. A narrow mem0 search for a `validated_root_cause` with the same signature.
4. **Regressions and recent changes**: a scout brief running `git log` and `git blame` on the shortlist narrows the introducing commit; to find it exactly propose `git bisect run` with a dedicated test command (implement runs it). Also a new dependency, configuration, environment difference.
5. **Hard to reproduce**: time-dependent → log timestamps and an artificial delay to widen a race; environment-dependent → compare versions, env variables, empty vs full data; state-dependent → globals, singletons, shared caches, isolated vs after another action; truly random → defensive logging and an alert on the signature. Mobile: `adb logcat`, Xcode crash logs or `atos`, Metro or Hermes output are evidence like any log. Multi-component systems (CI → build → signing, API → service → DB): propose one measurement at each boundary (in, out, configuration passed) to learn where before why.
6. **Shrink before fixing**: strip code, configuration and input one thing at a time, re-running, until removing any remaining part turns the case green. The smallest case becomes the regression test.
7. **Compare with working code**: find similar working code and list every difference, however small; never drop one as "that probably doesn't matter".
8. **One hypothesis at a time**: "I think X is the root cause because Y", falsifiable ("if X is the cause, changing Y makes the failure vanish"; no prediction means drop or sharpen it), tested by the smallest change, one variable. Each probe answers one prediction (debugger or REPL first, then a log at the boundary separating hypotheses, never "log everything, then grep"). Wrong → a new hypothesis, never a stacked fix; not understanding → say "I don't understand X".
9. **Read through scout**: every file, history or log the trace needs is a `recommend_scan[]` entry; synthesize from `scout_results_refs[]`.
10. **Trace backward** from the symptom through the call chain ("what called this, with which value"), asking "why" to the original trigger, and fix at the source, not where it shows (a duplicate in a list → fix the JOIN, not dedupe in the UI). "Fix at source, not at symptom."
11. **Synthesize**: root cause apart from contributing factors, and a causal chain with every link cited `file:line`, into `root_cause_or_mechanism` and `causal_chain[]`. Below 0.7 confidence it is a hypothesis: label it or ask.
12. **Compare sibling paths**: every other code path writing the same table or state and every user-facing screen, route or message reached (`impact` or scout) goes in `affected_surfaces`, each with a covering task or a reason.
13. **Genuinely environmental, timing or external**: record what was investigated, propose handling (retry, timeout, a clear error) and monitoring. "95% of "no root cause" cases are incomplete investigation."
14. **Signals of patching without understanding**: the user says "stop guessing", "is that not happening?", "think deeper" → back to evidence, no further fix.
15. **Debug logging** only when the failing line cannot be pinned, the failure is intermittent, or several components interact; brainstorm proposes it (file, what, remove-when), implement adds it, removing it when done and at once anything holding sensitive data. Keep permanently: error boundaries, API error logs with context.
16. **Prove it**: the test plan's first case is the failing reproduction, written by planner as the task's first case and step so implement's red step runs it before the fix. Brainstorm runs no test.
17. **Where the regression test goes.** Name the correct seam (the lowest level whose failure pattern matches the bug at the call site) in the first case and step. A bug no seam can lock in is recorded as an architectural finding rather than a fragile test. The original unminimised reproduction green, the regression test passing and debug logs removed closes it.
18. **Build, type, import and config errors**: triage by the first reported error only: type → the exact location; import → the module exists, export matches, path right; config → syntax and schema; dependency → manifest and lockfile; environment → versions and OS. `test` quotes the first error and stops (`refs/roles/test/repro.md`); this tree is brainstorm's.

## Before a cause is accepted

The feedback loop is the skill; every later step consumes its signal (matt diagnosing-bugs SKILL.md:18-66).

- Ways to build one, roughly in this order: a failing test at the seam that reaches the bug · an HTTP script against a dev server · a CLI run diffed against a known-good output · a headless-browser script asserting DOM, console or network · a replay of a captured payload · a throwaway harness of the minimal subset · a fuzz loop for "sometimes wrong" · a bisection harness · a differential run of old against new · a scripted human step as the last resort.
- Tighten it: faster (narrow the scope), sharper (assert the specific symptom, not "did not crash"), more deterministic (pin time, seed random, isolate files and network).
- Done test: one command, red-capable, deterministic, fast and runnable unattended. Brainstorm designs it and runs no test: it asks `test` to run it, in `mode=script`, by returning `needs_repro` with a `repro_request` (the command, the symptom it must go red on, the environment). `test` runs it and reports the exit code and output.
- A root cause is accepted only after that command went red on the reported symptom. A different nearby failure is the wrong bug.

## Not reproducible

Gather data, never guess (obra systematic-debugging SKILL.md:58-62; matt diagnosing-bugs :49-55; addy debugging-and-error-recovery SKILL.md:40-73).

- A non-deterministic bug: the goal is a higher reproduction rate, so loop the trigger, add stress, narrow the timing window; a 1% flake is not debuggable, a 50% one is.
- Access or an artefact missing: return `needs_user_input` asking for the environment, a secret-redacted capture, or leave to add temporary instrumentation. Do not hypothesise without a loop.
- Otherwise design an instrumentation task (D10-b): `implement` adds the temporary logging in its own task and that task's last step removes it. Logs carry a unique tag (`skills/implementation-tdd/SKILL.md` step 5) so one grep removes them.

## Hypotheses and defence in depth

- Write 3-5 ranked hypotheses before testing any; each names the prediction that would refute it ("if X is the cause, changing Y makes the failure vanish"). Single-hypothesis generation anchors on the first plausible idea (matt :88-98).
- When the cause is a bad value, add a check at every layer it crossed: the entry point, the business logic, the environment guard (refuse the dangerous operation in that context) and a debug record for forensics (obra defense-in-depth.md:20-94).
- Red flags: "quick fix for now", "just try changing X", several changes at once, "one more attempt" after two failures, each fix revealing a new problem elsewhere. All mean back to evidence; three failed fixes also raise `architecture_signals[]` (`refs/roles/orchestrator/error-loop.md`) (obra :214-255).
