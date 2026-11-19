# Rule authoring: the standard for every rule edit
<Owner: rules/core.md § No invented rule>
<Read when: writing or editing any rule file, agent, ref, skill, template or ADR in ~/.claude, and when a reviewer reviews such a diff>

This file is the only home of authoring rules: skill and agent files, wording, testing a rule. Writing a rule or a brief for an agent: read `refs/vendored/writing-for-agents.md` too.

## Agent-file criteria

No file has a line or token ceiling; each added sentence earns its place.

- A line in an agent file is a rule the agent acts on every run, or a pointer to the tier-3 ref that holds it; text needed only on a trigger goes to that ref.
- Each rule has one home. Every other file points to it; `python3 tools/check.py ruleset` (agent-hub repo only) N1 (`rule_no_duplicate_passage`) reports a passage stated in two files.
- A section whose body is a `refs/` pointer holds that one line (N2, `pointer_section_one_line`); every ref and reference is named by path in another rule file (N3, the existing `no_orphan_ref_files`).
- Prune test, applied to every sentence a diff adds: delete it and ask whether an agent would act differently; if not, the sentence is prunable and the diff drops it. The reviewer applies this on each rule diff.
- One line states one rule; the sentence stays as long as that rule needs, split at the rule's boundary and not packed to reach a count.

## Prohibitions

Write the action first and the prohibition second. Every sentence that forbids something names what to do instead ("Write the plan from the live file; a remembered line is not a source"). A user's verbatim quote and a HARD marker stay exactly as written; the pairing goes in the sentence beside them.

## Skill and agent files

- Create a skill only for a technique that is non-obvious and reused across projects; a one-off or a project convention goes in the repo's guidance file. Extend an existing skill before adding a near-duplicate.
- `name`: lowercase, digits and hyphens, equal to the folder, a verb-ing or clear noun phrase; never `Helper`, `Utils`, `Tools`.
- `description`: third person, opens "Use when <trigger>.", then one sentence naming the outcome (an artifact, decision or answer) and the trigger keywords users actually say. It states what the skill gives and when to use it, within 1,536 characters, and names no step or order: the body holds the steps, and a description that narrates them gets followed instead of the skill.
- Body shape: purpose, When to use, When NOT to use (if non-obvious), Steps, Key rules, Red flags, Verification with evidence. Imperative voice; a fixed output format is a template.
- A step is concrete and checkable ("run the test command and confirm every test passes") and ends with a done criterion.
- Progressive disclosure: name and description are always in context, the body loads when the skill fires, references load when needed. Under 50 lines of principle stays in the body; longer reference goes one level below `SKILL.md` behind a pointer that says when to read it. Each reference is named by one load line with its condition.
- Co-locate a concept's definition, rule and exceptions under one heading. Use one term throughout and forward slashes in paths. Several valid routes get prose; a fragile operation gets an exact command, with one default and one escape hatch.
- One real, runnable example beats many mediocre ones.

## Wording

Pick the form by the failure measured:

| Failure | Form |
|---|---|
| a HARD rule broken under pressure | "forbidden" + rationalization table + red flags |
| output of the wrong shape | a positive recipe naming the parts in order |
| a missing element | a required slot in the template |
| behaviour that depends on a condition | tie it to an observable condition |
| everything else | say what to do |

- State the wanted action: a bare prohibition primes the forbidden behaviour.
- Give the reason instead of capitalised MUST, written general and not narrowed to one example.
- Mark a rule `(HARD)` only when breaking it once cannot be taken back: data, secrets, history, a host, or an approval the user has not given. Any other rule is a guideline the agent may weigh, so it carries no label.
- A leading word the model already knows ("tight", "red") replaces a long sentence.
- A real exception is its own rule; an "unless it matters" clause reopens negotiation.
- Keep one source of truth: the environment (scripts, config, layout, `--help`) is the source and docs copying it are copies. Record what cannot be looked up: conventions, reasons, traps.
- Prune what no reader needs: write only what the agent does not already follow, and delete a dead sentence whole.
- A mechanical violation (pattern, banned API, file location) becomes a deterministic check; prose is for judgement.

## Testing a rule

- Pressure-test a rule by running the scenario without it first: the baseline shows the failure the rule must fix.
- Then run the same scenario with the rule; the rule passes only when the choice changes as intended.
- Only a discipline or heavily reused skill gets the eval loop (baseline run, with-rule run, compare, tighten the wording, repeat); the rest are read once as a stranger would.
- Finish one rule before starting the next.

## Red flags

| Thought | Reality |
|---|---|
| "The description should list the steps" | The agent then skips the body. |
| "More skills means more coverage" | Near-duplicates drift; extend the owner. |
| "A longer rule is a safer rule" | Dead sentences cost tokens and hide the live ones. |

## ADRs

Whether a decision gets an ADR is settled by the three-part filter in `refs/artifact-layout.md` § Where writing is allowed; a decision that fails it is recorded elsewhere. In a workspace with OpenSpec a decision goes in the change's `design.md` and no ADR is written. The body has the headings `Context` and `Decision`, 1-3 sentences, per the template `templates/adr/ADR-template.md`. Files are numbered NNN in the existing sequence; 013 stays unused.

## Behavioural testing

Only a new rule or an ADR-level change gets a behavioural test; a wording fix is read by a stranger and shipped.
- Brainstorm writes one pressure scenario per new rule, with a forced A/B/C choice and the expected choice taken from the rule text.
- Main thread spawns two short sonnet runs per scenario: a baseline given the governing text as it was before the change, and a with-rule run given the new text. Each writes its choice and a one-sentence reason under `.cm-tmp/{plan_id}/rule-tests/`.
- `test mode=script` compares each recorded choice with the expected one. A with-rule run that chooses wrong is a finding for brainstorm `mode=error-batch`.
- A subagent asks main thread for a run and spawns none (`rules/core.md`, first paragraph).

## Scripts

A script's header lists every exit code it returns. A hook that must never block says "Always exits 0" and ends with `exit 0`. A script that writes a temp file removes it on failure and re-raises the error; status goes to stderr and machine-readable output to stdout. Shipped scripts are invoked through their interpreter in the instruction (`bash scripts/x.sh`).
