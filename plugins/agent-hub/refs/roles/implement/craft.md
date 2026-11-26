# Craft
<Owner: agents/implement.md § References>
<Read when: Workflow step 3, before the first line is written. The priority ladder, the evidence each claim carries, naming and shape, and which comments a diff may carry decide every line from here on; step 7 re-reads § The self-check before committing.>

---

## Priorities (HARD — in this order when they conflict)

**1. Do not break the existing structure.** The smallest structural disturbance wins: no moving files, renaming modules, changing a layering boundary or adding an architectural concept because it is tidier. Restructuring is its own task.

**2. Apply the codebase's patterns completely, not partially.** Same error type, logging call, folder, naming as the codebase. Half a pattern is worse than none: the next reader cannot tell which convention is current. Two carve-outs only: **how many comments the diff carries** (rule 5 and § Comments decide; a neighbour dense with comments is drift, not licence) and **the folder of a new test file** (`code-style/README.md` § Test layout, not a neighbouring `__tests__/`).

**3. Prefer the simple, low-risk, whole solution.** Of two working options take the one easier to read and harder to get wrong, even at a few lines or some elegance. Write the correct naive version first; optimise only after tests prove it. Trade-offs stay inside the task's scope and go in the handoff's cost line (`close-task.md § Write the result`).

- Before writing, climb this ladder and stop at the first rung that works: (1) does it need to exist; (2) the best solution for the real data, simple unless a measurement, an acceptance criterion or known large data calls for an optimised algorithm; (3) a library: the standard library, the platform, or an installed dependency (a new dependency stops and asks); (4) a standard pattern; (5) code already in the project, used or adapted, and extracted on the third copy. Lazy about the solution, never the change: update the callers, tests and fixtures it breaks, since they are part of it.
- Deletion beats addition: removing code the change makes unnecessary is the smallest diff.
- Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility. Code you move or merge keeps its error handling and validation.
- Abstract on the third use, not the first (three similar lines beat a premature abstraction). Clarity over brevity: no nested ternaries or long reduce chains.
- State the smallest diff first; a diff 3x larger needs a reason. Use a named constant for a value that never varied, with no config for it. Do not rewrite what the codebase has inside the task; report it.
- New code defaults to safe and conservative: a feature off, a notification unsent, enabled only on purpose.

**4. Then optimise the algorithm.** Pick the algorithm for the real input size and state the complexity and why it fits (`O(n log n)` over `O(n²)` on 4,000 rows is a reason; "cleaner" is not). No micro-optimising an unmeasured path. Measured work: `refs/roles/implement/perf-deps.md`.

**5. Comment rarely, and only where it matters.** A comment qualifies only under a category of `rules/code-style/_discipline.md` §5; first ask whether the line should be clearer. See § Comments.

**6. Clean code.** No leftover lines, dead branches, commented-out blocks or half-finished abstraction.

**7. Tick the task and write the result into the handoff before finishing**, bug fix and hotfix included: `refs/roles/implement/close-task.md` § Write the result.

## Evidence

> NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE

- **Pattern reference**: before writing ≥10 new lines cite `Pattern reference: <file:line>` of a standard pattern or an in-project one; none cited means none was looked for.
- **Business rule**: `UC-XXX / AC-N`. No AC means the rule is missing from the spec: block with `blocked_needs_spec`, since an invented rule is forbidden.
- **Contract change**: the tool result listing every call site, `impact` by depth for a symbol, `api_impact` by consumer for a route; never a guess from naming.
- **Algorithm choice**: the complexity and the input size.
- **Test result**: the command, exit code and real numbers, tagged with the test-case id, run in this turn. "Should work", "looks fine" and "tests pass" without a count are not results; a clean lint is not a passing build.
- **Trade-off**: what was given up, in the handoff's cost line; empty means not thought about.
- **No savings claims** ("saved X lines"): only counted figures.

## Craft — naming, shape, structure

### Naming

- **House dialect first**: where neighbours say `fetchOrders`, never write `getOrderList`.
- **Business names come from the Entity Model** (`specs/entities/`); a coined synonym splits the codebase's language.
- **Variables** name content, not type: `activeAlerts`, not `arr`, `data`, `x`; a boolean reads as a predicate (`hasExpired`), never `flag`; units in the name (`timeoutMs`); a single letter only as an index in a three-line loop.
- **Functions**: verb first, and truthful: `getX` reads, `fetchX` crosses a network, `computeX` derives, `ensureX` is idempotent, `validateX` throws or returns a verdict. A `getUser` that also writes an audit row is misnamed: rename or split.
- Length follows scope; no abbreviation the codebase has not established (`id`, `url`, `db` are fine); no name that no longer matches the code.

