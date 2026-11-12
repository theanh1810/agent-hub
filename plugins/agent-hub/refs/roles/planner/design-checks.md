# Design checks — what planner verifies while detailing brainstorm's design
<Owner: agents/planner.md § References>
<Read when: the plan carries a contract, API, migration, module-boundary, decision-record or prototype task, at Workflow step 4. The design is brainstorm's (user, 2026-10-26); planner only checks the detail carries it.>

---

A failed check is `needs_revision`, `reason: change_design_incomplete`, naming task and field. Planner adds none of these to the design.

## API and contract

- The contract is defined before it is implemented; its task precedes its consumers.
- One error shape for every endpoint. New fields optional; an old field neither changed nor removed. Lists paginate from the start. One version at a time: extend, never branch.
- Every observable behaviour (error wording, ordering, timing) is a commitment; no implementation detail leaks. "With a sufficient number of users of an API, all observable behaviors of your system will be depended on by somebody." Plan removal at design time: for anything new ask "how do we remove it in three years".

## State-changing endpoints with an idempotency key

- The key comes from the intent, not the attempt; claiming it is one atomic step (unique constraint); the same key with a different body fails loudly; a copy still running returns 409, waits or returns 202 by deliberate choice.
- The intent is written before the outside call, because "Every call has three outcomes, not two: success, failure, and unknown."; the key outlives the longest retry chain, dead-letter replay included.

## Migration

- "A migration you can't reverse is a deploy you can't roll back." Every migration has a reversal run before merge; a large index is created without blocking writes; backfill in small batches off the hot path, never one `UPDATE` over millions of rows.

## Modules and test seams

- A module's interface is its test surface; a test that must cross it suggests the wrong shape; an internal seam is not exposed because a test uses it.
- Dependencies sort by how they are tested: in-process (directly), local stand-in (run it), our own across the network (port and adapter, in-memory adapter in tests), third party (mock at the port).
- "One adapter means a hypothetical seam. Two adapters means a real one." No port without two adapters worth having.
- Deep over shallow: a module is deep when a small interface hides a lot of behaviour, shallow when the interface is nearly as large as what it hides (matt codebase-design SKILL.md:8-95); check the design asks for depth where callers would otherwise repeat the work. Deletion test: if deleting the module makes its complexity vanish it was a pass-through; if the complexity reappears in N callers it earns its keep.
- Locality: the change a requirement causes lands in one module, and a design that spreads it over several is reported. Depth is a property of the interface, not the implementation; a deep module may have internal seams.

## Decision records and prototypes

- A decision record exists only for a choice costly to reverse (framework, large library, data, auth, API architecture, infrastructure), in the repo's convention (location, numbering, headings); disagreeing sources are reported, not settled with a new style. Never deleted: a changed mind writes a new record naming the one it replaces; each rejected option lists pros, cons and why it lost.
- "A prototype is **throwaway code that answers a question**." Labelled a prototype, one command to run, nothing durable stored, no polish, full state printed after every action; once verified the decision goes into real code and the prototype stays on a temporary branch with a pointer in the task.
