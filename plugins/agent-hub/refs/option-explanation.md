# Option explanation

Tier 3 of `rules/core.md § Ask, never guess` — the rules live here; the core keeps one pointer line.
Read when: building an `AskUserQuestion` call — every agent with a gate that asks the user.

---

# 17. Option Explanation Standard (HARD — AskUserQuestion)

**Ask the open question first**: state the decision plainly and let the user answer in their own words, `options[]` empty. Offer 2-4 options with a recommendation when the user is stuck or the choice is a real trade-off. One decision per question; a clarify turn may carry up to **5** questions, all on one issue (another issue goes in its own round, D18), each its own decision, never bundled. Every option gets a full explanation in the reply language (`rules/core.md § Language`), never a vague one-liner.

**Per option**: Solution (1-2 sentences) · How (the steps) · Impact (files · behaviour change · performance · risk) · Trade-off (✅ / ❌) · When to choose it · Effort (S/M/L) · Reversibility; the headings are shown in the reply language.

**AskUserQuestion mapping**: `label` ≤5 words, a verb plus a user-visible object, no jargon. `description` ≤2 sentences on the **consequence the user sees**, never the code mechanism. The rest goes in the preview text or markdown printed before the call.

**Plain language.** A non-developer must understand `label` and `description`. Outside a code block, banned: refactor, DAG, polymorphism, hydration, idempotent, schema-migration, binding, coroutine, N+1, adapter, strategy pattern, side-effect, race condition. Unavoidable → move to **Explain** with a one-sentence gloss in the reply language and an everyday example.

**The Explain block** — required when an option carries technical weight; code allowed with its meaning in words beside it, never bare. Seven points:

1. **What logic** — in plain language: what goes in, what happens, what comes out; with code, explain it line by line.
2. **Where** — a concrete `file:line`, or a module name the user knows; never "somewhere in the backend".
3. **Impact** — what the user sees differently, which features are touched (≤5), whether downtime, a migration or re-login is needed.
4. **Knowledge used** — the pattern or library by its real name, one sentence in the reply language with an everyday example, an official link.
5. **Why this way** — the project's current constraint that forces it; never "best practice".
6. **Concrete benefit** — numbers, before and after, risk avoided ("~300 ms less per request because the DB-calling loop (N+1) is gone", not "faster, cleaner").
7. **Concrete cost** — what could break, extra maintenance, a new dependency ("needs Redis, so devops must set up and monitor one more service", not "a bit more complex").

5-15 sentences. A rename or copy change may skip Explain; an option touching the data model, an API contract or infrastructure **must** have it.

**Recommended.** Exactly one option is marked Recommended, with a reason of ≥2 sentences: why it fits **this** project (constraint, data volume, team size, deadline) and why the alternatives are worse (trade-off numbers). Word each question so "yes" accepts your recommendation.

**Forbidden**: a label plus a one-line description · "A faster, B safer" with no numbers · more than 4 options · a Recommended justified by "industry standard" · skipping the explanation because the user seems rushed · a code block inside `label` or `description` · an unglossed jargon term · dropping Explain on a data, API or infra option.

| Rationalization | Reality |
|---|---|
| "The user is in a hurry, a one-liner will do" | Only the user saying "keep it short" or "I understand the code" (or the same words in the reply language) switches to compact mode |
| "It is the industry standard" | A recommendation cites this project's constraint |

**Override**: "keep it short" or "I understand the code", or the same words in the reply language, enables compact mode — label, description, one recommended reason. Default stays full.

---

# The user_questions block

`user_questions[]` is required on `needs_user_input`: main thread passes it verbatim to `AskUserQuestion`. Its text is in the reply language (`rules/core.md § Language`); the shape of a question, the count per round and the one-issue rule are § 17 above.
