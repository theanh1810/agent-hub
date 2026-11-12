---
sdd_adopted: YYYY-MM-DD          # date SDD started for this repo
naming_convention_from: YYYY-MM-DD   # from this date a new test must carry UC-ID + AC-ID
scope: partial                    # partial | full
modules_in_scope:                 # required when scope=partial
  - src/use-cases/checkout
---

# Spec index

> Prose in this file is written in the reply language (core §1); headings, field labels and ids stay in English.
>
> The YAML block above is **required**. Without it, `auditor` cannot tell
> "no tests yet" from "tests exist but are not labelled", and reports N/A instead of 0%.
> Never edit `sdd_adopted` later: it is the cut-off that excludes old commits from the measurement.

## Use cases

| Id | Name | Business group | Status | AC | Updated |
|---|---|---|---|---|---|
| UC-001 | {name} | {group} | draft / approved / implemented / retired | {n} | YYYY-MM-DD |

## Business requirements

| Id | Name | Status | Related UCs |
|---|---|---|---|
| BR-001 | {name} | draft / approved / in progress / done | UC-001, UC-002 |

## Not yet specified

> **This section is required.** Without it the index lies about coverage: the reader
> assumes whatever is absent from the tables above does not exist, when in fact
> nobody has written it yet.

| Module / flow | Why not written | Temperature | Expected |
|---|---|---|---|
| {e.g. src/reporting} | untouched for 8 months | cold | not needed |
| {e.g. src/notifications} | waiting for the business decision | warm | next quarter |

Module temperature is found with:

```bash
git log --since=6.months.ago --name-only | sort | uniq -c | sort -rn | sed -n '1,20p'
```

Hot (changes every sprint) → full spec · warm (every few months) → stub · cold → leave alone.

## Unconfirmed legacy

UCs under `use-cases/_legacy/` are specs dug out of old code that **nobody on the business side has confirmed**.
They do not count toward coverage. Never use them as grounds to claim any behaviour is correct.

| Id | Name | Dug from | Who to ask |
|---|---|---|---|
| UC-0XX | {name} | {controller / log / UI} | {the operator} |
