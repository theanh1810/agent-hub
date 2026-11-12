# security domain memory binary
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches native or unsafe code, parsers and decoders, foreign-function boundaries, binary loaders, kernel or driver interfaces, language runtimes or JITs>

---

Nothing here is in `skills/review-checklist/references/security-surfaces.md`, so the file is whole; base checks stay in `skills/review-checklist/references/security-depth.md`. Tiering: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, against `skills/review-checklist/references/security.md` § What is a finding bounding what qualifies, and this file adds none. Protocol authorization and state-machine logic belong to `skills/review-checklist/references/security-domain-protocols.md`; this file covers process integrity, memory safety, ABI boundaries and loader behavior. A crash that shared users can trigger is reported under `skills/review-checklist/references/security-domain-availability.md`.

## When to use

The target handles untrusted bytes in a memory-unsafe or privileged context: C, C++, Objective-C, Rust `unsafe`, foreign-function interfaces, kernel modules and drivers, parsers and decoders, network daemons, firmware, binary loaders, runtimes and JITs. Split a large target by parser, allocator and lifetime, foreign interface, concurrency, loader, runtime or privileged interface.

## Core discipline

- Re-derive every bound and lifetime from attacker-controlled inputs and all callers, and test against the worst accepted case, not a typical sample.
- A panic, sanitizer report or crash proves a defect only when a realistic untrusted input reaches it; never infer memory corruption, code execution or shared unavailability from a label.
- Reproduction uses a local harness: sanitizers, deterministic concurrency tests, existing fuzz targets and debugger-assisted fault classification. Stop once the violated invariant and its observable effect are shown; never develop post-corruption techniques.
- Assembly, JIT output, custom allocators, intra-object accesses and foreign libraries can fall outside sanitizer coverage; say which instructions are instrumented.
- Unknown ABI, allocator, architecture, feature, deployment or reachability facts are `needs_validation`.

## Bounds, integer and representation classes

- **Out-of-bounds access**: a length, offset, index or terminator reaches a fixed or allocated buffer with no correct bound. Recompute headroom after prefixes, alignment, padding and terminators; check source and destination capacity, and whether a short input is read before its declared length is trusted.
- **Integer arithmetic faults**: attacker-controlled arithmetic before allocation, copy, loop, indexing or pointer steps. High-hit shapes: `a - b` with `b > a`, `count * element_size`, additions near the type maximum, negatives converted to unsigned, 64-bit lengths narrowed into 32-bit fields, and a sentinel such as `-1` becoming a huge size. Confirm which checked representation is used afterward.
- **Unit and pointer-depth confusion**: bytes, elements, code units, pages, words, wire units or nested element sizes mixed. Compare the unit at parse, validation, allocation, API boundary and copy; a bounds check in the same wrong unit as the allocation is still wrong.
- **Uninitialized data**: a buffer, padding, struct field or vector capacity returned, compared, hashed, serialized or passed across a trust boundary before initialization. Needs an observable consumer and a realistic output length; a stack allocation alone is not disclosure.

## Lifetime, type and concurrency classes

- **Use after free and stale views**: owners released while callbacks, wait queues, timers, iterators, borrowed slices or cached raw pointers can still use them. Read every error, cancellation, close and realloc path; for embedded notification anchors, each free path must drain or detach all observers.
- **Type confusion**: a tag, vtable, union discriminator, object kind or foreign handle is checked differently from the representation read later. Look for unchecked dynamic casts, stale tags after reuse and serialized types whose validated element differs from the consumed one; confirm the wrong-type access locally without extending beyond the violated invariant.
- **Reference-count and ownership races**: non-atomic retain and release, a check followed by an unlocked use, or ownership rules that differ across threads. Compare fast, error, shutdown and compatibility paths for the same locking.
- **Shared-state races**: concurrent parser streams, global caches, lazy initialization, signal handlers and teardown can invalidate a bound, policy or pointer established earlier. Reproduce with a repeatable schedule, barrier or thread sanitizer; an imagined interleaving with no security-relevant state change stays `needs_validation`.
- **Lock order and starvation**: reachable operations take locks in inconsistent order or hold them across callbacks and blocking I/O. Report under availability only when bounded input stops shared progress; otherwise record it as an ordinary concurrency defect.

