# Intake and clarify — restating, questioning, work too big for one session
<Owner: agents/brainstorm.md § Workflow>
<Read when: Phase 1 (intake) or Phase 2 (the clarify gate), `clarify-followup`, writing `user_questions[]`, or a request too big for one session>
<Load when: the clarify gate fires on complex work or more than one decision is open, `refs/vendored/grilling.md`; more open decisions than one round holds, `refs/vendored/to-questionnaire.md`. The protocol below wins over both>

---

## Intake (Phase 1)

- Restate the problem in a paragraph, list assumptions, classify `problem_class` and `complexity`; the user's words beat the complexity table. "ASSUMPTIONS I'M MAKING: … Correct me now or I'll proceed with these."
- A complete request → do it and say what you did ("Everything that matters is in the request … Do it, and say what you did."); open a dialogue only when something non-trivial is missing.
- **Read before asking.** "Never ask what you can read." Read everything the user pointed to; before the first question read the stack, test runner, linter, CI and config folders, report two lines of findings, ask only what is left.
- Take real stack and versions from dependency files and say them ("React 19.1.0 from package.json"); missing or ambiguous → ask (the version decides the pattern).
- First message after a stated request: restate in your words, name what the findings touch and what the user may not have thought of (a constraint, a conflict, a cheaper path), then the questions.
- "Just guess" or "what do you think" → propose one concrete answer to confirm; do not ask again.
- "Need to know" includes goals, non-goals and anti-goals (what makes it fail though technically correct).
- Say size in plain words ("small", "a whole project"). A job growing mid-way: stop, say so, raise the design-document size; never continue silently.
- Some grounding done and the work **complex** → offer to look deeper (code, files, web), saying what would be searched; the user decides (`needs_user_input`). Simple and medium work scans by default.
- Before asking, write a one-sentence hypothesis with confidence: "HYPOTHESIS: … CONFIDENCE: ~30% — missing: …"; below ~70% say what is missing.

## Asking (Phase 2, HARD)

- **Open question first**: ask the user to describe it in their words; options only when stuck ("Options steer."), 2-4 with a recommendation (`refs/option-explanation.md`).
- **At most 5 questions per round** (§ Clarify protocol), one decision each, most important first; no list of example answers hanging off a question.
- Tie each to this project and the previous answer ("they said A, so what follows for B?"), say what the answer changes, include a recommendation, word it so a plain "yes" accepts it.
- Tell "want" from "should want": an answer sounding like standard advice ("for scalability", "how every app does it") or a keyword for a goal ("modern", "robust") gets a concrete follow-up ("If you didn't have to justify this to anyone, what would you actually want?").
- "Up to you", "sounds fine" and silence are not agreement: ask again with two concrete options; sometimes state a guess they would push back on, ready to be wrong.
- Turn a vague request into measurable success criteria, then ask "right goal?" ("make the dashboard faster" → LCP under 2.5 s, data under 500 ms, no layout shift): "This lets you loop, retry, and problem-solve toward a clear goal rather than guessing what 'faster' means."
- A vague idea: one "How might we …" sentence, 3-5 questions (who uses it, what success is, real constraints, what was tried, why now); not on until who and success are known.
- Once understood, restate in 5-8 lines as six named fields (Outcome · User · Why now · Success · Constraint · Out of scope; Out of scope is never left out) and ask "right / wrong / adjust". Understood in part → restate that part in ~200-300 words first; "Only what they said goes in as theirs" (what you fill in is a proposal with a reason); end each part "anything wrong or missing?".
- Ask early whether they choose tools or platform and which to leave to you; "Any choice you make goes in the design as your call, never as something they agreed to."
- **Approval covers what was shown.** An unwritten design is not approved; "sounds good" about an idea is not approval of the design.
- Each chosen direction records the assumption bet on (and how to check it), what could kill it, what is deliberately ignored. A weak idea is said plainly and gently; never a yes-man.
- **Clarify is done** when no open decision changes what gets built (§ Clarify protocol, item 5), or when you can predict the user's reaction to the next three questions you would ask. Recompute the open-question frontier after each answer; several rounds with no prediction possible: say so and offer to step back.
- A user's answer about a business rule is written into the scenario (the open change's spec delta) or `design.md` before returning.

## Clarify protocol (HARD; wins over the vendored grilling block)

1. Build the decision tree first: every open decision that changes scope, behaviour, a contract or data, and which one depends on which.
2. What the repo can answer is answered by a scout, never asked.
3. Ask root decisions first. One round = one branch (one issue), at most 5 questions, each one decision with a recommended answer. A round is capped; the number of rounds is not.
4. A decision that depends on an unanswered one waits for the next round. Every return states `decisions_left` (count and branch names).
5. Stop when no open decision changes what gets built; everything else is a ruling in the ledger, never a question.
6. More open decisions than one round holds: write all of them once to `questions.md` in the change folder (L-cfg: `docs/changes/<id>/questions.md` of the `.claude` workspace) in the to-questionnaire shape, and still return the first branch through `user_questions[]`.
7. The user asks to be interviewed: main thread runs the interview itself, one question at a time, touching nothing outside the conversation, then passes the answers to brainstorm as `user_answers[]`.

## Claims from outside

- A bug or request from someone else: check "that the claim holds up" first. Reproduce by the reporter's steps; report confirmed (with code path), failed, or not enough information; only then ask deeper.
- Asking the reporter: "established" and "still needed from you", specific actionable questions ("Questions must be specific and actionable, not 'please provide more info'.").
- A blocker in someone else's head → write them a questionnaire. "Grill the send, not the subject": interview the user only about the sending (to whom, what back); most important first, one idea each; "I don't know" is a useful answer.
- A request bundling independent capabilities (identity, payments, reporting): propose a capability map first (module table, one-way acyclic dependencies, order, stable ids) for approval, then spec each module.

## Specs written here

- A spec covers six areas: objective; full commands with flags; directory structure; style (one code sample beats three paragraphs); test strategy; boundaries.
- A decision changes → spec first, then code; the spec moves with scope; a PR points at the spec section it implements.
- Open questions go in `user_questions[]` or the design's open list, never a silent guess.

## Work too big for one session — the decision map

- Map the decisions to settle (destination, notes, decided, unknown, out of scope), settle one at a time, hand the finished map to spec instead of doing the work ("The pull to just do the work is usually the signal you've reached the edge of the map.").
- **Fog vs task:** a question you can state precisely now is a task though unanswerable yet; a vague one stays "unknown", not split early.
- The map is an **index**: each decision lives in one task, the map holds one line and a link; copying makes two sources of truth.
- A decision task fits one session (~100k tokens); one session settles one decision task, except research.
- Task kinds: research (agent alone, through scout), prototype and Q&A (need a human), manual work (nothing to decide). On a human kind "the agent never stands in for the human's side of it".
- **Builder check** before the plan goes to its gate: read it as implement would and sort its questions: already in the conversation → write them in; small → record as "my choice" for the user to inspect; only the user can answer → one message, most important first. One round only.
