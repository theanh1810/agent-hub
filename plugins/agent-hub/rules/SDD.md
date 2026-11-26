# SDD — Spec-Driven Development, OpenSpec form
<Owner: rules/core.md>
<Read when: `spec_required` is true, a net raises it, or work touches a spec, glossary, decision or spec debt>

---

Spec first, code second: people agree on intent, AI writes code and tests around it. Spec deltas are English (`refs/plan-lane.md`); file locations are stated once in `refs/plan-lane.md § Where the files live`.

## 1. When to use it

**On** when the system lives long, several people touch it, rules involve money, contracts, legal or access, or AI writes most of the code. **Off:** a prototype, spike, one-off script, typo, or a hotfix while it burns (spec afterwards).

**Scope list.** The modules in the spec layer are the project's `modules_in_scope[]` list, widened only on the user's word. A task touching a module outside it makes brainstorm ask once: bring it into scope · work without spec · log the debt. Never add or skip it silently. 

| Class | Spec required? |
|---|---|
| `simple`, `problem-solving`, `infra`, `docs`, local `bug`, `hotfix` (at fix time) | no |
| `bug` on a shared symbol, contract, route or schema; `feature`; `medium`; `complex`; `refactor` | yes |

§ 10 says which artifact each class owes.

### 1.1 Spec Layer — who does what

- `brainstorm` owns specs, glossary and decisions and writes the user's business answer into the delta before returning. `designer`: the main flow is the primary flow. `implement`: a rule no scenario states is `blocked_needs_spec`; a hotfix logs debt; never edits specs. `reviewer`: the run's `independent` review never opens a spec (`agents/reviewer.md`); in `task` mode on a brief it reads the scenarios first, and `spec_drift` blocks. A run's spec compliance is `test`'s. `test`: one test per scenario a task's `Covers:` names. `devops`: infrastructure has a `## Decisions` entry.

**Blocking gates:** a requirement with no scenario, or a class-B bug with no user answer: no code · `spec_drift`: no merge. A hotfix is never blocked: patch, log the debt, repay within 24 hours.

The initial `spec_required` is a guess; three nets re-evaluate it (§ 11).

## 2. The spec form

OpenSpec only. Live specs: `openspec/specs/<capability>/spec.md` with `### Requirement: <name>` (SHALL) and `#### Scenario: <name>` (WHEN/THEN). A change states its edits as a delta (`templates/spec/spec-delta-template.md`). A delta that adds a new capability carries a real `## Purpose`: without one, archive writes a placeholder that `openspec validate --specs --strict` rejects. Requirement wording, checked by `openspec validate --strict`: SHALL or MUST, at most 500 characters, each scenario with `- **WHEN**` and `- **THEN**` lines; the template holds the form.

Mapping: a UC becomes a requirement group titled with its old id; an acceptance criterion a `#### Scenario` titled with its old AC id; a BR one `### Requirement` titled with its old id; an entity term a glossary entry (§ 7); an entity rule a requirement.

Old ids survive as names in titles only.

## 3. Conversion on first touch

On first touch of a project with `docs/specs/**` and no `openspec/specs/`, brainstorm runs `mode=spec-convert`: `openspec init --tools none --no-animation --no-copilot-cloud .` (`--tools claude` would install skills the harness auto-loads), write each approved UC and BR by hand, with the mapping above, as an ADDED delta under `openspec/changes/<change>/specs/<capability>/spec.md`; nothing is written to the live `openspec/specs/` before approval. No bulk tool. The plan gate and its stamp cover the converted specs; after the final `Approve`, `openspec archive <change> --yes` (main thread) merges them into `openspec/specs/`; on Cancel the change folder is discarded. `docs/specs/**` stays as history, read by no role, removed only on the user's word.

### 3.1 Closing a change

`openspec archive <change> --yes` merges the deltas into the live specs (`refs/plan-lane.md § Close`). Before it runs, brainstorm checks every requirement the change adds or edits is a delta under the change and every scenario has a test in `ac_coverage[]` or is stated uncovered. An unconfirmed rule is not written: `needs_user_input`.

## 4. Spec prose style

Entity names, fields, statuses and endpoints stay English. Every scenario is one observable WHEN/THEN with a name the tests bind to. Every technical term is in the glossary. No class or function names in a requirement (they belong in `design.md`). No unmeasurable sentence: state the result. An exception the user expects is spec; a crash is a bug.

## 5. Principles and Ready / Done

A new concept in code (field, status, flow, permission) exists in the spec before or with the code. People decide limits, refunds and anything with money or legal weight. The user's answer is written into the delta, never left in the session.