## Foreign-interface and ABI classes

- **Pointer, length and ownership contract mismatch**: caller and callee disagree about who allocates, frees, pins or changes a buffer, how long a pointer stays valid, or whether a length counts bytes or elements. Trace both sides of every `extern`, CGo, JNI, Python or native binding and generated wrapper; check null, zero length, aliasing and callback retention.
- **Layout and calling-convention disagreement**: a struct, bitfield, packed record, callback signature, integer width, enum or calling convention differs by architecture or build flag. Verify representation attributes, packing, alignment, endianness and ABI-specific types; a declaration mismatch in the repository is confirmable locally, an opaque foreign implementation is `needs_validation`.
- **Unwind and thread-affinity violations**: exceptions or panics cross an ABI that forbids unwinding, callbacks run after teardown, or an API tied to one runtime thread is called elsewhere. Read error conversion and cancellation, and confirm whether the process aborts or state corrupts before assigning impact.

## Binary loading and runtime classes

- **Search-order trust**: a privileged process loads a library, plugin, runtime image or helper from a path a less-trusted principal can write, or resolves a bare name through an attacker-influenceable working directory or environment. Compare intended ownership with each fallback and compatibility path; a user loading their own plugin into their own process is not a violation.
- **Check-to-map identity gap**: a loader verifies one file or metadata record but maps another because path resolution, replacement, architecture slices or embedded resources are not bound to the check. Distribution-channel authenticity belongs to the supply-chain domain; this class is the local verification-to-map gap.
- **Malformed metadata and relocations**: offsets, counts, sections, relocations, symbols, bytecode or debug metadata trusted before range, overlap and representation checks. Feed parsers bounded local fixtures under sanitizers, and separate memory corruption from a malformed file rejected safely.
- **JIT and generated-code consistency**: validator, interpreter, optimizer and generated code disagree on types, bounds, side effects or lifetime. Diff optimized and unoptimized paths on the same input and confirm an integrity effect; output variance within language semantics is not a finding.
- **Teardown safety**: function pointers, callbacks, worker threads or data views still referenced after module unload or runtime reset. Read shutdown and failed-load cleanup as closely as startup.

## Kernel and privileged-interface classes

- **User-copy bounds and repeated reads**: a syscall, control call, driver or kernel parser derives a trusted fact from user memory and then reads the same mutable address again. Copy the full request once or revalidate the later copy; audit size, direction and access checks at each user-copy primitive.
- **Privileged object lifecycle and dispatch**: reachable objects with unbalanced retain and release, teardown without observer drain, unchecked selector or table indices, or duplicated compatibility paths missing a guard. Diff each dispatch and free path side by side.
- **Under-authorized powerful interfaces**: a device node, admin socket, helper or management API validates shape but not the caller's authority over the resource. Establish actual ownership and reachability; permissions or confinement policy outside the repository make it `needs_validation`. <!-- scrub-allow: generic security term, not a personal name -->

## Universal moves

- Audit fixes and duplicated paths for the same source-to-sink shape: a check in one caller, architecture, protocol role, feature flag or compatibility path does not protect its siblings.
- Build a table per parser or foreign boundary: accepted length and type, checked representation, allocation owner, consumer, thread and teardown. Most native findings are one disagreement in that table.
- Use existing corpora and small locally generated boundary fixtures; keep the exact sanitizer output and the triggering input property, avoid large resource use, and never run against a deployed target (that is `needs_validation`, naming the local harness).

## Validation rules

1. Establish a realistic untrusted entry and the exact operation that breaks a bounds, type, lifetime, ABI, concurrency, loader or authority invariant.
2. Classify the observable effect (invalid read, invalid write, stale alias, wrong object, uninitialized output, unauthorized image load, deadlock, or safe termination) and claim nothing stronger than observed.
3. Use the narrowest local harness, existing test, sanitizer or fuzzer that reproduces it; verify sanitizer coverage of the faulting operation and record architecture and build conditions.
4. Concurrency needs a deterministic schedule or sanitizer trace; binary loading needs proof that the checked identity differs from the mapped one and the named lower-trust writer.
5. `confirmed` needs the exact input, source trace and observed result; `needs_validation` names the unresolved reachability, ABI, build, deployment or runtime fact and the bounded check.
