# Codex Work runtime contract

This contract adapts the complete Claude workflow to local Work/Codex. It takes precedence
over runtime-specific wording in migrated role bodies, skills and shared rule references.
System/developer policy, sandbox restrictions and the user's current instructions always
take precedence. This contract does not grant permission to send messages or deploy.

## Fleet

Use the actual configured Codex role profiles in `~/.codex/agents/*.toml`, including effort
variants. Main coordinates the fleet; workers request a follow-up and never recursively
spawn another role. Use the host's available spawn/wait/resume API. Where its spawn API
accepts a custom agent selector, select the exact configured role. If it has no selector,
provide that profile's full developer instructions in a self-contained worker brief and
record the limitation. Dispatch workers only through that spawn operation; do not create user chats to simulate workers.

The installed workflow requests role delegation for engineering work where the host allows
it. A higher-priority prohibition on proactive delegation wins; in that case use sequential
role phases, report self-review honestly, and leave a mandatory independent gate pending.
Leave the independent reviewer visibly pending; never silently downgrade it to an implementer's self-review.

`Agent(...)` means the real host spawn operation, `SendMessage` means its permitted worker
message/resume operation, and `AskUserQuestion` means the real available user-input tool.
These are conceptual mappings, not executable API names. Use the actual exposed signature.
`$ARGUMENTS` means the user's supplied command arguments, never shell substitution.

## Models, effort, caps and tools

All 19 profiles inherit the parent OpenAI model and preserve each source profile's reasoning
effort through `model_reasoning_effort`. Claude model names are historical tiers; pass the inherited OpenAI model, never
a Claude name as a Codex model. Opus/sonnet/haiku header strings become a truthful role
header using the effective OpenAI model when known; otherwise omit the unknown model.
Report only cost or token measurements taken on this host; do not fabricate them from historical Claude calibration figures.

Codex has no equivalent enforced per-profile `maxTurns` in the currently documented schema.
Keep source caps as provenance and checkpoint/resume guidance; never claim they are enforced.
Role ownership and read/write restrictions remain mandatory instructions. Claude's
frontmatter `tools` allowlist is not a native per-role allowlist in this conversion.
Permissions remain those of the parent; source restrictions do not widen them.

Codex does not eagerly load skills from Claude frontmatter. Each role must explicitly read
its listed bootstrap skills if not already present. Load only relevant references. Read the
actual source disk section before judging a rule; source history is not current authority.

Use the real tool names supplied by configured connectors. Source MCP prefixes are semantic
names, not a guarantee of a tool schema. GitNexus, mem0, Context7 and UI tools are used only
when exposed and authorized. Missing tools are reported unavailable; appropriate targeted
search or official documentation can support a result, reported as that and not as a graph
PASS, a memory write or an executed browser test.

## Rules and artifacts

`~/.codex/claude-compat/` holds the converted rule/reference library. Relative rule paths
such as `refs/`, `agents/`, `skills/` and `templates/` resolve from that library, never from
the application repository. Native skill folders are under `~/.agents/skills/`.
Historical `docs/analysis`, `docs/plan` and `docs/adr` references that document earlier user
decisions remain at `~/.claude/docs/`; their ids are preserved verbatim. Product artifact
paths resolve from the explicitly resolved product workspace.

The library shares scripts, templates, code style and other unchanged support resources
with `~/.claude` through links; it does not require the Claude application or Claude API.
It requires the source library to remain on this machine. Regenerate with `codex-convert.py`
after source edits; manifest hashes detect drift. Keep the original library in place and do not move or delete it
until those support links and historical citations have been migrated explicitly.

Behavior specs/current approved deltas own intent. Brainstorm owns scope and decomposition.
Execution YAML owns tasks and results; Vietnamese mirror is derived.
Keep English YAML and Vietnamese human prose according to the source templates. Source
plan paths, diagnostic paths, lock protocol, exact results and spec references remain intact.
Change files follow `refs/change-files.md`. Never rewrite a historical id just because it contains `claude`.

## Gates, errors and closeout

Preserve all workflow gates for decisions that remain unresolved. Retain authorization and
choices already given in the conversation; do not ask again solely because a phase changes.
Update the affected design/plan before applying a scope amendment. A user's chat instruction
is valid intent, not a reason to discard the amendment. Host restrictions still apply.

Keep the source error-loop cap of two correction cycles, exact diagnostics and approved
partial status. Failed behavior, unresolved gates or missing evidence never become done.
Implement → review → test remains the order after edits. Independent review/test read the
same frozen state. Further edits invalidate evidence for the prior state as appropriate.

Closeout records actual scope/diff, task results, validation, spec sync, available durable
memory and exact-path cleanup. A ruleset check runs on the source `.claude` tree, not the
translated library: the source checker validates historical pins and Claude runtime tables.
The conversion manifest/validator separately validates native configuration and drift.

## Hooks, worktrees and statusline

SessionStart, UserPromptSubmit and PreToolUse are translated to Codex hook events. Hooks
remain pending until the host's normal exact-definition trust review is completed. Follow trust and permission policy as configured and do not
bypass it. RTK is a command-output aid, never the authority for a
reviewed diff or an approval grant. Native permissions still apply to rewritten commands.

Codex currently exposes no WorktreeCreate/WorktreeRemove hook events. Use native managed
worktree creation/archive lifecycle with the host's supported tools when needed. Preserve
the user's requested starting state and never replace those operations with the source
tar-copy/delete hooks. Record that this is a native equivalent, not identical hook execution.
Claude statusLine has no documented equivalent in Work; use the native task/tool status.

Commands migrate to skill entry points: source-command-spec, source-command-audit and
source-command-codestyle; init/check are supporting refs, not separate user commands.
Orchestrate remains a manual skill. Use the skill selector supported by Work/Codex rather
than claiming that Claude slash commands were registered identically.

The native Codex wrapper replaces Claude's plugin that calls Codex as an external engine.
Imported plugins retain their own compatibility and authorization requirements. Import
success establishes installation, not every plugin's live connector health.
