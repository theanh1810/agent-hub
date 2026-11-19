# Final response

<Owner: rules/core.md § Language>
<Read when: emitting the final answer to the user: main thread, and no other agent>

---

# Final Response

**The reply language (`rules/core.md § Language`), always**, however technical the work; technical terms stay verbatim inside sentences of that language, glossed once where a non-coder would stumble. **Written from the handoff, not from recollection**: its input is what the workers returned plus what main thread read itself; a claim in neither does not belong.

```markdown
## Summary
## Files changed
## Validation
## Risk
## Blocker / Approval
```

The section names above are canonical; main thread shows them in the reply language. Omit empty sections except `Summary`. Plan-only tasks add the change folder path, the path of `plan.vi.md`, the wave list, and what awaits approval.

The flow drawing (`refs/diagram.md`) is named under `Summary` by its absolute path, with whether closeout confirmed or updated it; a skipped one by its reason.

**Self-check points.** A final carrying an estimate or an assumption ends with 2-3 points the user should check, each naming one concrete number or assumption; once per conversation, skipped when the user said they will check or asked for the check. A generic "please verify" defeats the purpose.

**When the user says they do not understand**, re-tell it short: a little more context, simple sentences, the project's vocabulary, never the previous sentence repeated. **Name a task or item by its title, never a bare id, number or slug**.

**Fleet lessons awaiting approval.** A `closeout` block whose `memory` value lists `promote? <subject>` becomes one `AskUserQuestion` per subject (`refs/option-explanation.md`) under `Blocker / Approval`, with the drafted line, its target file and the three `seen` sources. Yes → main thread makes the one-line edit itself on the fast lane (`refs/lanes.md § L1 fast`) and sets `stage: pattern` and `promoted_to`. No → main thread records `declined: <date>`, the entry keeping `stage: candidate`, not asked again until a new sighting is counted. Each ledger change is one `agent-hub lesson` command (`skills/context-memory/references/dedup.md` § Lesson counter); main thread writes nothing to claude-mem, and nothing reaches a rule file before the yes.

**Closing line of a finished run.** A final whose run carries a `closeout` block (`refs/closeout.md` § Verification and enforcement) ends with this line, last and outside every section, in the reply language: `Type /clear to clear the context — the task summary reloads itself.` A final with no `closeout` block (a Q&A answer, or one stopping at a gate or question) never carries it. Only the user can run `/clear`; `hooks/clear_handoff.py` then restores that final's `Summary`.

**Explain, do not just report.** Every meaningful change answers **what changed · why it had to · what is different now**. A technical term on first use gets a one-sentence gloss in the reply language with an everyday example (`refs/option-explanation.md`). State every trade-off, even unasked. Work undone, blocked or unverified goes plainly under `Validation` or `Blocker`.

## Every claim carries its source

| Claim | Evidence |
|---|---|
| What the code does | `path/file.ts:120-134` |
| What was changed | the path plus a before/after excerpt, or the commit SHA |
| Tests pass | the command and its real numbers (`vitest run — 216/216`) |
| A build passes | the build command's exit 0 (a lint run is not a build) |
| The linter is clean | the linter's output with 0 errors |
| Delegated work is done | the diff of the work, not the agent's report of it |
| Validation could not run | say plainly it did **not** run, why, and the command for the user |
| A bug found | the error text verbatim |
| A business rule | `UC-XXX/AC-N` |
| A performance number | the figure and how it was measured |
| An external tool's state | the check command's output, with the date |
| An external document | the link and the date read |

**Banned** (in the reply language, whatever the wording): "checked it thoroughly" · "runs fine" · "a few hundred ms or so" · "per best practice" · "usually", and "should", "probably", "seems", or cheer before checking. Checked → show the result; not checked → say so.

**Say the set, then look once outside it.** A number is a claim about a set: name the set first (which tree, which pattern), then look once for the same thing *outside* it — split across a line break, hidden by markdown emphasis, in a copy of the file itself.

**Fresh evidence before any done claim.** The worker that claims done identifies the command that proves it, runs it in full, reads the output, the exit code and the failure count, and only then claims (obra verification-before-completion SKILL.md:14-36). Main thread quotes the worker's evidence path and runs nothing itself. Premature satisfaction before the run ("great", "done", "should work") and hedge words are red flags (:50-72).

Another agent's output is **not evidence** until cross-checked (agent said success → check the VCS diff). Quoting it names the source: "per `test`'s handoff: 216/216".

| Rationalization | Reality |
|---|---|
| "I checked carefully" | Show the command and its numbers, or say it was not run |
| "The worker said 216/216" | Cross-check, then name the source |
| "It worked a minute ago" | Evidence is the run you can show now, not memory of an earlier one |
| "The linter passed, so the build passes" | Different commands prove different things; run the build |

## Model trace

Main thread surfaces a trace line in the `Summary`:

```
Model trace: brainstorm(opus) → implement(sonnet) → reviewer(opus) → test(sonnet)
```

Printed with it, one more line: `Size: <lane id>`, the lane of `refs/lanes.md` the run took.

A missing header → re-spawn, or note it under `Risk`. Each `(model)` is the `model` the spawn passed to `Agent(model)` (`refs/effort-routing.md`), not the header, which under an override still names the frontmatter model.

## Field kinds

Three kinds of field cross into the reply:

| Kind | What main thread does | Language | Examples |
|---|---|---|---|
| **Relay** | quotes it unrewritten | the language its reader reads (the agent's Language block names these fields) | `user_questions[]`, `spec_question`, `new_dependency` |
| **Summary** | rewrites it into the reply | English; translating twice only loses meaning | `summary`, `root_cause_or_mechanism`, `classification_reason`, `findings[].description` |
| **Foreign** | forwards untouched in the language it arrived | **never translated or compressed**: quoted from outside the fleet, so rewording makes it evidence of nothing (`skills/context-compression/SKILL.md` § Hard rules) | `first_match_excerpt` |
