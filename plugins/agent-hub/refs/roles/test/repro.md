# Reproducing a bug, and the red-green proof

<Owner: agents/test.md § Workflow>
<Read when: a bug report or bug-fix task arrives, a regression case is written or checked, a case is flaky, or a failure needs its data traced across layers.>

---

Test only reproduces and hands the failing run to brainstorm, who owns the root cause (user decision 42). It never proposes a fix.

## On receipt

1. Write the repro case at once, before the root cause is settled (user decision 47), as a command or browser case on a copy under `.cm-tmp/{task_id}/repro/`. The real tree is untouched.
2. Build a tight loop: a red signal on the exact symptom (not "didn't crash"), fast, stable (pin the clock, seed randomness). About 2 s deterministic beats 30 s flaky.
3. No loop buildable → stop. Say what was tried and ask the user for the environment or a redacted artifact (HAR, log) and reproduce from what they send. Never guess further.
4. Hard "sometimes wrong" bug: run 1000 random inputs; compare the same input between old and new build.

## Red then green

A regression case for a fixed bug carries proof it was red on the buggy build and green on the fixed one. "Test written" without a seen red does not count; auditor counts it as "regression not red-green checked".

## Flaky

A flaky case is a `flaky` finding with its rate: red x of N repeated runs (50% is debuggable; 1% needs a higher run count before it is worth reporting).

## Many layers

When a multi-layer system fails, record the data in and out at each boundary in one run to show which layer breaks. Still no cause: name the suspect layer and stop. A build, type or import error: quote the first error with its location; triage is brainstorm's.

## Quoting evidence

Redact secrets to `<REDACTED>` before quoting a command, output or artifact; auth headers keep only the signal lines. Redaction leaving too little to diagnose → say so and ask the user.
