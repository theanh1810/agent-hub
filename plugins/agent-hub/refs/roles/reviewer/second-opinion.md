# Review second opinions
<Owner: agents/reviewer.md § Workflow>
<Read when: the review ends and a doubt about named hunks stays open>

## Rules

- One review per run: the agent-hub reviewer, blind to the plan. It stays the single final review.
- A second opinion is never a second review. It answers one question about named hunks.
- The reviewer may request one at the end of its review, first pass only.
- The reviewer's return carries `second_opinion_request[]`, at most three entries: two specialists, one Codex.
- Each entry is `{kind, agent, sign, hunks[], question, brief_path}`.
- The reviewer judges the sign and asks only when its own checklist leaves the doubt open.
- A subagent cannot spawn. Main thread spawns every requested agent in one message.
- The brief is the file the reviewer wrote, `second-opinion-<n>.md` in its own `.cm-tmp/` folder (`refs/artifact-layout.md § Ephemeral output`), from the template below: hunks, diff base, the one question. No plan text, no diff text, no finding of this review, no secret, no PII.

## Specialists (pr-review-toolkit)

| Sign in the diff | Agent to request |
|---|---|
| an added or changed catch / except / rescue / fallback that swallows, downgrades or defaults an error | `pr-review-toolkit:silent-failure-hunter` |
| a new or changed exported type, schema or model whose invariants the diff relies on | `pr-review-toolkit:type-design-analyzer` |
| changed logic whose tests look thin or missing for the changed branches | `pr-review-toolkit:pr-test-analyzer` |
| added or changed doc comments on a public API, or comments that may contradict the code | `pr-review-toolkit:comment-analyzer` |

- Never requested: `code-reviewer` (a second general review), `code-simplifier` (it edits code), the command `review-pr` (a second workflow).

## Codex

- Codex diff review only at high risk: the run's tier is L4, or the security override is on, or the user asked.
- `tier` and `security_override` arrive in the reviewer's brief (brainstorm's return, `refs/effort-routing.md § Tier`).

## Brief template

```
Read-only review of named hunks: report findings and change nothing. Never edit, create or delete a file; never commit. Codex runs without --write.
Question: {the one question}
Hunks:
{file:line-range, one per line}
Diff base: {base_ref, or "none: review the files as they stand"}
Read only these files and the files they import. Leave unopened: .env*, *secret*, *credential*, *.pem, *.key, id_rsa*, ~/.ssh/, ~/.aws/. Describe a secret you meet by its location, never by its value.
Answer one line per point: file:line | problem | why | confidence (high, medium or low).
```

## Result path

- Each result is saved as an annex, `reviews/annex-<n>.md`, beside the review file.
- The annex goes with the review in `review_paths[]` to brainstorm `error-batch`, which triages every finding by the same bar.
- The reviewer is not re-spawned to merge it.
- At the final gate annex findings appear apart from the verdict (`refs/gates.md § Gate procedures`, Final gate step 4).
- Plugin missing or Codex not ready: main thread records `second_opinion_skipped` with the reason; the run does not stop.