**Ready:** a requirement with at least one scenario, every term in the glossary, every clarify question answered. **Done:** every scenario has a passing test, a rule found while coding is written back as a delta.

## 7. Glossary and decisions

- **Glossary.** Kept at `openspec/glossary.md` (else `docs/glossary.md`); write rules and format: `refs/vendored/domain-modeling.md`.
- **Decisions.** The `## Decisions` section of the change's `design.md`, with each rejected alternative. What a project with `openspec/` does not create, and the method: `refs/vendored/domain-modeling.md`.

## 8. Brownfield and scope

No big-bang rewrite before a baseline. A spec generated from code says what the code does, not whether it is right: the user verifies it. Spec hot modules first.

### 8.1 Adoption block and coverage

`openspec/scope.md` opens with `sdd_adopted`, `scope: partial|full` and `modules_in_scope[]`; without it every metric reads `N/A`, never `0%`. The user picks modules from a list built from commit counts. Hot modules left out are listed there with commit counts.

### 8.2 Coverage

A scenario is tested when a task's `Covers:` names it and test's `ac_coverage[]` records a passing test; missing a test when shipped with none; not yet measurable when tests exist but are unnamed by scenario (counted in neither numerator nor denominator). Procedure: `refs/commands/spec-check.md`.

## 10. Playbook per task type

| Task type | Artifact (when, who) | Blocks? |
|---|---|---|
| `simple`, `problem-solving`, `docs`, `error-batch` | none (a spec gap found: a debt line) | no |
| `bug` A | a regression test on the scenario (test) | no |
| `bug` B, or shared symbol, contract, route, schema | a new scenario or requirement (before, brainstorm, user approves) | yes |
| `hotfix` | a spec debt line (after, 24 h) | no |
| `feature`, `medium`, `complex` | requirements with scenarios; `complex` adds a `## Decisions` entry (before, brainstorm) | yes |
| `refactor` | none; characterization tests first; a behaviour change is a second change | yes |
| `infra` | a `## Decisions` entry (devops) | no |

### 10.1 Bug type A or B

Does the spec already say what this behaviour should be? Clear and the code differs: **A**. Ambiguous, silent or absent: **B**: ask the user, write the scenario, then fix. A type-B fix with a self-chosen rule is forbidden.

### 10.2 Hotfix — spec debt

Fix first, spec after. Implement patches, then adds a line to `openspec/_debt.md`:

```markdown
- [ ] 2026-08-07 · hotfix · <what happened>
      - Patched at: `<file:line>` · Rule just applied: <rule> · Confirmed by anyone: no, ask {person}
      - Requirement to update: <name> · Due: 2026-08-08
```

Within 24 h brainstorm has the user confirm the rule, writes it into a delta and ticks the box; "confirmed by anyone" matters most, since a hotfix rule is one developer's decision.

### 10.3 No spec layer yet

A task needing SDD stops with `needs_user_input` proposing `/spec init` (`commands/spec.md`): the init command of § 3, `openspec/scope.md`, `openspec/_debt.md`, no requirement; the first is written for the part being touched.

## 11. Against misclassification

`spec_required` comes from the class before anyone knows what the code touches. Re-evaluate: brainstorm after its dependency trace → implement on the real diff → reviewer on the diff.

### 11.1 Deterministic triggers

A diff touching any of these forces `spec_required = true`, whatever the class:

Migration or schema (`**/migrations/**`, `schema.prisma`, `*.sql`, a model column added or removed) · external contract (`*.proto`, `openapi*.yaml`, `swagger*.json`, `**/contracts/**`) · routing (`**/routes/**`, an endpoint added, removed or changed) · a business enum value (status, type, tier, role) · permission (`**/policies/**`, `**/permissions/**`, `**/guards/**`, `**/middleware/auth*`) · events (new name or changed payload) · a business constant · a module named `payment`, `refund`, `invoice`, `billing`, `tax`, `contract`, `kyc` or `consent`.

A floor, not a ceiling.

### 11.2 The three nets

- **Net 1, brainstorm:** after the dependency trace, raise `spec_required` on a shared symbol, contract, route, schema or § 11.1 match; record `spec_required_escalated_from`. Never lower.
- **Net 2, implement, before committing:** `spec_required: false` but § 11.1 matches or a business rule is added: `blocked_needs_spec`, `reason: spec_required_escalation`, pattern, `file:line`. A hotfix logs debt; a mechanical change says so in `## Risks`.
- **Net 3, reviewer:** at `false`, a new field, enum value, route, event, migration or unsourced business constant is finding `spec_required_misclassified` (major); the user decides.
