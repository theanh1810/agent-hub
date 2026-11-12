# lark-task: Init, New project and registry shape

Read from `SKILL.md` section 5 (Init, New project) and section 6 (registry writes).

## Init and New project

**Init (once, resumable).** Write each guid to the registry right after the call that returns it; a rerun creates only what the registry still lacks.

1. `template_tasklist_guid` null: `tasklist.list` and look for `[TPL] lark-task fields`. Exactly one found: record its guid. More than one: stop and ask. None: `tasklist.create` `[TPL] lark-task fields` and write its guid immediately.
2. `customField.list` on the template tasklist. For each field whose registry guid is null (`Priority` single_select with the 4 options `P0 Urgent`, `P1 High`, `P2 Medium`, `P3 Low`, `Labels` multi_select with the 6 options `Frontend`, `Backend`, `Bug`, `Feature`, `Docs`, `Infra`, `Estimate` number decimal_count 1, `Status` single_select with the 6 options of `SKILL.md` section 3): a field with that exact name already on the template - record its guid and option guids (an option name missing from it: stop and ask); otherwise `customField.create` it and write its guid and option guids immediately. Never create a field whose name already exists on the template.
3. `me.open_id` null: the owner of the template tasklist (`tasklist.get`). Only if the owner id is missing, ask the user for an email and resolve it as in `SKILL.md` section 4 (`contact_v3_user_batchGetId` on `lark-contact`); no open_id returned: stop and tell the user.

**New project.** `tasklist.list` first: if `[PRJ] <name>` already exists and the registry lacks
that KEY, stop and ask. Otherwise `tasklist.create` `[PRJ] <name>`, and right after write
`projects.<KEY>` = `{name, tasklist_guid, sections: {}, next_n: 1}` -> `section.list`, rename the
default section to `Backlog` with `section.patch` -> `section.create` for `To do`, `In progress`,
`Testing`, `Deploy`, `Done` in that order, adding each section guid to the registry as it is created. If the
registry shows fewer than 6 sections, resume the remaining section steps; never `tasklist.create`
again. Then `customField.list` on the project and `customField.add` only the missing fields
(resource = the new tasklist) -> `customField.list` read-back.

## Registry shape

Write after every create. Ids only. Keep to the keys of this shape and never add keys outside it:

```
version, domain
me.open_id
template_tasklist_guid
fields{priority{guid, options}, labels{guid, options}, estimate_hours{guid}, status{guid, options}}
projects{KEY:{name, tasklist_guid, sections{name:guid}, next_n}}
```

| Template field | Registry key |
|---|---|
| `Priority` | `fields.priority` |
| `Labels` | `fields.labels` |
| `Estimate` | `fields.estimate_hours` |
| `Status` | `fields.status` |

`options` is keyed by the exact option name (`SKILL.md` section 3) -> option_guid; `sections` is keyed by the
exact section name (`SKILL.md` section 2) -> section_guid.