### Function and file shape

- **Split by job, not line count**: say what it does in one sentence without "and"; never split into helpers only to look short. 40 lines is a target, 80 a flag to check the job count, not a cap (user, 2026-10-26).
- Cyclomatic complexity ≤12; nesting ≤3; parameters ≤4 (beyond that an object with named fields). Guard clauses first, happy path unindented. No boolean parameter that switches behaviour; a function returns a value or causes an effect, not both quietly.
- A symbol used by one function lives beside it; a function with one caller lives next to that caller; a second caller justifies a split.
- No layer jumping to save lines; handle errors the established way (same type, wrapping, logging).
- Delete what the change orphans, leave what it does not; unrelated dead code is a finding.
- **File budget**: each new file needs an accepted reason, one line per file. No `utils` / `helpers` / `common` for one function, `types` / `constants` file for one symbol, one-call wrapper, or surplus README.
- **A file you create** nearing ~400 lines or gaining a second concern is split, and you say what you split; new files stay inside `files_allowed[]`, else `scope_extension_needed`.
- **Slices**: work the plan cuts small ships in slices, each leaving the project compiling with old tests green. An unfinished user-facing part sits behind a flag defaulting off; a flag the plan never names is forbidden. One commit per task (`refs/roles/implement/close-task.md` § Commit).

### Cases and security

- Walk the case list: empty, absent, boundary, wrong type, too large; for an operation, run twice, break midway, run concurrently, dead dependency; for output, an error path that leaks nothing internal, an empty result distinct from an error. An impossible case needs a concrete reason; every possible case is a test or a stated non-goal.
- Parameterized queries; output encoded against XSS; authorization checked at every guard point; secrets only in environment variables.
- Before commit scan the diff for secrets with a redacting tool (gitleaks `--redact` style); report rule and location, never the value. `.env`, `*.pem`, `*.key` are gitignored; `.env.example` holds fake values only.

### Style sources

The repo's `docs/CODE-STYLE.md` beats the neighbour; a disagreement is a finding. Load only the language files for languages in scope (today: javascript, typescript, react, python, sql); a missing one goes under Risks and the neighbour decides.

### The self-check before committing

Read the diff as a stranger, answer:

1. Does every name still describe what the code now does?
2. Could a reader follow this without asking me a question?
3. Is there a line here the task did not ask for?
4. Does this replace an existing implementation, and did I report it (file:line, call sites) as a separate proposed task?
5. Would I be comfortable if this were the file someone read to learn the house style?

Also: every requirement done, no edge case missed; tests check behaviour, not mocks, with clean output. Any "no" is fixed before the commit, not filed.

## Reporting

- **Three parts**: changed (a file and one line each) · deliberately not touched (a file like the problem but out of scope) · concerns for the user to confirm (a strict schema rejecting extra fields, how heavy a new dependency is).
- **NOTICED BUT NOT TOUCHING**: something worth fixing outside the task is listed with its path and the reason in `extra.findings[]`, asking whether to make a task. Never fix it.
- **Four states**: done · done with concerns (settled before review) · needs context · blocked. A stop is never an error: "Bad work is worse than no work." Act on every escalation and change something before a retry; never ignore it or force the same model to retry unchanged.
- **Stop and report, do not push through**, when: an architectural decision has several valid directions · you must understand code beyond what you were given · you are unsure of the right way · the work needs restructuring beyond the plan · you read file after file without progress.
- Detail is the handoff (`refs/roles/implement/close-task.md § Write the result`); the returned message is short. A TDD task's handoff carries red (command, failing output, why that failure is right) and green (command, passing output).

## Comments

How priority rule 5 applies. Categories and forbidden shapes: `rules/code-style/_discipline.md` §5 only. A comment matching no category is rewritten into one or deleted. A deliberate shortcut is an allowed why-comment in the form `shortcut: <limit>, <when to upgrade>`. Every comment in the diff is listed in the handoff with its `file:line` and claimed category; no count or cap.
