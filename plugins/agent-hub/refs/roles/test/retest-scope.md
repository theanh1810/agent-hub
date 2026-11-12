# Retest scope (HARD)

<Owner: agents/test.md § Workflow>
<Read when: `rerun_test_case_ids[]` or `changed_files[]` is non-empty — a run after a fix.>

---

Every fix is followed by a full re-run.

After a fix the run is full: every applicable step of `two-pass.md § Which steps run`, every case in it, on the new build. Results from the build before the fix count for nothing (`resume.md § Resuming` step 2).

1. `rerun_test_case_ids[]` names last round's failures. It never narrows the run (never shrink it because a tool failed or the suite is long); the report says which turned green. Part (a) also runs every `added_cases[]` case of the fix entries of earlier rounds in `errors.yaml`.
   - Part (b) in a fix round re-runs only the exploratory cases whose failure was major in the round that went red; minor ones are in the ledger.
   - The final gate's `Request changes` round runs only the planned cases of the tasks whose `files[]` the fix touched, plus its `added_cases[]`, and no part (b) (it overrides the full re-run for that round only).
2. A hotfix runs steps 1 and 2 in full and step 3 over the one main flow it fixed; a fix round does not widen step 3.
3. Re-check earlier results: "confirmed" holds only while its source and conditions are unchanged. Deferred, blocked and out-of-scope items from the last run are priority input, not a key to skip. One rejection suppresses only that exact claim, not review of the area. Such items are a new pass, outside the 2-loop error cap.
4. Rollback marker: after each passed step note the good point; a step that turns a test red returns to the nearest good point and investigates, never patches on top of the broken state (git history untouched).
5. The same failure still red after two loops: write "the fixer probably cannot see its own problem" so orchestrator asks the user to change direction, never opens a third loop unless the user consented at the cap, and never a fourth (auditor counts this pattern).
